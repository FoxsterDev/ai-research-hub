#!/usr/bin/env python3
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from server_bridge_runtime import (
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
from server_specs import STARTUP_POLICIES

ACTIVATION_DELAY_SECONDS = 0.35


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


def find_running_unity_editors_for_project(project_root: Path) -> list[dict[str, Any]]:
    target_path = str(project_root)
    marker = f"-projectPath {target_path}"

    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    matches: list[dict[str, Any]] = []
    seen_pids: set[int] = set()
    for line in completed.stdout.splitlines():
        line = line.rstrip()
        if not line:
            continue

        parts = line.lstrip().split(None, 1)
        if len(parts) != 2:
            continue

        raw_pid, command = parts
        try:
            pid = int(raw_pid)
        except ValueError:
            continue

        if pid <= 0 or pid in seen_pids or not pid_is_alive(pid):
            continue

        if "Unity.app/Contents/MacOS/Unity" not in command:
            continue

        normalized_command = command.replace("\\ ", " ")
        if marker not in normalized_command and target_path not in normalized_command:
            continue

        unity_app = ""
        unity_version = ""
        app_match = re.search(r"(.+?/Unity\.app)/Contents/MacOS/Unity", normalized_command)
        if app_match:
            unity_app = app_match.group(1)
            try:
                unity_version = Path(unity_app).parent.name
            except Exception:
                unity_version = ""

        matches.append(
            {
                "pid": pid,
                "command": normalized_command,
                "unity_app": unity_app,
                "unity_version": unity_version,
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
    return {
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "editor_log_path": str(log_path),
        "background_open": background_open,
        "opened_by_host": True,
        "opened_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "editor_pid": max(0, int(editor_pid or 0)),
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
        path = Path(explicit_path).expanduser().resolve()
        if not path.is_dir():
            raise ToolInvocationError("unity_app_not_found", f"Unity app not found: {path}")
        return path

    candidates = sorted(Path("/Applications/Unity/Hub/Editor").glob("*/Unity.app"))
    if not candidates:
        raise ToolInvocationError(
            "unity_app_not_found",
            "Could not auto-detect a Unity.app under /Applications/Unity/Hub/Editor. Pass --unity-app explicitly.",
        )
    return candidates[-1]


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
        exact_match = Path("/Applications/Unity/Hub/Editor") / project_version / "Unity.app"
        if exact_match.is_dir():
            return exact_match.resolve()

    return detect_unity_app_path(None)


def resolve_unity_app_version(unity_app: Path) -> str:
    return unity_app.parent.name


def activate_unity_editor(project_root: Path, explicit_unity_app: Path | None = None) -> dict[str, Any]:
    unity_app = explicit_unity_app or detect_unity_app_path_for_project(project_root, None)
    subprocess.run(["open", "-a", str(unity_app)], check=True)
    time.sleep(ACTIVATION_DELAY_SECONDS)
    return {
        "unity_app": str(unity_app),
        "activation_delay_seconds": ACTIVATION_DELAY_SECONDS,
    }


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

    command = ["open"]
    if background_open:
        command.append("-g")
    command.extend(
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

    subprocess.run(command, check=True)
    launched_editors = find_running_unity_editors_for_project(project_root)
    launched_pid = int(launched_editors[0]["pid"]) if launched_editors else 0
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
    unity_binary = unity_app / "Contents" / "MacOS" / "Unity"
    if not unity_binary.is_file():
        raise ToolInvocationError("unity_binary_not_found", f"Unity binary not found: {unity_binary}")

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


def restore_host_opened_editor_state(
    project_root: Path,
    timeout_ms: int,
    request_editor_quit: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any]:
    session = try_read_host_editor_session_state(project_root)
    if not session or not bool(session.get("opened_by_host")):
        return {
            "project_root": str(project_root),
            "restored": False,
            "reason": "not_opened_by_host",
        }

    tracked_pid = int(session.get("editor_pid") or 0)
    live_state = try_read_live_editor_state(project_root)
    restoration = {
        "project_root": str(project_root),
        "tracked_editor_pid": tracked_pid,
        "restored": False,
        "reason": "",
        "close_path": "",
    }

    if live_state is not None:
        current_pid = int(live_state.get("editor_pid") or 0)
        if current_pid > 0 and (tracked_pid <= 0 or current_pid == tracked_pid):
            request_editor_quit(str(project_root), timeout_ms)
            deadline = time.time() + (max(1000, timeout_ms) / 1000.0)
            while time.time() < deadline:
                live_project_pids = list_live_project_editor_pids(project_root)
                if not pid_is_alive(current_pid) and current_pid not in live_project_pids:
                    clear_host_editor_session_state(project_root)
                    restoration["restored"] = True
                    restoration["reason"] = "host_opened_editor_closed"
                    restoration["close_path"] = "unity.editor.quit"
                    restoration["closed_editor_pid"] = current_pid
                    clear_stale_project_lock(project_root)
                    return restoration
                time.sleep(0.2)

    if tracked_pid > 0 and terminate_editor_pid(tracked_pid, timeout_ms):
        live_project_pids = list_live_project_editor_pids(project_root)
        if tracked_pid not in live_project_pids:
            clear_host_editor_session_state(project_root)
            restoration["restored"] = True
            restoration["reason"] = "host_opened_editor_closed"
            restoration["close_path"] = "host_sigterm"
            restoration["closed_editor_pid"] = tracked_pid
            clear_stale_project_lock(project_root)
            return restoration

    if tracked_pid > 0 and not pid_is_alive(tracked_pid):
        live_project_pids = list_live_project_editor_pids(project_root)
        if not live_project_pids:
            clear_host_editor_session_state(project_root)
            restoration["restored"] = False
            restoration["reason"] = "tracked_editor_already_closed"
            return restoration

        restoration["reason"] = "project_editor_still_running_untracked"
        restoration["live_project_editor_pids"] = live_project_pids
        return restoration

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
    while time.time() < deadline:
        state = try_read_bridge_state(project_root)
        if state:
            pid = int(state.get("editor_pid") or 0)
            age_seconds = heartbeat_age_seconds(state)
            if (
                pid_is_alive(pid)
                and age_seconds is not None
                and age_seconds <= heartbeat_max_age_seconds
                and state.get("health_status") == "healthy"
                and not bool(state.get("is_compiling"))
            ):
                state["startup_policy"] = startup_policy
                state["editor_log_path"] = str(editor_log_path)
                state["heartbeat_age_seconds"] = round(age_seconds, 3)
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
            f"Last inspected log: {editor_log_path}"
        ),
    )
