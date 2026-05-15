#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from server_bridge_runtime import (
    bridge_state_path,
    bridge_enabled,
    default_editor_log_path,
    heartbeat_age_seconds,
    host_editor_session_state_path,
    logs_dir,
    pid_is_alive,
    try_read_bridge_state,
    try_read_live_editor_state,
)
from server_core import ToolInvocationError, read_json, write_json
from server_host_platform import current_host_platform_adapter
from server_specs import STARTUP_POLICIES

ACTIVATION_DELAY_SECONDS = 0.35
UNITY_EDITOR_ROOTS_ENV = "XUUNITY_UNITY_EDITOR_ROOTS"
HOST_EDITOR_LAUNCH_IN_PROGRESS_MAX_AGE_SECONDS = 90.0


def host_platform_kind() -> str:
    return current_host_platform_adapter().platform_kind


def parse_unity_version_from_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    match = re.search(r"(\d{4}\.\d+\.\d+[A-Za-z]\d+)", text)
    if match:
        return match.group(1)
    return text


def version_sort_key(version: str) -> tuple[Any, ...]:
    text = (version or "").strip()
    match = re.match(r"(\d+)\.(\d+)\.(\d+)([A-Za-z])(\d+)$", text)
    if not match:
        return (0, 0, 0, 0, 0, text)

    stream_rank = {
        "a": 0,
        "b": 1,
        "f": 2,
        "p": 3,
        "x": 4,
    }
    major, minor, patch, stream, stream_number = match.groups()
    return (
        int(major),
        int(minor),
        int(patch),
        stream_rank.get(stream.lower(), 99),
        int(stream_number),
        text,
    )


def normalize_unity_installation_path(path: Path) -> Path | None:
    candidate = path.expanduser().resolve()
    platform_kind = host_platform_kind()

    if platform_kind == "macos":
        if candidate.is_file() and candidate.name == "Unity" and candidate.parent.name == "MacOS":
            app_path = candidate.parent.parent.parent
            if app_path.name == "Unity.app":
                return app_path
        if candidate.is_dir() and candidate.name == "Unity.app" and (candidate / "Contents" / "MacOS" / "Unity").is_file():
            return candidate
        return None

    if platform_kind == "windows":
        if candidate.is_file() and candidate.name.lower() == "unity.exe":
            return candidate
        if candidate.is_dir():
            direct = candidate / "Unity.exe"
            nested = candidate / "Editor" / "Unity.exe"
            if direct.is_file():
                return direct
            if nested.is_file():
                return nested
        return None

    if candidate.is_file() and candidate.name == "Unity":
        return candidate
    if candidate.is_dir():
        direct = candidate / "Unity"
        nested = candidate / "Editor" / "Unity"
        if direct.is_file():
            return direct
        if nested.is_file():
            return nested
    return None


def resolve_unity_executable(unity_app: Path) -> Path:
    normalized = normalize_unity_installation_path(unity_app)
    if normalized is None:
        raise ToolInvocationError("unity_app_not_found", f"Unity installation not found: {unity_app}")

    if host_platform_kind() == "macos":
        executable = normalized / "Contents" / "MacOS" / "Unity"
    else:
        executable = normalized

    if not executable.is_file():
        raise ToolInvocationError("unity_binary_not_found", f"Unity binary not found: {executable}")
    return executable


def resolve_unity_app_version(unity_app: Path) -> str:
    normalized = normalize_unity_installation_path(unity_app)
    if normalized is None:
        return ""

    platform_kind = host_platform_kind()
    if platform_kind == "macos":
        return normalized.parent.name

    if platform_kind == "windows":
        if normalized.parent.name == "Editor":
            return parse_unity_version_from_text(normalized.parent.parent.name)
        return parse_unity_version_from_text(normalized.parent.name)

    if normalized.parent.name == "Editor":
        return parse_unity_version_from_text(normalized.parent.parent.name)
    return parse_unity_version_from_text(normalized.parent.name)


def configured_unity_editor_roots() -> list[Path]:
    raw = (os.environ.get(UNITY_EDITOR_ROOTS_ENV) or "").strip()
    if not raw:
        return []

    roots: list[Path] = []
    for entry in raw.split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        roots.append(Path(entry).expanduser())
    return roots


def candidate_unity_editor_roots() -> list[Path]:
    configured = configured_unity_editor_roots()
    if configured:
        return configured

    platform_kind = host_platform_kind()
    roots: list[Path] = []

    if platform_kind == "macos":
        roots.append(Path("/Applications/Unity/Hub/Editor"))
        return roots

    if platform_kind == "windows":
        seen: set[str] = set()
        for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = (os.environ.get(env_name) or "").strip()
            if not value:
                continue
            expanded = str(Path(value).expanduser())
            if expanded.lower() in seen:
                continue
            seen.add(expanded.lower())
            roots.append(Path(expanded))
        return roots

    roots.append(Path.home() / "Unity" / "Hub" / "Editor")
    roots.append(Path("/opt/Unity/Hub/Editor"))
    roots.append(Path("/opt/unity/Hub/Editor"))
    return roots


def iter_candidate_installation_paths_from_root(root: Path) -> list[Path]:
    platform_kind = host_platform_kind()
    candidates: list[Path] = []

    normalized_root = normalize_unity_installation_path(root)
    if normalized_root is not None:
        candidates.append(normalized_root)
        return candidates

    if not root.exists():
        return candidates

    if platform_kind == "macos":
        candidates.extend(sorted(root.glob("*/Unity.app")))
        return candidates

    if platform_kind == "windows":
        candidates.extend(sorted(root.glob("Unity/Hub/Editor/*/Editor/Unity.exe")))
        candidates.extend(sorted(root.glob("Unity*/Editor/Unity.exe")))
        candidates.extend(sorted(root.glob("Unity/Editor/Unity.exe")))
        return candidates

    candidates.extend(sorted(root.glob("*/Editor/Unity")))
    candidates.extend(sorted(root.glob("*/Unity")))
    return candidates


def discover_unity_installations() -> list[tuple[str, Path]]:
    discovered: list[tuple[str, Path]] = []
    seen: set[str] = set()

    for root in candidate_unity_editor_roots():
        for candidate in iter_candidate_installation_paths_from_root(root):
            normalized = normalize_unity_installation_path(candidate)
            if normalized is None:
                continue
            key = str(normalized).lower() if os.name == "nt" else str(normalized)
            if key in seen:
                continue
            seen.add(key)
            version = resolve_unity_app_version(normalized)
            discovered.append((version, normalized))

    discovered.sort(key=lambda item: version_sort_key(item[0]))
    return discovered


def list_process_commands() -> list[tuple[int, str]]:
    return current_host_platform_adapter().list_process_commands()


def try_read_host_editor_session_state(project_root: Path) -> dict[str, Any] | None:
    path = host_editor_session_state_path(project_root)
    if not path.is_file():
        return None

    try:
        data = read_json(path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def write_host_editor_session_state(project_root: Path, data: dict[str, Any]) -> None:
    write_json(host_editor_session_state_path(project_root), data)


def clear_host_editor_session_state(project_root: Path) -> None:
    path = host_editor_session_state_path(project_root)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def try_read_recent_host_editor_launch_in_progress(project_root: Path) -> dict[str, Any] | None:
    session = try_read_host_editor_session_state(project_root)
    if not session or not bool(session.get("opened_by_host")) or not bool(session.get("launch_in_progress")):
        return None

    path = host_editor_session_state_path(project_root)
    try:
        age_seconds = time.time() - path.stat().st_mtime
    except OSError:
        age_seconds = HOST_EDITOR_LAUNCH_IN_PROGRESS_MAX_AGE_SECONDS + 1.0

    if age_seconds > HOST_EDITOR_LAUNCH_IN_PROGRESS_MAX_AGE_SECONDS:
        return None

    session["launch_in_progress_age_seconds"] = round(max(0.0, age_seconds), 3)
    return session


def clear_stale_bridge_state(project_root: Path) -> bool:
    path = bridge_state_path(project_root)
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        return False
    return False


def clear_stale_active_test_run_state(project_root: Path) -> bool:
    path = project_root / "Library" / "XUUnityLightMcp" / "state" / "active_test_run.json"
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        return False
    return False


def _normalized_project_match_key(path_value: str | Path) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    try:
        resolved = str(Path(text).expanduser().resolve())
    except OSError:
        resolved = str(Path(text).expanduser())
    normalized = resolved.replace("\\", "/").rstrip("/")
    if os.name == "nt":
        normalized = normalized.lower()
    return normalized


def extract_unity_project_path_from_command(command: str) -> str:
    normalized_command = str(command or "").replace("\\ ", " ").strip()
    if not normalized_command:
        return ""

    match = re.search(
        r'(?:^|\s)-projectPath\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s].*?))(?=\s+-\w|\s*$)',
        normalized_command,
        re.IGNORECASE,
    )
    if not match:
        return ""

    for group in match.groups():
        value = str(group or "").strip()
        if value:
            return value
    return ""


def unity_command_targets_project(command: str, project_root: Path) -> bool:
    project_path_argument = extract_unity_project_path_from_command(command)
    if not project_path_argument:
        return False
    return _normalized_project_match_key(project_path_argument) == _normalized_project_match_key(project_root)


def find_running_unity_editors_for_project(project_root: Path) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for pid, command in list_process_commands():
        normalized_command = command.replace("\\ ", " ").strip()
        command_for_match = normalized_command.replace("\\", "/")

        if pid <= 0 or pid in seen_pids or not pid_is_alive(pid):
            continue

        if "Unity Hub.app/Contents/MacOS/Unity Hub" in normalized_command:
            continue

        if not (
            "Unity.app/Contents/MacOS/Unity" in normalized_command
            or "Unity.exe" in normalized_command
            or "/Unity " in f"{command_for_match} "
            or command_for_match.endswith("/Unity")
        ):
            continue

        project_path_argument = extract_unity_project_path_from_command(normalized_command)
        if not project_path_argument or not unity_command_targets_project(normalized_command, project_root):
            continue

        unity_app = ""
        unity_version = ""
        app_match = re.search(r"(.+?/Unity\.app)/Contents/MacOS/Unity", normalized_command)
        if app_match:
            unity_app = app_match.group(1)
            unity_version = resolve_unity_app_version(Path(unity_app))
        else:
            windows_match = re.search(r'([A-Za-z]:\\[^"\r\n]*?Unity\.exe)', normalized_command)
            linux_match = re.search(r"((?:/[^\"\s]+)+/Unity)(?:\s|$)", command_for_match)
            if windows_match:
                unity_app = windows_match.group(1)
                unity_version = resolve_unity_app_version(Path(unity_app))
            elif linux_match:
                unity_app = linux_match.group(1)
                unity_version = resolve_unity_app_version(Path(unity_app))

        matches.append(
            {
                "pid": pid,
                "command": normalized_command,
                "project_path": project_path_argument,
                "unity_app": unity_app,
                "unity_version": unity_version,
            }
        )
        seen_pids.add(pid)

    return matches


def find_running_unity_hub_launchers_for_project(project_root: Path) -> list[dict[str, Any]]:
    if host_platform_kind() != "macos":
        return []

    matches: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for pid, command in list_process_commands():
        normalized_command = command.replace("\\ ", " ").strip()

        if pid <= 0 or pid in seen_pids or not pid_is_alive(pid):
            continue

        if "Unity Hub.app/Contents/MacOS/Unity Hub" not in normalized_command:
            continue

        project_path_argument = extract_unity_project_path_from_command(normalized_command)
        if not project_path_argument or not unity_command_targets_project(normalized_command, project_root):
            continue

        matches.append(
            {
                "pid": pid,
                "command": normalized_command,
                "project_path": project_path_argument,
            }
        )
        seen_pids.add(pid)

    return matches


def list_live_project_editor_pids(project_root: Path) -> list[int]:
    pids: set[int] = set()

    bridge_state = try_read_live_editor_state(project_root)
    if bridge_state is not None:
        bridge_pid = int(bridge_state.get("editor_pid") or 0)
        if bridge_pid > 0 and pid_is_alive(bridge_pid):
            pids.add(bridge_pid)

    for editor in find_running_unity_editors_for_project(project_root):
        pid = int(editor.get("pid") or 0)
        if pid > 0 and pid_is_alive(pid):
            pids.add(pid)

    return sorted(pids)


def project_lock_path(project_root: Path) -> Path:
    return project_root / "Temp" / "UnityLockfile"


def try_list_path_owner_pids(path: Path) -> list[int]:
    if not path.is_file():
        return []

    lsof_path = shutil.which("lsof")
    if not lsof_path:
        return []

    try:
        completed = subprocess.run(
            [lsof_path, "-t", "--", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    owner_pids: list[int] = []
    for line in completed.stdout.splitlines():
        raw_value = line.strip()
        if not raw_value:
            continue
        try:
            pid = int(raw_value)
        except ValueError:
            continue
        if pid > 0 and pid not in owner_pids:
            owner_pids.append(pid)
    return owner_pids


def inspect_project_lock(project_root: Path) -> dict[str, Any]:
    lock_path = project_lock_path(project_root)
    present = lock_path.is_file()
    owner_pids = try_list_path_owner_pids(lock_path) if present else []
    live_owner_pids = [pid for pid in owner_pids if pid_is_alive(pid)]

    return {
        "path": str(lock_path),
        "present": present,
        "owner_pids": owner_pids,
        "live_owner_pids": live_owner_pids,
    }


def clear_stale_project_lock(project_root: Path) -> dict[str, Any]:
    lock_state = inspect_project_lock(project_root)
    if not lock_state["present"] or lock_state["live_owner_pids"]:
        lock_state["removed"] = False
        return lock_state

    try:
        Path(lock_state["path"]).unlink()
        lock_state["removed"] = True
        lock_state["present"] = False
    except OSError:
        lock_state["removed"] = False
    return lock_state


def build_host_editor_session_state(
    project_root: Path,
    unity_app: Path,
    log_path: Path,
    background_open: bool,
    editor_pid: int = 0,
) -> dict[str, Any]:
    log_session_start_offset_bytes = 0
    log_session_start_mtime = 0.0
    try:
        if log_path.is_file():
            stat_result = log_path.stat()
            log_session_start_offset_bytes = int(stat_result.st_size or 0)
            log_session_start_mtime = float(stat_result.st_mtime or 0.0)
    except OSError:
        log_session_start_offset_bytes = 0
        log_session_start_mtime = 0.0

    return {
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
        "opened_by_host": True,
        "opened_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "editor_pid": max(0, int(editor_pid or 0)),
        "log_session_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "log_session_start_offset_bytes": log_session_start_offset_bytes,
        "log_session_start_mtime": round(log_session_start_mtime, 6),
        "log_scope_source": "host_opened_editor_session",
    }


def update_host_editor_session_pid(project_root: Path, editor_pid: int) -> None:
    state = try_read_host_editor_session_state(project_root)
    if not state or not bool(state.get("opened_by_host")):
        return

    normalized = dict(state)
    normalized["editor_pid"] = max(0, int(editor_pid or 0))
    write_host_editor_session_state(project_root, normalized)


def detect_unity_app_path(explicit_path: str | None) -> Path:
    if explicit_path:
        normalized = normalize_unity_installation_path(Path(explicit_path))
        if normalized is None:
            raise ToolInvocationError("unity_app_not_found", f"Unity installation not found: {explicit_path}")
        return normalized

    candidates = discover_unity_installations()
    if not candidates:
        raise ToolInvocationError(
            "unity_app_not_found",
            (
                "Could not auto-detect a Unity installation. "
                f"Check the default Unity Hub install locations for {host_platform_kind()} "
                f"or set {UNITY_EDITOR_ROOTS_ENV} to one or more custom roots."
            ),
        )
    return candidates[-1][1]


def read_project_unity_version(project_root: Path) -> str | None:
    version_path = project_root / "ProjectSettings" / "ProjectVersion.txt"
    if not version_path.is_file():
        return None

    try:
        for line in version_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("m_EditorVersion:"):
                version = line.split(":", 1)[1].strip()
                return version or None
    except OSError:
        return None

    return None


def detect_unity_app_path_for_project(project_root: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return detect_unity_app_path(explicit_path)

    project_version = read_project_unity_version(project_root)
    if project_version:
        for version, candidate in discover_unity_installations():
            if version == project_version:
                return candidate

    return detect_unity_app_path(None)


def activate_unity_editor(project_root: Path, explicit_unity_app: Path | None = None) -> dict[str, Any]:
    unity_app = explicit_unity_app or detect_unity_app_path_for_project(project_root, None)
    if host_platform_kind() == "macos":
        try:
            subprocess.run(["open", str(unity_app)], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            detail = stderr or stdout or str(exc)
            raise ToolInvocationError(
                "unity_editor_activation_failed",
                (
                    f"Failed to activate Unity editor at {unity_app}. "
                    f"Command: open {unity_app}. Detail: {detail}"
                ),
            ) from exc
    time.sleep(ACTIVATION_DELAY_SECONDS)
    return {
        "unity_app": str(unity_app),
        "activation_delay_seconds": ACTIVATION_DELAY_SECONDS,
    }


def try_find_matching_editor_process(project_root: Path, unity_app: Path) -> dict[str, Any] | None:
    requested_version = resolve_unity_app_version(unity_app)
    matches = find_running_unity_editors_for_project(project_root)
    if not matches:
        return None

    if requested_version:
        for match in matches:
            if str(match.get("unity_version") or "") == requested_version:
                return match

    return matches[0]


def wait_for_matching_editor_process(
    project_root: Path,
    unity_app: Path,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    deadline = time.time() + max(1.0, timeout_seconds)
    while time.time() < deadline:
        match = try_find_matching_editor_process(project_root, unity_app)
        if match is not None:
            return match
        time.sleep(0.25)
    return None


def terminate_project_hub_launchers(project_root: Path, timeout_ms: int) -> list[int]:
    terminated: list[int] = []
    for launcher in find_running_unity_hub_launchers_for_project(project_root):
        pid = int(launcher.get("pid") or 0)
        if pid > 0 and terminate_editor_pid(pid, timeout_ms):
            terminated.append(pid)
    return terminated


def bridge_state_is_ready(state: dict[str, Any] | None, heartbeat_max_age_seconds: int) -> bool:
    if not isinstance(state, dict):
        return False

    pid = int(state.get("editor_pid") or 0)
    age_seconds = heartbeat_age_seconds(state)
    return (
        pid_is_alive(pid)
        and age_seconds is not None
        and age_seconds <= heartbeat_max_age_seconds
        and state.get("health_status") == "healthy"
        and not bool(state.get("is_compiling"))
    )


def classify_editor_log(log_text: str, startup_policy: str) -> tuple[str, str] | None:
    if not log_text:
        return None

    if "Project has invalid dependencies:" in log_text or "An error occurred while resolving packages:" in log_text:
        return (
            "package_resolution_failed",
            "Unity package resolution failed. Inspect Editor.log for invalid dependencies, git package errors, or registry failures.",
        )

    if "Could not clone [" in log_text:
        return (
            "package_resolution_failed",
            "Unity could not clone a git package dependency. Inspect Editor.log for the failing dependency URL or commit hash.",
        )

    if "error CS" in log_text or "AssetDatabase: script compilation time:" in log_text and "error CS" in log_text:
        if startup_policy == "batch_compile_lane":
            return (
                "interactive_compile_block_detected",
                "Interactive Unity startup is blocked by compilation errors. Use the batch compile lane for compile-only validation or fix the compile errors first.",
            )

        if startup_policy == "auto_enter_safe_mode_preferred":
            return (
                "safe_mode_manual_required",
                "Compilation errors were detected during startup. This host-side wrapper cannot click the Safe Mode dialog. Prefer auto-enter Safe Mode in Unity preferences or reopen manually into Safe Mode.",
            )

        return (
            "interactive_compile_block_detected",
            "Compilation errors were detected during interactive startup. This wrapper is failing fast instead of waiting for a bridge heartbeat that cannot become healthy.",
        )

    return None


def resolve_editor_log_path(project_root: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    return default_editor_log_path(project_root)


def sanitize_filename_component(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "item"

    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return sanitized.strip("._-") or "item"


def default_batch_build_log_path(project_root: Path, build_target: str) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return logs_dir(project_root) / "batch" / f"{timestamp}_{sanitize_filename_component(build_target)}.log"


def default_batch_build_result_path(project_root: Path, build_target: str) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return logs_dir(project_root) / "batch" / f"{timestamp}_{sanitize_filename_component(build_target)}_result.json"


def default_batch_operation_log_path(project_root: Path, operation_name: str) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return logs_dir(project_root) / "batch" / f"{timestamp}_{sanitize_filename_component(operation_name)}.log"


def default_batch_operation_result_path(project_root: Path, operation_name: str) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return logs_dir(project_root) / "batch" / f"{timestamp}_{sanitize_filename_component(operation_name)}_result.json"


def resolve_batch_build_output_path(project_root: Path, explicit_path: str | None) -> str:
    if not explicit_path:
        return ""

    path = Path(explicit_path).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return str(path.resolve())


def read_recent_editor_log(log_path: Path, command_started_at: float) -> str:
    if not log_path.is_file():
        return ""

    try:
        stat = log_path.stat()
    except OSError:
        return ""

    if stat.st_mtime < command_started_at - 1.0:
        return ""

    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    if len(text) > 200000:
        return text[-200000:]
    return text


def open_unity_editor(project_root: Path, log_path: Path, unity_app: Path, background_open: bool) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    live_state = try_read_live_editor_state(project_root)
    if live_state is not None:
        requested_version = resolve_unity_app_version(unity_app)
        running_version = str(live_state.get("unity_version") or "")
        if requested_version and running_version and requested_version != running_version:
            raise ToolInvocationError(
                "project_already_open_with_different_unity_version",
                (
                    "This project already appears open in Unity "
                    f"{running_version} (pid {live_state.get('editor_pid')}). "
                    f"Requested Unity version is {requested_version}. "
                    "Close the running editor instance for this project before opening a different version."
                ),
            )

        return {
            "unity_app": str(unity_app),
            "editor_log_path": str(log_path),
            "background_open": background_open,
            "reused_existing_editor": True,
            "editor_pid": live_state.get("editor_pid"),
            "unity_version": running_version,
        }

    detected_editors = find_running_unity_editors_for_project(project_root)
    if detected_editors:
        requested_version = resolve_unity_app_version(unity_app)
        detected_versions = sorted(
            {
                str(editor.get("unity_version") or "").strip()
                for editor in detected_editors
                if str(editor.get("unity_version") or "").strip()
            }
        )
        if requested_version and detected_versions and requested_version not in detected_versions:
            raise ToolInvocationError(
                "project_already_open_with_different_unity_version",
                (
                    "This project already appears open in Unity "
                    f"{', '.join(detected_versions)} (pid {detected_editors[0]['pid']}). "
                    f"Requested Unity version is {requested_version}. "
                    "Close the running editor instance for this project before opening a different version."
                ),
            )

        detected_unity_app = str(detected_editors[0].get("unity_app") or unity_app)
        try:
            activate_unity_editor(project_root, Path(detected_unity_app))
        except Exception:
            pass

        return {
            "unity_app": detected_unity_app,
            "editor_log_path": str(log_path),
            "background_open": background_open,
            "reused_existing_editor": True,
            "reused_via": "project_process_detection",
            "bridge_available": False,
            "editor_pid": detected_editors[0]["pid"],
            "unity_version": str(detected_editors[0].get("unity_version") or requested_version or ""),
            "matching_editor_pids": [int(editor["pid"]) for editor in detected_editors],
        }

    launch_in_progress = try_read_recent_host_editor_launch_in_progress(project_root)
    if launch_in_progress is not None:
        return {
            "unity_app": str(launch_in_progress.get("unity_app") or unity_app),
            "editor_log_path": str(launch_in_progress.get("editor_log_path") or log_path),
            "background_open": bool(launch_in_progress.get("background_open")),
            "reused_existing_editor": True,
            "reused_via": "host_launch_in_progress",
            "opened_by_host": True,
            "launch_in_progress": True,
            "launch_in_progress_age_seconds": launch_in_progress.get("launch_in_progress_age_seconds"),
            "editor_pid": int(launch_in_progress.get("editor_pid") or 0),
        }

    lock_state = inspect_project_lock(project_root)
    if lock_state["present"]:
        live_owner_pids = lock_state["live_owner_pids"]
        if live_owner_pids:
            raise ToolInvocationError(
                "project_already_open_without_bridge",
                (
                    "This project already appears open in Unity, but no reusable MCP bridge session is currently "
                    f"available. Project lock: {lock_state['path']}. "
                    f"Live lock owner pid(s): {', '.join(str(pid) for pid in live_owner_pids)}. "
                    "Focus or recover the running editor instead of launching a second instance."
                ),
            )
        cleared_lock_state = clear_stale_project_lock(project_root)
        if cleared_lock_state.get("present"):
            raise ToolInvocationError(
                "project_lock_present_without_bridge",
                (
                    "This project has a Unity lock file, but no reusable MCP bridge session is currently available. "
                    f"Project lock: {lock_state['path']}. "
                    "Another Unity instance may already own the project, or the editor may have exited uncleanly. "
                "Resolve the running editor or clear the stale lock before retrying."
                ),
            )

    launch_session = build_host_editor_session_state(project_root, unity_app, log_path, background_open, 0)
    launch_session["launch_in_progress"] = True
    write_host_editor_session_state(project_root, launch_session)

    launched_pid = 0
    launch_command: list[str]
    try:
        if host_platform_kind() == "macos":
            launch_command = ["open"]
            if background_open:
                launch_command.append("-g")
            launch_command.extend(
                [
                    "-na",
                    str(unity_app),
                    "--args",
                    "-projectPath",
                    str(project_root),
                    "-logFile",
                    str(log_path),
                ]
            )
            try:
                subprocess.run(launch_command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                stdout = (exc.stdout or "").strip()
                detail = stderr or stdout or str(exc)
                raise ToolInvocationError(
                    "unity_editor_launch_failed",
                    (
                        f"Failed to launch Unity editor at {unity_app}. "
                        f"Command: {' '.join(launch_command)}. Detail: {detail}"
                    ),
                ) from exc

            launched_editor = wait_for_matching_editor_process(project_root, unity_app, 15.0)
            if launched_editor is None:
                hub_launchers = find_running_unity_hub_launchers_for_project(project_root)
                terminated_hub_pids = terminate_project_hub_launchers(project_root, 5000) if hub_launchers else []
                hub_pids = [int(launcher.get("pid") or 0) for launcher in hub_launchers]
                raise ToolInvocationError(
                    "editor_process_not_observed_after_launch",
                    (
                        f"Unity launch command completed but no matching editor process was observed for project {project_root}. "
                        f"Resolved unity_app: {unity_app}. "
                        f"Command: {' '.join(launch_command)}. "
                        f"Observed Unity Hub launcher pid(s): {hub_pids or []}. "
                        f"Terminated stale Hub launcher pid(s): {terminated_hub_pids or []}."
                    ),
                )
            launched_pid = int(launched_editor["pid"])
        else:
            unity_executable = resolve_unity_executable(unity_app)
            launch_command = [
                str(unity_executable),
                "-projectPath",
                str(project_root),
                "-logFile",
                str(log_path),
            ]
            popen_kwargs: dict[str, Any] = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL,
                "close_fds": True,
            }
            if os.name == "nt":
                creation_flags = 0
                detached_process = getattr(subprocess, "DETACHED_PROCESS", 0)
                new_process_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if background_open:
                    creation_flags |= detached_process
                creation_flags |= new_process_group
                if creation_flags:
                    popen_kwargs["creationflags"] = creation_flags
            else:
                popen_kwargs["start_new_session"] = True

            process = subprocess.Popen(launch_command, **popen_kwargs)
            launched_pid = int(process.pid or 0)
    except Exception:
        clear_host_editor_session_state(project_root)
        raise

    write_host_editor_session_state(
        project_root,
        build_host_editor_session_state(project_root, unity_app, log_path, background_open, launched_pid),
    )
    return {
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
        "opened_by_host": True,
        "editor_pid": launched_pid,
        "launch_command": [str(part) for part in launch_command],
    }


def build_plain_batch_build_command(
    project_root: Path,
    unity_app: Path,
    log_path: Path,
    result_path: Path,
    build_target: str,
    output_path: str,
    scene_paths: list[str],
    build_options: list[str],
) -> list[str]:
    unity_binary = resolve_unity_executable(unity_app)

    command = [
        str(unity_binary),
        "-batchmode",
        "-quit",
        "-projectPath",
        str(project_root),
        "-buildTarget",
        build_target,
        "-logFile",
        str(log_path),
        "-executeMethod",
        "XUUnity.LightMcp.Editor.Batch.XUUnityLightMcpBatchBuildCli.ExecuteFromCommandLine",
        "--",
        "--xuunity-build-target",
        build_target,
        "--xuunity-result-file",
        str(result_path),
    ]

    if output_path:
        command.extend(["--xuunity-output-path", output_path])
    for scene_path in scene_paths:
        command.extend(["--xuunity-scene-path", scene_path])
    for build_option in build_options:
        command.extend(["--xuunity-build-option", build_option])

    return command


def build_batch_validation_command(
    project_root: Path,
    unity_app: Path,
    log_path: Path,
    result_path: Path,
    action: str,
    extra_args: list[str] | None = None,
) -> list[str]:
    unity_binary = resolve_unity_executable(unity_app)
    command = [
        str(unity_binary),
        "-batchmode",
        "-projectPath",
        str(project_root),
        "-logFile",
        str(log_path),
        "-executeMethod",
        "XUUnity.LightMcp.Editor.Batch.XUUnityLightMcpBatchValidationCli.ExecuteFromCommandLine",
        "--",
        "--xuunity-batch-action",
        action,
        "--xuunity-result-file",
        str(result_path),
    ]

    if extra_args:
        command.extend(extra_args)
    return command


def terminate_editor_pid(pid: int, timeout_ms: int) -> bool:
    if pid <= 0 or not pid_is_alive(pid):
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return not pid_is_alive(pid)

    deadline = time.time() + (max(1000, timeout_ms) / 1000.0)
    while time.time() < deadline:
        if not pid_is_alive(pid):
            return True
        time.sleep(0.2)

    return not pid_is_alive(pid)


def wait_for_project_editor_exit(
    project_root: Path,
    *,
    tracked_pid: int,
    current_pid: int,
    timeout_ms: int,
) -> tuple[bool, list[int]]:
    deadline = time.time() + (max(1000, timeout_ms) / 1000.0)
    live_project_pids: list[int] = []
    while time.time() < deadline:
        live_project_pids = list_live_project_editor_pids(project_root)
        tracked_alive = tracked_pid > 0 and pid_is_alive(tracked_pid)
        current_alive = current_pid > 0 and pid_is_alive(current_pid)
        if (
            not tracked_alive
            and not current_alive
            and (tracked_pid <= 0 or tracked_pid not in live_project_pids)
            and (current_pid <= 0 or current_pid not in live_project_pids)
        ):
            return True, live_project_pids
        time.sleep(0.2)

    return False, list_live_project_editor_pids(project_root)


def restore_host_opened_editor_state(
    project_root: Path,
    timeout_ms: int,
    request_editor_quit: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any]:
    session = try_read_host_editor_session_state(project_root)
    if not session or not bool(session.get("opened_by_host")):
        return {
            "project_root": str(project_root),
            "host_opened_session_found": False,
            "restored": False,
            "closeout_verified": True,
            "closeout_classification": "not_opened_by_host",
            "recommended_next_action": "none",
            "reason": "not_opened_by_host",
        }

    tracked_pid = int(session.get("editor_pid") or 0)
    live_state = try_read_live_editor_state(project_root)
    current_pid = int((live_state or {}).get("editor_pid") or 0)
    managed_pid = tracked_pid if tracked_pid > 0 else current_pid
    bounded_timeout_ms = max(1000, timeout_ms)
    quit_wait_timeout_ms = max(1000, bounded_timeout_ms // 2)
    sigterm_timeout_ms = max(1000, bounded_timeout_ms - quit_wait_timeout_ms)
    restoration = {
        "project_root": str(project_root),
        "host_opened_session_found": True,
        "tracked_editor_pid": tracked_pid,
        "live_state_editor_pid": current_pid,
        "restored": False,
        "closeout_verified": False,
        "closeout_classification": "",
        "recommended_next_action": "inspect_project_editor_processes",
        "reason": "",
        "close_path": "",
    }

    if current_pid > 0 and (tracked_pid <= 0 or current_pid == tracked_pid):
        restoration["quit_request_attempted"] = True
        try:
            quit_response = request_editor_quit(str(project_root), bounded_timeout_ms)
            restoration["quit_request_accepted"] = quit_response.get("status") == "ok"
            restoration["quit_request_id"] = str(quit_response.get("request_id") or "")
            restoration["quit_request_status"] = str(quit_response.get("status") or "")
        except ToolInvocationError as exc:
            restoration["quit_request_error"] = {
                "code": exc.code,
                "message": exc.message,
            }
            if exc.details:
                restoration["quit_request_error"]["details"] = dict(exc.details)
            restoration["quit_request_id"] = str((exc.details or {}).get("request_id") or "")
            restoration["quit_request_status"] = "error"

        quit_request_id = str(restoration.get("quit_request_id") or "")
        if quit_request_id:
            restoration["recommended_recovery_command"] = (
                f"request-final-status --project-root {project_root} --request-id {quit_request_id}"
            )

        closed_after_quit, live_project_pids = wait_for_project_editor_exit(
            project_root,
            tracked_pid=tracked_pid,
            current_pid=current_pid,
            timeout_ms=quit_wait_timeout_ms,
        )
        if closed_after_quit:
            clear_host_editor_session_state(project_root)
            restoration["stale_bridge_state_cleared"] = clear_stale_bridge_state(project_root)
            restoration["stale_active_test_run_cleared"] = clear_stale_active_test_run_state(project_root)
            restoration["restored"] = True
            restoration["closeout_verified"] = True
            restoration["closeout_classification"] = "closed_via_unity_editor_quit"
            restoration["recommended_next_action"] = "none"
            restoration["reason"] = "host_opened_editor_closed"
            restoration["close_path"] = "unity.editor.quit"
            restoration["closed_editor_pid"] = current_pid
            restoration["live_project_editor_pids"] = live_project_pids
            clear_stale_project_lock(project_root)
            return restoration

    if managed_pid > 0 and terminate_editor_pid(managed_pid, sigterm_timeout_ms):
        live_project_pids = list_live_project_editor_pids(project_root)
        if managed_pid not in live_project_pids:
            clear_host_editor_session_state(project_root)
            restoration["stale_bridge_state_cleared"] = clear_stale_bridge_state(project_root)
            restoration["stale_active_test_run_cleared"] = clear_stale_active_test_run_state(project_root)
            restoration["restored"] = True
            restoration["closeout_verified"] = True
            restoration["reason"] = "host_opened_editor_closed"
            restoration["recommended_next_action"] = "none"
            if bool(restoration.get("quit_request_attempted")) and bool(restoration.get("quit_request_accepted")):
                restoration["closeout_classification"] = "quit_ack_without_exit_sigterm_recovered"
                restoration["close_path"] = "unity.editor.quit+host_sigterm"
            elif bool(restoration.get("quit_request_attempted")):
                restoration["closeout_classification"] = "quit_request_failed_host_sigterm_recovered"
                restoration["close_path"] = "failed_quit_request+host_sigterm"
            else:
                restoration["closeout_classification"] = "closed_via_host_sigterm"
                restoration["close_path"] = "host_sigterm"
            restoration["closed_editor_pid"] = managed_pid
            restoration["live_project_editor_pids"] = live_project_pids
            clear_stale_project_lock(project_root)
            return restoration

    if managed_pid > 0 and not pid_is_alive(managed_pid):
        live_project_pids = list_live_project_editor_pids(project_root)
        if not live_project_pids:
            terminated_hub_pids = terminate_project_hub_launchers(project_root, timeout_ms)
            clear_host_editor_session_state(project_root)
            restoration["stale_bridge_state_cleared"] = clear_stale_bridge_state(project_root)
            restoration["stale_active_test_run_cleared"] = clear_stale_active_test_run_state(project_root)
            restoration["restored"] = False
            restoration["closeout_verified"] = True
            restoration["closeout_classification"] = "tracked_editor_already_closed"
            restoration["recommended_next_action"] = "none"
            restoration["reason"] = "tracked_editor_already_closed"
            restoration["terminated_hub_launcher_pids"] = terminated_hub_pids
            return restoration

        if bool(restoration.get("quit_request_attempted")) and bool(restoration.get("quit_request_accepted")):
            restoration["closeout_classification"] = "quit_ack_without_exit"
            restoration["reason"] = "quit_request_completed_without_process_exit"
            restoration["recommended_next_action"] = (
                "inspect_quit_request_final_status"
                if restoration.get("recommended_recovery_command")
                else "manual_editor_close"
            )
        else:
            restoration["closeout_classification"] = "project_editor_still_running_untracked"
            restoration["reason"] = "project_editor_still_running_untracked"
        restoration["live_project_editor_pids"] = live_project_pids
        return restoration

    if bool(restoration.get("quit_request_attempted")) and bool(restoration.get("quit_request_accepted")):
        restoration["closeout_classification"] = "quit_ack_without_exit"
        restoration["reason"] = "quit_request_completed_without_process_exit"
        restoration["recommended_next_action"] = (
            "inspect_quit_request_final_status"
            if restoration.get("recommended_recovery_command")
            else "manual_editor_close"
        )
    elif bool(restoration.get("quit_request_attempted")):
        restoration["closeout_classification"] = "quit_request_failed_editor_still_running"
        restoration["reason"] = "quit_request_failed_editor_still_running"
        restoration["recommended_next_action"] = (
            "inspect_quit_request_final_status"
            if restoration.get("recommended_recovery_command")
            else "manual_editor_close"
        )
    else:
        restoration["closeout_classification"] = "tracked_editor_still_running"
        restoration["reason"] = "tracked_editor_still_running"
    restoration["live_project_editor_pids"] = list_live_project_editor_pids(project_root)
    return restoration


def wait_for_ready(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    startup_policy: str,
    editor_log_path: Path,
) -> dict[str, Any]:
    if startup_policy not in STARTUP_POLICIES:
        raise ToolInvocationError("invalid_startup_policy", f"Unknown startup policy: {startup_policy}")

    if not bridge_enabled(project_root):
        raise ToolInvocationError(
            "bridge_disabled",
            (
                "Unity bridge is disabled for this project. "
                "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                "and reopen Unity."
            ),
        )

    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    state: dict[str, Any] | None = None
    while time.time() < deadline:
        state = try_read_bridge_state(project_root)
        if bridge_state_is_ready(state, heartbeat_max_age_seconds):
            age_seconds = heartbeat_age_seconds(state)
            state["startup_policy"] = startup_policy
            state["editor_log_path"] = str(editor_log_path)
            state["heartbeat_age_seconds"] = round(age_seconds or 0.0, 3)
            return state

        classification = classify_editor_log(read_recent_editor_log(editor_log_path, started_at), startup_policy)
        if classification:
            code, message = classification
            raise ToolInvocationError(code, message)

        time.sleep(1.0)

    raise ToolInvocationError(
        "editor_ready_timeout",
        (
            "Timed out waiting for a healthy Unity bridge heartbeat. "
            f"Last inspected log: {editor_log_path}. "
            f"Bridge state present: {bool(state)}. "
            f"Running editor pid(s): {[int(editor.get('pid') or 0) for editor in find_running_unity_editors_for_project(project_root)]}. "
            f"Running Unity Hub launcher pid(s): {[int(launcher.get('pid') or 0) for launcher in find_running_unity_hub_launchers_for_project(project_root)]}. "
            f"Host session: {try_read_host_editor_session_state(project_root) or {}}"
        ),
    )
