from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def load_side_effect_allow_file(path_value: str, *, tool_error_type: type[Exception]) -> dict[str, Any]:
    if not path_value:
        return {}

    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise tool_error_type("side_effect_allow_file_not_found", f"Side-effect allow file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise tool_error_type("side_effect_allow_file_invalid", str(exc)) from exc
    if not isinstance(payload, dict):
        raise tool_error_type("side_effect_allow_file_invalid", "Side-effect allow file must contain a JSON object.")
    return payload


def capture_git_dirty_paths(workspace_root: Path) -> tuple[str, list[str]]:
    if shutil.which("git") is None:
        return "unavailable", []

    repo_root_result = subprocess.run(
        ["git", "-C", str(workspace_root), "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if repo_root_result.returncode != 0:
        return "unavailable", []

    repo_root = Path(repo_root_result.stdout.strip()).expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--untracked-files=no"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return "unavailable", []

    paths: list[str] = []
    for raw_line in completed.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        value = raw_line[3:].strip()
        if " -> " in value:
            value = value.split(" -> ", 1)[1].strip()
        if value:
            relative_path = _path_relative_to_workspace(repo_root / value, workspace_root)
            if relative_path is not None:
                paths.append(_normalize_path(relative_path))
    return "git", sorted(set(paths))


def _path_relative_to_workspace(path: Path, workspace_root: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(workspace_root))
    except ValueError:
        return None


def build_workspace_side_effects(
    *,
    workspace_root: Path,
    before_dirty_paths: list[str],
    after_dirty_paths: list[str],
    mode: str,
    allow_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before = sorted(set(_normalize_path(path) for path in before_dirty_paths))
    after = sorted(set(_normalize_path(path) for path in after_dirty_paths))
    new_dirty = [path for path in after if path not in set(before)]
    allowed_new = [path for path in new_dirty if _is_allowed(path, allow_config or {})]
    unexpected_new = [path for path in new_dirty if path not in set(allowed_new)]

    return {
        "enabled": True,
        "mode": mode,
        "workspace_root": str(workspace_root),
        "preexisting_dirty_count": len(before),
        "new_dirty_count": len(new_dirty),
        "allowed_new_dirty_count": len(allowed_new),
        "unexpected_new_dirty_count": len(unexpected_new),
        "preexisting_dirty_paths": before,
        "allowed_new_dirty_paths": allowed_new,
        "unexpected_new_dirty_paths": unexpected_new,
        "recommended_cleanup_commands": _recommended_cleanup_commands(allowed_new),
    }


def unavailable_workspace_side_effects(workspace_root: Path, mode: str = "unavailable") -> dict[str, Any]:
    return {
        "enabled": True,
        "mode": mode,
        "workspace_root": str(workspace_root),
        "preexisting_dirty_count": 0,
        "new_dirty_count": 0,
        "allowed_new_dirty_count": 0,
        "unexpected_new_dirty_count": 0,
        "preexisting_dirty_paths": [],
        "allowed_new_dirty_paths": [],
        "unexpected_new_dirty_paths": [],
        "recommended_cleanup_commands": [],
    }


def _is_allowed(path: str, allow_config: dict[str, Any]) -> bool:
    allowed_paths = {_normalize_path(item) for item in list(allow_config.get("allowedTrackedPaths") or [])}
    if path in allowed_paths:
        return True

    for pattern in list(allow_config.get("allowedPathGlobs") or []):
        if fnmatch.fnmatch(path, _normalize_path(str(pattern))):
            return True
    return False


def _recommended_cleanup_commands(paths: list[str]) -> list[str]:
    if not paths:
        return []
    quoted = " ".join(_shell_quote(path) for path in paths)
    return [f"git restore -- {quoted}"]


def _shell_quote(value: str) -> str:
    if not value:
        return "''"
    if all(ch.isalnum() or ch in "/._-:" for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().strip('"')
