#!/usr/bin/env python3
"""Deterministic cleanup for reproducible developer caches and scratch data."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


UNITY_PROCESS_MARKERS = ("/Unity.app/Contents/MacOS/Unity",)
XCODE_PROCESS_MARKERS = (
    "/Xcode.app/Contents/MacOS/Xcode",
    "/usr/bin/xcodebuild",
    "/usr/bin/xctest",
)
SIMULATOR_PROCESS_MARKERS = ("/Simulator.app/Contents/MacOS/Simulator",)
DEFAULT_MODEL_FITNESS_PRUNE_NAMES = {
    "compile-tree",
    "final-tree",
    "prepared",
    "treatment-fixture",
    "workspaces",
    "Library",
    "Temp",
    "Logs",
    "Obj",
    "__pycache__",
}
UNITY_VERSION_PATTERN = re.compile(r"^m_EditorVersion:\s*\S+", re.MULTILINE)


@dataclass(frozen=True)
class Candidate:
    category: str
    path: Path
    anchor: Path
    reason: str


def _is_within(path: Path, anchor: Path) -> bool:
    path_abs = Path(os.path.abspath(path))
    anchor_abs = Path(os.path.abspath(anchor))
    return path_abs != anchor_abs and anchor_abs in path_abs.parents


def _size_bytes(path: Path) -> int:
    if path.is_symlink() or path.is_file():
        try:
            return path.lstat().st_size
        except FileNotFoundError:
            return 0
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in files:
            item = root_path / name
            try:
                total += item.lstat().st_size
            except FileNotFoundError:
                pass
        for name in list(dirs):
            item = root_path / name
            if item.is_symlink():
                try:
                    total += item.lstat().st_size
                except FileNotFoundError:
                    pass
                dirs.remove(name)
    return total


def _age_hours(path: Path, now: float) -> float:
    return max(0.0, (now - path.lstat().st_mtime) / 3600.0)


def _process_commands() -> list[str]:
    completed = subprocess.run(
        ["ps", "-axo", "args="],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.splitlines()


def _has_process(commands: Sequence[str], markers: Sequence[str]) -> bool:
    return any(marker in command for command in commands for marker in markers)


def _is_unity_project(project_root: Path) -> bool:
    assets = project_root / "Assets"
    manifest = project_root / "Packages" / "manifest.json"
    settings = project_root / "ProjectSettings" / "ProjectSettings.asset"
    version = project_root / "ProjectSettings" / "ProjectVersion.txt"
    required_directory = assets.is_dir() and not assets.is_symlink()
    required_files = all(path.is_file() and not path.is_symlink() for path in (manifest, settings, version))
    if not required_directory or not required_files:
        return False
    try:
        return bool(UNITY_VERSION_PATTERN.search(version.read_text(encoding="utf-8")))
    except (OSError, UnicodeError):
        return False


def discover_unity_libraries(scan_roots: Iterable[Path]) -> list[Candidate]:
    candidates: list[Candidate] = []
    prune = {".git", "Library", "Temp", "Logs", "Obj", "Build", "Builds"}
    for scan_root in scan_roots:
        if not scan_root.is_dir():
            continue
        for root, dirs, files in os.walk(scan_root, followlinks=False):
            dirs[:] = [name for name in dirs if name not in prune]
            root_path = Path(root)
            if root_path.name == "ProjectSettings" and "ProjectVersion.txt" in files:
                project_root = root_path.parent
                library = project_root / "Library"
                if _is_unity_project(project_root) and library.is_dir() and not library.is_symlink():
                    candidates.append(
                        Candidate("unity_library", library, project_root, "regenerable Unity import cache")
                    )
                dirs[:] = []
    return sorted(candidates, key=lambda item: str(item.path))


def discover_children(root: Path, category: str, reason: str) -> list[Candidate]:
    if not root.is_dir():
        return []
    return [
        Candidate(category, child, root, reason)
        for child in sorted(root.iterdir(), key=lambda item: item.name)
    ]


def discover_temp_candidates(config: dict, now: float) -> list[Candidate]:
    if not config or "root" not in config:
        return []
    root = Path(config["root"])
    prefixes = tuple(config.get("prefixes", []))
    protected = set(config.get("protected_names", []))
    min_age = float(config.get("minimum_age_hours", 72))
    result: list[Candidate] = []
    if not root.is_dir():
        return result
    for child in root.iterdir():
        if child.name in protected or not child.name.startswith(prefixes):
            continue
        if _age_hours(child, now) < min_age:
            continue
        result.append(Candidate("temporary", child, root, f"temporary prefix older than {min_age:g}h"))
    return sorted(result, key=lambda item: str(item.path))


def discover_model_fitness_candidates(config: dict, now: float) -> list[Candidate]:
    names = set(config.get("prune_directory_names", DEFAULT_MODEL_FITNESS_PRUNE_NAMES))
    min_age = float(config.get("minimum_age_hours", 72))
    result: list[Candidate] = []
    for raw_root_value in config.get("roots", []):
        raw_root = Path(raw_root_value)
        if not raw_root.is_dir():
            continue
        for root, dirs, _files in os.walk(raw_root, topdown=True, followlinks=False):
            root_path = Path(root)
            matches = [name for name in dirs if name in names]
            for name in matches:
                candidate = root_path / name
                if _age_hours(candidate, now) >= min_age:
                    result.append(
                        Candidate("model_fitness_workspace", candidate, raw_root, "regenerable evaluation workspace/cache")
                    )
                dirs.remove(name)
    return sorted(result, key=lambda item: str(item.path))


def discover_scratch_candidates(config: dict, now: float) -> list[Candidate]:
    result: list[Candidate] = []
    for item in config.get("roots", []):
        root = Path(item["path"])
        min_age = float(item.get("minimum_age_hours", 168))
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if _age_hours(child, now) >= min_age:
                result.append(Candidate("scratch", child, root, f"scratch child older than {min_age:g}h"))
    return sorted(result, key=lambda item: str(item.path))


def _contains_dirty_git(path: Path) -> bool:
    git_roots: list[Path] = []
    if (path / ".git").exists():
        git_roots.append(path)
    if path.is_dir():
        for root, dirs, _files in os.walk(path, followlinks=False):
            if ".git" in dirs:
                git_roots.append(Path(root))
                dirs.remove(".git")
    for git_root in git_roots:
        completed = subprocess.run(
            ["git", "-C", str(git_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or completed.stdout.strip():
            return True
    return False


def _is_tracked_by_parent_repo(candidate: Candidate) -> bool:
    current = candidate.anchor
    repository = None
    while current != current.parent:
        if (current / ".git").exists():
            repository = current
            break
        current = current.parent
    if repository is None:
        return False
    try:
        relative = candidate.path.relative_to(repository)
    except ValueError:
        return True
    completed = subprocess.run(
        ["git", "-C", str(repository), "ls-files", "--error-unmatch", "--", str(relative)],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _remove(candidate: Candidate) -> None:
    if not _is_within(candidate.path, candidate.anchor):
        raise ValueError(f"unsafe candidate outside anchor: {candidate.path}")
    if candidate.path.is_symlink() or candidate.path.is_file():
        candidate.path.unlink(missing_ok=True)
    elif candidate.path.is_dir():
        shutil.rmtree(candidate.path)


def _run_simulator_cleanup(mode: str, runner: Callable[..., subprocess.CompletedProcess[str]]) -> list[dict]:
    commands: list[list[str]] = []
    if mode == "erase_all":
        commands = [["xcrun", "simctl", "shutdown", "all"], ["xcrun", "simctl", "erase", "all"]]
    elif mode == "delete_all":
        commands = [["xcrun", "simctl", "shutdown", "all"], ["xcrun", "simctl", "delete", "all"]]
    elif mode not in {"off", "report"}:
        raise ValueError(f"unsupported simulator mode: {mode}")
    results = []
    for command in commands:
        completed = runner(command, capture_output=True, text=True)
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
        if completed.returncode != 0:
            break
    return results


def run_cleanup(
    config: dict,
    *,
    apply: bool,
    now: float | None = None,
    commands: Sequence[str] | None = None,
    simulator_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    now = time.time() if now is None else now
    commands = _process_commands() if commands is None else list(commands)
    blocked = {
        "unity_library": _has_process(commands, UNITY_PROCESS_MARKERS),
        "xcode_derived_data": _has_process(commands, XCODE_PROCESS_MARKERS),
        "simulator": _has_process(commands, XCODE_PROCESS_MARKERS + SIMULATOR_PROCESS_MARKERS),
    }

    candidates: list[Candidate] = []
    candidates.extend(discover_temp_candidates(config.get("temporary", {}), now))
    candidates.extend(discover_scratch_candidates(config.get("scratch", {}), now))
    candidates.extend(discover_model_fitness_candidates(config.get("model_fitness", {}), now))
    unity = config.get("unity", {})
    if unity.get("remove_libraries", False):
        candidates.extend(discover_unity_libraries(Path(value) for value in unity.get("scan_roots", [])))
    xcode = config.get("xcode", {})
    if xcode.get("remove_derived_data", False):
        candidates.extend(
            discover_children(Path(xcode["derived_data_root"]), "xcode_derived_data", "regenerable Xcode cache")
        )

    entries = []
    reclaimed = 0
    for candidate in candidates:
        size = _size_bytes(candidate.path)
        state = "candidate"
        detail = candidate.reason
        if candidate.category in blocked and blocked[candidate.category]:
            state = "skipped_active_process"
        elif candidate.category in {"temporary", "scratch"} and any(
            str(candidate.path) in command for command in commands
        ):
            state = "skipped_live_process_reference"
        elif candidate.category in {"scratch", "unity_library"} and _is_tracked_by_parent_repo(candidate):
            state = "skipped_tracked_path"
        elif candidate.category in {"temporary", "scratch"} and _contains_dirty_git(candidate.path):
            state = "skipped_dirty_git"
        elif apply:
            _remove(candidate)
            state = "deleted"
            reclaimed += size
        entries.append(
            {
                "category": candidate.category,
                "path": str(candidate.path),
                "bytes": size,
                "state": state,
                "reason": detail,
            }
        )

    simulator_config = config.get("simulator", {})
    simulator_mode = simulator_config.get("mode", "off")
    simulator_results: list[dict] = []
    simulator_state = "off"
    if simulator_mode not in {"off", "report"}:
        simulator_state = "candidate"
        if blocked["simulator"]:
            simulator_state = "skipped_active_process"
        elif apply:
            simulator_results = _run_simulator_cleanup(simulator_mode, simulator_runner)
            simulator_state = "completed" if simulator_results and simulator_results[-1]["returncode"] == 0 else "failed"

    audit = []
    for value in config.get("audit_only_paths", []):
        path = Path(value)
        audit.append({"path": str(path), "bytes": _size_bytes(path) if path.exists() else 0, "exists": path.exists()})

    return {
        "schema_version": 1,
        "mode": "apply" if apply else "dry_run",
        "generated_at_epoch": int(now),
        "reclaimed_bytes": reclaimed,
        "process_guards": blocked,
        "entries": entries,
        "simulator": {"mode": simulator_mode, "state": simulator_state, "commands": simulator_results},
        "audit_only": audit,
    }


def _load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("config schema_version must be 1")
    return data


def _write_report(report: dict, destination: Path | None) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if destination is None:
        sys.stdout.write(payload)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(destination)
    sys.stdout.write(payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="perform deletion; omission is dry-run")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--lock", type=Path, default=Path("/private/tmp/workspace-cleanup.lock"))
    args = parser.parse_args(argv)
    config = _load_config(args.config)
    args.lock.parent.mkdir(parents=True, exist_ok=True)
    with args.lock.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("cleanup already running", file=sys.stderr)
            return 2
        report = run_cleanup(config, apply=args.apply)
        _write_report(report, args.report)
    return 1 if report["simulator"]["state"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
