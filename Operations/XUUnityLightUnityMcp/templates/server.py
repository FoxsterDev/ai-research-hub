#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from server_build_config import build_compile_matrix_args_from_build_config
from server_bridge_runtime import (
    DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
    DEFAULT_IDLE_STABLE_CYCLES,
    active_scenario_run_path,
    annotate_bridge_state_with_liveness,
    build_bridge_stabilization_summary,
    build_request_final_status,
    bridge_enabled,
    bridge_identity_from_state,
    bridge_root,
    bridge_state_path,
    captures_dir,
    default_editor_log_path,
    derive_busy_reason,
    expected_playmode_state_for_action,
    heartbeat_age_seconds,
    inspect_bridge_state_liveness,
    invoke_bridge_transport,
    logs_dir,
    maybe_record_settle_lifecycle_transition,
    parse_journal_utc_timestamp,
    pid_is_alive,
    read_best_effort_bridge_state,
    request_journal_dir,
    scenario_results_dir,
    summarize_state_for_error,
    try_read_bridge_state,
    try_read_live_editor_state,
    wait_for_editor_idle,
    wait_for_playmode_state,
)
from server_core import ToolInvocationError, read_json, write_json
from server_editor_host import (
    activate_unity_editor,
    bridge_state_is_ready,
    build_batch_validation_command,
    build_plain_batch_build_command,
    clear_stale_project_lock,
    default_batch_build_log_path,
    default_batch_operation_log_path,
    default_batch_operation_result_path,
    default_batch_build_result_path,
    detect_unity_app_path_for_project,
    list_live_project_editor_pids,
    open_unity_editor,
    read_recent_editor_log,
    resolve_batch_build_output_path,
    resolve_editor_log_path,
    restore_host_opened_editor_state,
    try_read_host_editor_session_state,
    update_host_editor_session_pid,
    wait_for_ready,
)
from server_specs import (
    OPERATION_LIFECYCLE_POLICIES,
    SCENARIO_DEFINITION_SCHEMA,
    SCENARIO_TERMINAL_STATUSES,
    STARTUP_POLICIES,
    TOOLS,
)
from server_runtime_config import (
    build_runtime_config_report,
    resolve_operation_default_timeout_ms,
    resolve_operation_lifecycle_policy_overrides,
)
from server_summaries import (
    build_scenario_result_summary,
    build_status_summary,
    normalize_scenario_payload,
    prune_project_artifacts,
    try_read_json_dict,
    truncate_text,
)

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {
    "name": "xuunity-light-unity-mcp",
    "version": "0.3.9",
}
LIGHTWEIGHT_PACKAGE_NAME = "com.xuunity.light-mcp"
LIGHTWEIGHT_PACKAGE_TEMPLATE_MARKER = Path(
    "AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/package.json"
)

def ensure_project_root(project_root: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not (root / "Assets").is_dir() or not (root / "ProjectSettings" / "ProjectVersion.txt").is_file():
        raise ToolInvocationError("project_not_found", f"Not a Unity project root: {root}")
    return root


def find_latest_request_event(
    project_root: Path,
    operations: list[str] | None = None,
) -> dict[str, Any] | None:
    journal_dir = request_journal_dir(project_root)
    if not journal_dir.is_dir():
        return None

    normalized_operations = {
        str(operation).strip()
        for operation in (operations or [])
        if str(operation).strip()
    }

    matched: list[dict[str, Any]] = []
    for path in journal_dir.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            continue

        operation = str(payload.get("operation") or "").strip()
        if normalized_operations and operation not in normalized_operations:
            continue

        event = dict(payload)
        event["_path"] = str(path)
        matched.append(event)

    matched.sort(
        key=lambda item: (
            parse_journal_utc_timestamp(item.get("event_at_utc")),
            str(item.get("event_id") or ""),
        )
    )
    return matched[-1] if matched else None


def find_repo_local_package_source(project_root: Path) -> Path | None:
    for candidate_root in (project_root, *project_root.parents):
        marker = candidate_root / LIGHTWEIGHT_PACKAGE_TEMPLATE_MARKER
        if marker.is_file():
            return marker.parent.resolve()
    return None


def inspect_package_dependency_alignment(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "Packages" / "manifest.json"
    package_source = find_repo_local_package_source(project_root)
    result: dict[str, Any] = {
        "package_name": LIGHTWEIGHT_PACKAGE_NAME,
        "manifest_path": str(manifest_path),
        "dependency": "",
        "dependency_mode": "missing",
        "repo_local_package_source": str(package_source) if package_source else "",
        "repo_local_package_source_present": package_source is not None,
        "alignment": "unknown",
        "warning": "",
    }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["alignment"] = "manifest_unreadable"
        result["warning"] = f"Could not inspect manifest dependency: {exc}"
        return result

    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict):
        result["alignment"] = "dependencies_missing"
        result["warning"] = "Packages/manifest.json does not contain a dependencies object."
        return result

    dependency_value = dependencies.get(LIGHTWEIGHT_PACKAGE_NAME)
    if not isinstance(dependency_value, str) or not dependency_value.strip():
        result["alignment"] = "dependency_missing"
        result["warning"] = f"{LIGHTWEIGHT_PACKAGE_NAME} is not declared in Packages/manifest.json."
        return result

    dependency_value = dependency_value.strip()
    result["dependency"] = dependency_value

    if dependency_value.startswith("file:"):
        result["dependency_mode"] = "file"
        dependency_path = (manifest_path.parent / dependency_value[len("file:"):]).resolve()
        result["resolved_dependency_path"] = str(dependency_path)
        if package_source is None:
            result["alignment"] = "file_no_repo_local_reference"
        elif dependency_path == package_source:
            result["alignment"] = "aligned"
        else:
            result["alignment"] = "file_mismatch"
            result["warning"] = (
                "The project uses a file dependency, but it does not point at the repo-local "
                "AIRoot XUUnityLightUnityMcp template package."
            )
        return result

    if dependency_value.startswith(("http://", "https://", "git@", "ssh://")):
        result["dependency_mode"] = "git_or_remote"
    else:
        result["dependency_mode"] = "other"

    if package_source is not None:
        result["alignment"] = "repo_local_source_not_loaded"
        result["warning"] = (
            "A repo-local AIRoot XUUnityLightUnityMcp package source exists, but the project manifest "
            "does not currently load it through a file dependency."
        )
    else:
        result["alignment"] = "external_only"

    return result

def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=True)
    sys.stdout.write("\n")


def emit_tool_error_summary(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        return

    error = payload.get("error")
    if not isinstance(error, dict):
        return

    code = str(error.get("code") or "")
    message = first_non_empty_line(str(error.get("message") or ""), limit=200)
    request_id = str(payload.get("request_id") or "")
    request_submitted = payload.get("request_submitted")
    request_ownership_acquired = payload.get("request_ownership_acquired")
    recommended_next_action = str(payload.get("recommended_next_action") or "")
    recommended_recovery_command = str(payload.get("recommended_recovery_command") or "")
    transport_outcome = str(payload.get("transport_outcome") or "")
    operation_outcome = str(payload.get("operation_outcome") or "")

    parts = ["[xuunity-light-unity-mcp] request_failure"]
    if code:
        parts.append(f"code={code}")
    if request_submitted is not None:
        parts.append(f"request_submitted={str(bool(request_submitted)).lower()}")
    if request_ownership_acquired is not None:
        parts.append(f"request_ownership_acquired={str(bool(request_ownership_acquired)).lower()}")
    if request_id:
        parts.append(f"request_id={request_id}")
    if transport_outcome:
        parts.append(f"transport_outcome={transport_outcome}")
    if operation_outcome:
        parts.append(f"operation_outcome={operation_outcome}")
    if recommended_next_action:
        parts.append(f"recommended_next_action={recommended_next_action}")

    try:
        sys.stderr.write(" ".join(parts) + "\n")
        if message:
            sys.stderr.write(f"[xuunity-light-unity-mcp] error_message {message}\n")
        if recommended_recovery_command:
            sys.stderr.write(
                "[xuunity-light-unity-mcp] recovery_command "
                f"{recommended_recovery_command}\n"
            )
        sys.stderr.flush()
    except Exception:
        pass


def build_tool_error_payload(exc: ToolInvocationError) -> dict[str, Any]:
    details = dict(exc.details or {})
    error: dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
    }
    if details:
        error["details"] = details

    payload: dict[str, Any] = {"error": error}
    for key in (
        "request_id",
        "request_submitted",
        "request_ownership_acquired",
        "transport_outcome",
        "operation_outcome",
        "recommended_next_action",
        "transport",
        "initial_bridge_generation",
        "initial_bridge_session_id",
        "current_bridge_generation",
        "current_bridge_session_id",
        "retryable",
        "request_processed",
        "bridge_stabilization",
        "request_final_status",
        "journal_event_path",
        "recommended_recovery_command",
        "batch_summary_file",
        "batch_failure_summary",
    ):
        if key in details:
            payload[key] = details[key]
    return payload


def first_non_empty_line(text: str, *, limit: int = 240) -> str:
    for line in str(text or "").splitlines():
        candidate = line.strip()
        if candidate:
            return truncate_text(candidate, limit)
    return ""


def batch_summary_artifact_path(result_path: Path) -> Path:
    suffix = result_path.suffix or ".json"
    stem = result_path.stem if result_path.suffix else result_path.name
    return result_path.with_name(f"{stem}_summary{suffix}")


def write_batch_summary_artifact(summary_path: Path, summary: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def batch_phase_for_action(action: str) -> str:
    if action == "plain_batch_build":
        return "build"
    if action.startswith("batch_"):
        return "validation"
    return "batch"


def derive_batch_unity_outcome(result_payload: dict[str, Any] | None, succeeded: bool) -> str:
    if not isinstance(result_payload, dict):
        return "completed_ok" if succeeded else "unknown"

    for key in ("outcome", "status", "build_result"):
        value = str(result_payload.get(key) or "").strip()
        if value:
            return value

    compile_result = ((result_payload.get("compile") or {}).get("result") or {}) if isinstance(result_payload.get("compile"), dict) else {}
    if isinstance(compile_result, dict):
        value = str(compile_result.get("status") or "").strip()
        if value:
            return value

    matrix_payload = result_payload.get("matrix") or {}
    if isinstance(matrix_payload, dict):
        value = str(matrix_payload.get("status") or "").strip()
        if value:
            return value

    tests_payload = result_payload.get("tests") or {}
    if isinstance(tests_payload, dict):
        value = str(tests_payload.get("status") or "").strip()
        if value:
            return value

    return "completed_ok" if succeeded else "unknown"


def summarize_batch_result_payload(result_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result_payload, dict):
        return {}

    summary: dict[str, Any] = {}
    operation = str(result_payload.get("operation") or "")
    for key in (
        "action",
        "operation",
        "outcome",
        "succeeded",
        "build_result",
        "requested_build_target",
        "total_errors",
        "total_warnings",
        "total_size_bytes",
        "output_path",
        "output_directory",
    ):
        if key in result_payload:
            summary[key] = result_payload[key]

    compile_payload = result_payload.get("compile") or {}
    if operation == "compile-player-scripts" and isinstance(compile_payload, dict) and compile_payload:
        compile_result = compile_payload.get("result") or {}
        if isinstance(compile_result, dict) and compile_result:
            summary["compile"] = {
                "status": compile_result.get("status"),
                "compiled_assembly_count": compile_result.get("compiled_assembly_count"),
                "error_count": compile_result.get("error_count"),
            }
            if "warning_count" in compile_result and compile_result.get("warning_count") is not None:
                summary["compile"]["warning_count"] = compile_result.get("warning_count")

    matrix_payload = result_payload.get("matrix") or {}
    if operation == "compile-matrix" and isinstance(matrix_payload, dict) and matrix_payload:
        summary["matrix"] = {
            "status": matrix_payload.get("status"),
            "total": matrix_payload.get("total"),
            "passed": matrix_payload.get("passed"),
            "failed": matrix_payload.get("failed"),
            "skipped": matrix_payload.get("skipped"),
        }

    tests_payload = result_payload.get("tests") or {}
    if operation == "editmode-tests" and isinstance(tests_payload, dict) and tests_payload:
        summary["tests"] = {
            "status": tests_payload.get("status"),
            "total": tests_payload.get("total"),
            "passed": tests_payload.get("passed"),
            "failed": tests_payload.get("failed"),
            "skipped": tests_payload.get("skipped"),
        }

    top_actionable_error = first_non_empty_line(result_payload.get("top_actionable_error") or "")
    if not top_actionable_error:
        top_actionable_error = first_non_empty_line(result_payload.get("exception_message") or "")
    if top_actionable_error:
        summary["top_actionable_error"] = top_actionable_error

    return summary


def build_batch_execution_summary(
    *,
    action: str,
    result_payload: dict[str, Any] | None,
    batch_exit_code: int,
    succeeded: bool,
    result_path: Path,
    log_path: Path,
    log_excerpt_hint: str,
) -> dict[str, Any]:
    summary = {
        "action": action,
        "phase": batch_phase_for_action(action),
        "transport_outcome": "batch_process_exited_cleanly" if batch_exit_code == 0 else "batch_process_failed",
        "unity_outcome": derive_batch_unity_outcome(result_payload, succeeded),
        "succeeded": succeeded,
        "batch_exit_code": batch_exit_code,
        "result_file": str(result_path),
        "raw_log_path": str(log_path),
        "next_step": "Inspect raw_log_path only if result_file and this summary are insufficient.",
    }
    summary.update(summarize_batch_result_payload(result_payload))
    if log_excerpt_hint and "top_actionable_error" not in summary:
        summary["log_excerpt_hint"] = log_excerpt_hint
    return summary


def build_batch_prepare_failure_summary(
    *,
    action: str,
    result_path: Path,
    log_path: Path,
    exc: ToolInvocationError,
) -> dict[str, Any]:
    return {
        "action": action,
        "phase": "prepare",
        "transport_outcome": "batch_prepare_blocked",
        "unity_outcome": "not_started",
        "succeeded": False,
        "top_actionable_error": first_non_empty_line(exc.message or exc.code, limit=320),
        "result_file": str(result_path),
        "raw_log_path": str(log_path),
        "next_step": "Resolve the prepare blocker, then rerun the batch command.",
    }


def attach_batch_summary_to_error(
    exc: ToolInvocationError,
    *,
    summary_path: Path,
    summary: dict[str, Any],
) -> ToolInvocationError:
    details = dict(exc.details or {})
    details["batch_summary_file"] = str(summary_path)
    details["batch_failure_summary"] = summary
    return ToolInvocationError(exc.code, exc.message, details)


def request_editor_quit(project_root: Path, timeout_ms: int) -> dict[str, Any]:
    return invoke_bridge(project_root, "unity.editor.quit", {}, timeout_ms)

def wait_for_scenario_result(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    timeout_ms: int,
    poll_interval_ms: int,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    effective_poll_interval = max(0.1, poll_interval_ms / 1000.0)
    last_payload: dict[str, Any] | None = None
    transient_poll_error_codes = {
        "transport_not_ready",
        "transport_response_missing",
        "request_lifecycle_reset",
        "response_missing_after_lifecycle_reset",
    }

    while time.time() < deadline:
        live_state = try_read_live_editor_state(project_root)
        if isinstance(live_state, dict) and bool(live_state.get("playmode_transition_pending")):
            target_state = str(live_state.get("playmode_transition_target_state") or "")
            current_state = str(live_state.get("playmode_state") or "")
            if target_state in {"playing", "paused"} and current_state != target_state:
                try:
                    activate_unity_editor(project_root)
                except ToolInvocationError:
                    pass

        remaining_ms = max(1000, min(5000, int((deadline - time.time()) * 1000)))
        bridge_args: dict[str, Any] = {}
        if run_id:
            bridge_args["runId"] = run_id
        if scenario_name:
            bridge_args["scenarioName"] = scenario_name

        try:
            response = invoke_bridge(str(project_root), "unity.scenario.result", bridge_args, remaining_ms)
        except ToolInvocationError as exc:
            if exc.code in transient_poll_error_codes and time.time() + effective_poll_interval < deadline:
                time.sleep(effective_poll_interval)
                continue
            raise

        tool_result = bridge_response_to_tool_result(response)
        if tool_result.get("isError"):
            structured = tool_result.get("structuredContent") or {}
            error = structured.get("error") or {}
            raise ToolInvocationError(
                str(error.get("code") or "scenario_result_failed"),
                str(error.get("message") or "Scenario result polling failed."),
            )

        payload = tool_result.get("structuredContent") or {}
        if isinstance(payload, dict):
            payload = normalize_scenario_payload(payload, SCENARIO_TERMINAL_STATUSES)
        last_payload = payload

        if is_terminal_scenario_status(payload.get("status")):
            payload["waited_for_terminal_state"] = True
            payload["wait_duration_seconds"] = round(time.time() - started_at, 3)
            return payload

        time.sleep(effective_poll_interval)

    scenario_label = scenario_name or run_id or "unknown"
    suffix = ""
    if last_payload:
        suffix = f" Last observed status: {last_payload.get('status') or 'unknown'}."
    raise ToolInvocationError(
        "scenario_wait_timeout",
        f"Timed out waiting for scenario '{scenario_label}' to reach a terminal state.{suffix}",
    )

def is_terminal_scenario_status(status: Any) -> bool:
    return isinstance(status, str) and status in SCENARIO_TERMINAL_STATUSES


def normalize_refresh_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    requested_outcome = str(normalized.get("outcome") or "")
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    settled_at_utc = str(idle_wait_after.get("heartbeat_utc") or "")
    normalized["requested_outcome"] = requested_outcome
    normalized["outcome"] = (
        "refresh_and_resolve_completed"
        if bool(normalized.get("package_resolve_requested"))
        else "refresh_completed"
    )
    normalized["settled_at_utc"] = settled_at_utc
    if (
        str(idle_wait_after.get("refresh_settle_phase") or "") == "settled"
        and str(idle_wait_after.get("refresh_settle_request_id") or "") == str(normalized.get("settle_request_id") or "")
    ):
        normalized["completion_basis"] = "unity_refresh_settle_watcher"
        normalized["settled_at_utc"] = str(idle_wait_after.get("refresh_settle_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
        normalized["settle_request_id"] = str(idle_wait_after.get("refresh_settle_request_id") or normalized.get("settle_request_id") or "")
    else:
        normalized["completion_basis"] = "host_waited_for_editor_idle"
    normalized["editor_is_compiling_after_settle"] = bool(idle_wait_after.get("is_compiling"))
    normalized["editor_is_updating_after_settle"] = bool(idle_wait_after.get("is_updating"))
    normalized["playmode_state_after_settle"] = str(idle_wait_after.get("playmode_state") or "")
    return normalized


def normalize_compile_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    settled_at_utc = str(idle_wait_after.get("heartbeat_utc") or "")
    request_id = str(normalized.get("settle_request_id") or "")
    if (
        str(idle_wait_after.get("compile_settle_phase") or "") == "settled"
        and str(idle_wait_after.get("compile_settle_request_id") or "") == request_id
    ):
        normalized["completion_basis"] = "unity_compile_settle_watcher"
        normalized["settled_at_utc"] = str(idle_wait_after.get("compile_settle_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
        normalized["settle_request_id"] = str(idle_wait_after.get("compile_settle_request_id") or request_id)
    else:
        normalized["completion_basis"] = "host_waited_for_editor_idle"
        normalized["settled_at_utc"] = settled_at_utc

    normalized["editor_is_compiling_after_settle"] = bool(idle_wait_after.get("is_compiling"))
    normalized["editor_is_updating_after_settle"] = bool(idle_wait_after.get("is_updating"))
    normalized["playmode_state_after_settle"] = str(idle_wait_after.get("playmode_state") or "")
    return normalized


def normalize_playmode_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    settled_state = lifecycle.get("playmode_wait_after")
    if not isinstance(settled_state, dict):
        return normalized

    settled_at_utc = str(settled_state.get("heartbeat_utc") or "")
    request_id = str(normalized.get("settle_request_id") or "")
    if (
        str(settled_state.get("playmode_transition_phase") or "") == "settled"
        and str(settled_state.get("playmode_transition_request_id") or "") == request_id
    ):
        normalized["completion_basis"] = "unity_playmode_transition_watcher"
        normalized["settled_at_utc"] = str(settled_state.get("playmode_transition_completed_utc") or settled_at_utc)
        normalized["settle_phase"] = "settled"
    else:
        normalized["completion_basis"] = "host_waited_for_playmode_state"
        normalized["settled_at_utc"] = settled_at_utc

    normalized["settle_target_state"] = str(
        settled_state.get("playmode_transition_target_state")
        or normalized.get("settle_target_state")
        or settled_state.get("playmode_state")
        or ""
    )
    normalized["settle_request_id"] = str(
        settled_state.get("playmode_transition_request_id")
        or request_id
    )
    normalized["is_playing"] = bool(settled_state.get("is_playing"))
    normalized["is_paused"] = bool(settled_state.get("is_paused"))
    normalized["is_playing_or_will_change_playmode"] = bool(settled_state.get("is_playing_or_will_change_playmode"))
    normalized["playmode_state"] = str(settled_state.get("playmode_state") or normalized.get("playmode_state") or "")
    return normalized


def normalize_build_target_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    normalized["completion_basis"] = "host_waited_for_editor_idle"
    normalized["settled_at_utc"] = str(idle_wait_after.get("heartbeat_utc") or normalized.get("settled_at_utc") or "")
    normalized["editor_is_compiling_after_settle"] = bool(idle_wait_after.get("is_compiling"))
    normalized["editor_is_updating_after_settle"] = bool(idle_wait_after.get("is_updating"))
    normalized["playmode_state_after_settle"] = str(idle_wait_after.get("playmode_state") or "")
    return normalized


def normalize_tests_payload_from_lifecycle(payload: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    idle_wait_after = lifecycle.get("idle_wait_after")
    if not isinstance(idle_wait_after, dict):
        return normalized

    normalized["playmode_state_after_settle"] = str(
        idle_wait_after.get("playmode_state")
        or normalized.get("playmode_state_after_settle")
        or ""
    )
    return normalized


def normalize_response_payload_from_lifecycle(response: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    if response.get("status") != "ok":
        return response

    settled_state = lifecycle.get("playmode_wait_after")
    payload_json = response.get("payload_json")
    if not isinstance(payload_json, str) or not payload_json:
        return response

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return response

    operation = str(lifecycle.get("operation") or "")
    payload_type = str(response.get("payload_type") or "")

    if operation == "unity.playmode.set" and isinstance(settled_state, dict):
        payload = normalize_playmode_payload_from_lifecycle(payload, lifecycle)
    elif operation == "unity.project.refresh":
        payload = normalize_refresh_payload_from_lifecycle(payload, lifecycle)
    elif operation in {"unity.compile.player_scripts", "unity.compile.matrix"}:
        payload = normalize_compile_payload_from_lifecycle(payload, lifecycle)
    elif operation == "unity.build_target.switch":
        payload = normalize_build_target_payload_from_lifecycle(payload, lifecycle)
    elif operation == "unity.tests.run_playmode":
        payload = normalize_tests_payload_from_lifecycle(payload, lifecycle)

    if payload_type in {"unity.scenario.run", "unity.scenario.result"}:
        payload = normalize_scenario_payload(payload, SCENARIO_TERMINAL_STATUSES)

    normalized = dict(response)
    normalized["payload_json"] = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return normalized


def resolve_operation_timeout_ms(
    project_root: Path,
    operation: str,
    explicit_timeout_ms: Any,
    fallback_timeout_ms: int,
) -> int:
    if isinstance(explicit_timeout_ms, int):
        return explicit_timeout_ms
    if explicit_timeout_ms is not None:
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")
    return resolve_operation_default_timeout_ms(project_root, operation, fallback_timeout_ms)


def resolve_operation_lifecycle_policy(project_root: Path, operation: str) -> dict[str, Any]:
    policy = {
        "activate_unity": False,
        "wait_for_idle_before": False,
        "wait_for_idle_after": False,
        "idle_stable_cycles_after": DEFAULT_IDLE_STABLE_CYCLES,
        "retry_on_lifecycle_reset": False,
        "retry_on_transport_response_missing": False,
        "retry_on_transport_connect_failed": False,
        "post_reset_recovery_cap_ms": 0,
    }
    policy.update(OPERATION_LIFECYCLE_POLICIES.get(operation, {}))
    policy.update(resolve_operation_lifecycle_policy_overrides(project_root, operation))
    return policy


def invoke_bridge(project_root_value: str, operation: str, args: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
    project_root = ensure_project_root(project_root_value)
    policy = resolve_operation_lifecycle_policy(project_root, operation)
    max_attempts = 2 if (
        bool(policy.get("retry_on_lifecycle_reset"))
        or bool(policy.get("retry_on_transport_response_missing"))
        or bool(policy.get("retry_on_transport_connect_failed"))
    ) else 1

    for attempt_index in range(max_attempts):
        pre_request_state = try_read_live_editor_state(project_root) or try_read_bridge_state(project_root)
        lifecycle: dict[str, Any] = {
            "operation": operation,
            "attempt_index": attempt_index,
            "max_attempts": max_attempts,
            "activation_requested": False,
            "idle_wait_before": None,
            "idle_wait_after": None,
            "transport": None,
            "bridge_identity_before_request": {
                "bridge_generation": bridge_identity_from_state(pre_request_state)[0],
                "bridge_session_id": bridge_identity_from_state(pre_request_state)[1],
            },
        }

        try:
            if policy["activate_unity"]:
                lifecycle["activation_requested"] = True
                lifecycle["activation"] = activate_unity_editor(project_root)

            if policy["wait_for_idle_before"]:
                lifecycle["idle_wait_before"] = wait_for_editor_idle(
                    project_root,
                    timeout_ms,
                    DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                    f"before {operation}",
                    stable_cycles=1,
                )

            response, request_id, request_started_at, transport_metadata = invoke_bridge_transport(
                project_root,
                operation,
                args,
                timeout_ms,
                post_reset_recovery_cap_ms=int(policy.get("post_reset_recovery_cap_ms") or 0),
            )
            lifecycle["transport"] = transport_metadata

            if operation == "unity.playmode.set":
                expected_playmode_state = expected_playmode_state_for_action(str(args.get("action") or ""))
                if expected_playmode_state:
                    lifecycle["playmode_wait_after"] = wait_for_playmode_state(
                        project_root,
                        timeout_ms,
                        DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        expected_playmode_state,
                        f"after {operation}",
                        after_request_id=request_id,
                        not_before_unix=request_started_at,
                        stable_cycles=int(policy["idle_stable_cycles_after"]),
                    )
                elif policy["wait_for_idle_after"]:
                    lifecycle["idle_wait_after"] = wait_for_editor_idle(
                        project_root,
                        timeout_ms,
                        DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        f"after {operation}",
                        after_request_id=request_id,
                        not_before_unix=request_started_at,
                        stable_cycles=int(policy["idle_stable_cycles_after"]),
                    )
            elif policy["wait_for_idle_after"]:
                lifecycle["idle_wait_after"] = wait_for_editor_idle(
                    project_root,
                    timeout_ms,
                    DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                    f"after {operation}",
                    after_request_id=request_id,
                    not_before_unix=request_started_at,
                    stable_cycles=int(policy["idle_stable_cycles_after"]),
                )

            settled_state = (
                lifecycle.get("playmode_wait_after")
                if isinstance(lifecycle.get("playmode_wait_after"), dict)
                else lifecycle.get("idle_wait_after")
            )
            if isinstance(settled_state, dict):
                transition = maybe_record_settle_lifecycle_transition(
                    project_root,
                    operation,
                    request_id,
                    pre_request_state,
                    settled_state,
                )
                if transition:
                    lifecycle["bridge_identity_transition"] = transition

            if response.get("status") == "ok":
                response = normalize_response_payload_from_lifecycle(dict(response), lifecycle)
                response["_xuunity_lifecycle"] = lifecycle

            return response
        except ToolInvocationError as exc:
            if exc.code == "request_lifecycle_reset" and attempt_index + 1 < max_attempts:
                lifecycle["lifecycle_reset_retry"] = exc.details
                continue
            if (
                exc.code == "transport_response_missing"
                and bool(policy.get("retry_on_transport_response_missing"))
                and attempt_index + 1 < max_attempts
                and not bool((exc.details or {}).get("request_processed"))
            ):
                lifecycle["transport_response_missing_retry"] = exc.details
                continue
            if (
                exc.code == "transport_connect_failed"
                and bool(policy.get("retry_on_transport_connect_failed"))
                and attempt_index + 1 < max_attempts
            ):
                lifecycle["transport_connect_failed_retry"] = exc.details
                retry_state = try_read_bridge_state(project_root) or pre_request_state or {}
                wait_for_ready(
                    project_root=project_root,
                    timeout_ms=min(timeout_ms, 10000),
                    heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                    startup_policy=str(
                        retry_state.get("startup_policy")
                        or "fail_fast_on_interactive_compile_block"
                    ),
                    editor_log_path=default_editor_log_path(project_root),
                )
                continue
            raise

    raise ToolInvocationError("unreachable", f"Unexpected lifecycle retry state for {operation}.")

def bridge_response_to_tool_result(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("status") == "ok":
        payload = {}
        payload_json = response.get("payload_json") or "{}"
        payload_type = str(response.get("payload_type") or "")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            payload = {"raw_payload_json": payload_json}

        lifecycle = response.get("_xuunity_lifecycle")
        if isinstance(lifecycle, dict) and lifecycle:
            payload["_xuunity_lifecycle"] = lifecycle
        elif payload_type in {"unity.scenario.run", "unity.scenario.result"} and isinstance(payload, dict):
            payload = normalize_scenario_payload(payload, SCENARIO_TERMINAL_STATUSES)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": False
        }

    error = response.get("error") or {}
    message = error.get("message") or "Unknown bridge error."
    code = error.get("code") or "unknown_bridge_error"
    structured = {
        "error": {
            "code": code,
            "message": message
        }
    }
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ],
        "structuredContent": structured,
        "isError": True
    }


def scenario_failure_tool_result(result_payload: dict[str, Any]) -> dict[str, Any]:
    scenario_name = str(result_payload.get("scenario_name") or "unknown_scenario")
    status = str(result_payload.get("status") or result_payload.get("terminal_status") or "failed")
    structured = {
        "error": {
            "code": "scenario_failed",
            "message": f"Scenario '{scenario_name}' finished with status '{status}'.",
        },
        "scenario": result_payload,
    }
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ],
        "structuredContent": structured,
        "isError": True,
    }


def call_unity_compile_build_config_matrix_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    project_root = ensure_project_root(project_root_value)
    timeout_ms = resolve_operation_timeout_ms(
        project_root,
        "unity.compile.matrix",
        arguments.get("timeoutMs"),
        300000,
    )

    profiles = arguments.get("profiles")
    if profiles is not None and not isinstance(profiles, list):
        raise JsonRpcError(-32602, "profiles must be an array of strings when provided.")

    targets = arguments.get("targets")
    if targets is not None and not isinstance(targets, list):
        raise JsonRpcError(-32602, "targets must be an array of strings when provided.")

    stop_on_first_failure = arguments.get("stopOnFirstFailure", False)
    if not isinstance(stop_on_first_failure, bool):
        raise JsonRpcError(-32602, "stopOnFirstFailure must be a boolean when provided.")

    build_config_asset = arguments.get("buildConfigAsset")
    if build_config_asset is not None and not isinstance(build_config_asset, str):
        raise JsonRpcError(-32602, "buildConfigAsset must be a string when provided.")

    try:
        compile_plan = build_compile_matrix_args_from_build_config(
            project_root=project_root,
            build_config_asset=build_config_asset,
            requested_profiles=profiles,
            requested_targets=targets,
            stop_on_first_failure=stop_on_first_failure,
            tool_error_type=ToolInvocationError,
        )
        response = invoke_bridge(
            str(project_root),
            "unity.compile.matrix",
            compile_plan["matrixArgs"],
            timeout_ms,
        )
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": True
        }

    tool_result = bridge_response_to_tool_result(response)
    structured = tool_result.get("structuredContent") or {}
    if not tool_result.get("isError"):
        structured = {
            "build_config_asset": compile_plan["assetPath"],
            "profiles": compile_plan["profiles"],
            "matrix": structured,
        }
        tool_result["structuredContent"] = structured
        tool_result["content"] = [
            {
                "type": "text",
                "text": json.dumps(structured, ensure_ascii=True)
            }
        ]
    return tool_result


def call_unity_scenario_run_and_wait_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    project_root = ensure_project_root(project_root_value)
    scenario = arguments.get("scenario")
    if not isinstance(scenario, dict):
        raise JsonRpcError(-32602, "scenario must be an object.")

    timeout_ms = resolve_operation_timeout_ms(
        project_root,
        "unity.scenario.run",
        arguments.get("timeoutMs"),
        600000,
    )

    poll_interval_ms = arguments.get("pollIntervalMs", 1000)
    if not isinstance(poll_interval_ms, int):
        raise JsonRpcError(-32602, "pollIntervalMs must be an integer.")

    try:
        run_response = invoke_bridge(
            str(project_root),
            "unity.scenario.run",
            {"scenario": scenario},
            max(5000, min(timeout_ms, 15000)),
        )
        run_tool_result = bridge_response_to_tool_result(run_response)
        if run_tool_result.get("isError"):
            return run_tool_result

        run_payload = run_tool_result.get("structuredContent") or {}
        run_id = str(run_payload.get("run_id") or "")
        scenario_name = str(run_payload.get("scenario_name") or scenario.get("name") or "")
        result_payload = wait_for_scenario_result(
            project_root=project_root,
            run_id=run_id,
            scenario_name=scenario_name,
            timeout_ms=timeout_ms,
            poll_interval_ms=poll_interval_ms,
        )
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": True
        }

    result_payload["run_start"] = run_payload
    if not bool(result_payload.get("succeeded")):
        return scenario_failure_tool_result(result_payload)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result_payload, ensure_ascii=True)
            }
        ],
        "structuredContent": result_payload,
        "isError": False
    }


def call_unity_status_summary_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    timeout_ms = arguments.get("timeoutMs", 5000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    project_root = ensure_project_root(project_root_value)
    try:
        response = invoke_bridge(str(project_root), "unity.status", {}, timeout_ms)
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": True
        }

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        return tool_result

    payload = tool_result.get("structuredContent") or {}
    if not isinstance(payload, dict):
        payload = {}
    summary = build_status_summary(
        project_root,
        payload,
        read_best_effort_bridge_state=read_best_effort_bridge_state,
        try_read_bridge_state=try_read_bridge_state,
        pid_is_alive=pid_is_alive,
        heartbeat_age_seconds=heartbeat_age_seconds,
        derive_busy_reason=derive_busy_reason,
        summarize_state_for_error=summarize_state_for_error,
    )
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(summary, ensure_ascii=True)
            }
        ],
        "structuredContent": summary,
        "isError": False
    }


def call_unity_request_final_status_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    request_id = arguments.get("requestId")
    if not isinstance(request_id, str) or not request_id.strip():
        raise JsonRpcError(-32602, "requestId is required.")

    timeout_ms = arguments.get("timeoutMs", 2000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    operation = arguments.get("operation")
    if operation is not None and not isinstance(operation, str):
        raise JsonRpcError(-32602, "operation must be a string when provided.")

    project_root = ensure_project_root(project_root_value)
    current_state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root)
    summary = build_request_final_status(
        project_root,
        request_id.strip(),
        operation.strip() if isinstance(operation, str) else "",
        current_state=current_state,
        poll_timeout_ms=timeout_ms,
    )
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(summary, ensure_ascii=True)
            }
        ],
        "structuredContent": summary,
        "isError": False
    }


def call_unity_scenario_result_summary_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    timeout_ms = arguments.get("timeoutMs", 5000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    bridge_args: dict[str, Any] = {}
    run_id = arguments.get("runId")
    if isinstance(run_id, str) and run_id.strip():
        bridge_args["runId"] = run_id
    scenario_name = arguments.get("scenarioName")
    if isinstance(scenario_name, str) and scenario_name.strip():
        bridge_args["scenarioName"] = scenario_name

    try:
        response = invoke_bridge(project_root_value, "unity.scenario.result", bridge_args, timeout_ms)
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": True
        }

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        return tool_result

    payload = tool_result.get("structuredContent") or {}
    if not isinstance(payload, dict):
        payload = {}
    summary = build_scenario_result_summary(payload, SCENARIO_TERMINAL_STATUSES)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(summary, ensure_ascii=True)
            }
        ],
        "structuredContent": summary,
        "isError": False
    }


def call_unity_maintenance_prune_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    project_root = ensure_project_root(project_root_value)
    result = prune_project_artifacts(
        project_root,
        arguments,
        bridge_root=bridge_root,
        request_journal_dir=request_journal_dir,
        scenario_results_dir=scenario_results_dir,
        active_scenario_run_path=active_scenario_run_path,
        captures_dir=captures_dir,
        logs_dir=logs_dir,
        default_editor_log_path=default_editor_log_path,
        read_json=read_json,
    )
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=True)
            }
        ],
        "structuredContent": result,
        "isError": False
    }


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOLS:
        raise JsonRpcError(-32601, f"Unknown tool: {name}")

    args = arguments or {}
    if name == "unity_status_summary":
        return call_unity_status_summary_tool(args)
    if name == "unity_request_final_status":
        return call_unity_request_final_status_tool(args)
    if name == "unity_scenario_result_summary":
        return call_unity_scenario_result_summary_tool(args)
    if name == "unity_maintenance_prune":
        return call_unity_maintenance_prune_tool(args)
    if name == "unity_compile_build_config_matrix":
        return call_unity_compile_build_config_matrix_tool(args)
    if name == "unity_scenario_run_and_wait":
        return call_unity_scenario_run_and_wait_tool(args)

    tool = TOOLS[name]
    project_root = args.get("projectRoot")
    if not isinstance(project_root, str) or not project_root.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    resolved_project_root = ensure_project_root(project_root)
    timeout_ms = resolve_operation_timeout_ms(
        resolved_project_root,
        tool["bridgeOperation"],
        args.get("timeoutMs"),
        tool.get("inputSchema", {}).get("properties", {}).get("timeoutMs", {}).get("default", 5000),
    )

    bridge_args = dict(args)
    bridge_args.pop("projectRoot", None)
    bridge_args.pop("timeoutMs", None)

    try:
        response = invoke_bridge(str(resolved_project_root), tool["bridgeOperation"], bridge_args, timeout_ms)
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=True)
                }
            ],
            "structuredContent": payload,
            "isError": True
        }

    return bridge_response_to_tool_result(response)


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def success_response(request_id: Any, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def error_response(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload


def emit_message(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def log_stderr(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def build_initialize_result(requested_version: str | None) -> dict[str, Any]:
    protocol_version = requested_version or PROTOCOL_VERSION
    if protocol_version != PROTOCOL_VERSION:
        protocol_version = PROTOCOL_VERSION

    return {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        },
        "serverInfo": SERVER_INFO,
        "instructions": (
            "Use these tools for Unity editor validation over a lightweight file-IPC bridge. "
            "Every tool requires an explicit projectRoot."
        )
    }


def list_tools_result() -> dict[str, Any]:
    tools = []
    for name, spec in TOOLS.items():
        tools.append(
            {
                "name": name,
                "title": name.replace("_", " ").title(),
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            }
        )
    return {"tools": tools}


def handle_json_rpc_message(message: dict[str, Any], session: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if method == "initialize":
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "initialize params must be an object.")
        requested_version = params.get("protocolVersion")
        session["initialized"] = False
        session["protocolVersion"] = PROTOCOL_VERSION
        return success_response(request_id, build_initialize_result(requested_version))

    if method == "notifications/initialized":
        session["initialized"] = True
        return None

    if method == "ping":
        return success_response(request_id, {})

    if method == "tools/list":
        return success_response(request_id, list_tools_result())

    if method == "tools/call":
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "tools/call params must be an object.")
        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or not name:
            raise JsonRpcError(-32602, "tools/call requires a non-empty tool name.")
        if arguments is not None and not isinstance(arguments, dict):
            raise JsonRpcError(-32602, "tools/call arguments must be an object when provided.")
        return success_response(request_id, call_tool(name, arguments))

    raise JsonRpcError(-32601, f"Method not found: {method}")


def serve_stdio() -> int:
    session = {"initialized": False, "protocolVersion": PROTOCOL_VERSION}
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise JsonRpcError(-32600, "Invalid JSON-RPC message.")

            response = handle_json_rpc_message(message, session)
            if response is not None:
                emit_message(response)
        except json.JSONDecodeError:
            emit_message(error_response(None, -32700, "Parse error"))
        except JsonRpcError as exc:
            msg_id = message.get("id") if isinstance(message, dict) else None
            emit_message(error_response(msg_id, exc.code, exc.message, exc.data))
        except Exception as exc:
            log_stderr(f"[xuunity-light-unity-mcp] internal error: {exc}")
            msg_id = None
            if isinstance(message, dict):
                msg_id = message.get("id")
            emit_message(error_response(msg_id, -32603, "Internal error"))

    return 0


def cmd_bridge_state(args):
    project_root = ensure_project_root(args.project_root)
    if not bridge_enabled(project_root):
        raise SystemExit(
            "Bridge is disabled for this project. Enable it with "
            "init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project and reopen Unity."
        )
    state_path = bridge_state_path(project_root)
    if not state_path.is_file():
        raise SystemExit(f"Bridge state file not found: {state_path}")
    print_json(annotate_bridge_state_with_liveness(read_json(state_path)))


def cmd_request_status(args):
    response = invoke_bridge(args.project_root, "unity.status", {}, args.timeout_ms)
    print_json(response)


def cmd_request_status_summary(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(str(project_root), "unity.status", {}, args.timeout_ms)
    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        print_json(tool_result.get("structuredContent") or {})
        raise SystemExit(1)
    payload = tool_result.get("structuredContent") or {}
    print_json(build_status_summary(
        project_root,
        payload if isinstance(payload, dict) else {},
        read_best_effort_bridge_state=read_best_effort_bridge_state,
        try_read_bridge_state=try_read_bridge_state,
        pid_is_alive=pid_is_alive,
        heartbeat_age_seconds=heartbeat_age_seconds,
        derive_busy_reason=derive_busy_reason,
        summarize_state_for_error=summarize_state_for_error,
    ))


def cmd_request_latest_status(args):
    project_root = ensure_project_root(args.project_root)
    operations = [str(operation).strip() for operation in list(args.operation or []) if str(operation).strip()]
    current_state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root)
    latest_event = find_latest_request_event(project_root, operations)

    if latest_event is None:
        stabilization = build_bridge_stabilization_summary(current_state)
        print_json({
            "lookup_mode": "latest_request_by_operation",
            "lookup_found": False,
            "matched_operations": operations,
            "request_id": "",
            "operation": operations[-1] if operations else "",
            "request_started": False,
            "request_completed": False,
            "completion_status": "",
            "operation_outcome": "unknown",
            "reclassified": False,
            "reclassified_status": "",
            "reclassified_reason": "",
            "retryable": False,
            "recommended_next_action": (
                "retry_request" if stabilization["safe_to_retry"] else "wait_for_bridge_stabilization"
            ),
            "request_started_at_utc": "",
            "request_completed_at_utc": "",
            "last_event_type": "",
            "last_event_at_utc": "",
            "last_bridge_generation_seen": int((current_state or {}).get("bridge_generation") or 0),
            "last_bridge_session_id_seen": str((current_state or {}).get("bridge_session_id") or ""),
            "journal_event_count": 0,
            "journal_event_paths": [],
            "bridge_stabilization": stabilization,
        })
        return

    request_id = str(latest_event.get("request_id") or "").strip()
    operation = str(latest_event.get("operation") or "").strip()
    summary = build_request_final_status(
        project_root,
        request_id,
        operation,
        current_state=current_state,
        poll_timeout_ms=args.timeout_ms,
    )
    summary["lookup_mode"] = "latest_request_by_operation"
    summary["lookup_found"] = True
    summary["matched_operations"] = operations
    summary["lookup_event_type"] = str(latest_event.get("event_type") or "")
    summary["lookup_event_at_utc"] = str(latest_event.get("event_at_utc") or "")
    summary["lookup_event_path"] = str(latest_event.get("_path") or "")
    print_json(summary)


def cmd_request_final_status(args):
    project_root = ensure_project_root(args.project_root)
    summary = build_request_final_status(
        project_root,
        args.request_id,
        args.operation or "",
        current_state=read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root),
        poll_timeout_ms=args.timeout_ms,
    )
    print_json(summary)


def cmd_request_playmode_state(args):
    response = invoke_bridge(args.project_root, "unity.playmode.state", {}, args.timeout_ms)
    print_json(response)


def cmd_request_playmode_set(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.playmode.set",
        {"action": args.action},
        resolve_operation_default_timeout_ms(project_root, "unity.playmode.set", 180000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_capabilities(args):
    response = invoke_bridge(args.project_root, "unity.capabilities.get", {}, args.timeout_ms)
    print_json(response)


def cmd_request_health_probe(args):
    response = invoke_bridge(args.project_root, "unity.health.probe", {}, args.timeout_ms)
    print_json(response)


def cmd_request_build_target_get(args):
    response = invoke_bridge(args.project_root, "unity.build_target.get", {}, args.timeout_ms)
    print_json(response)


def cmd_request_build_target_switch(args):
    response = invoke_bridge(
        args.project_root,
        "unity.build_target.switch",
        {"target": args.target},
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_editor_quit(args):
    response = request_editor_quit(args.project_root, args.timeout_ms)
    print_json(response)


def cmd_request_project_refresh(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.project.refresh",
        {
            "forceAssetRefresh": args.force_asset_refresh,
            "resolvePackages": args.resolve_packages,
            "rerunHealthProbe": args.rerun_health_probe,
        },
        resolve_operation_default_timeout_ms(project_root, "unity.project.refresh", 180000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_editmode_tests(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.tests.run_editmode",
        {
            "testNames": args.test_names or None,
            "groupNames": args.group_names or None,
            "categoryNames": args.category_names or None,
            "assemblyNames": args.assembly_names or None,
        },
        resolve_operation_default_timeout_ms(project_root, "unity.tests.run_editmode", 300000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_playmode_tests(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.tests.run_playmode",
        {
            "testNames": args.test_names or None,
            "groupNames": args.group_names or None,
            "categoryNames": args.category_names or None,
            "assemblyNames": args.assembly_names or None,
        },
        resolve_operation_default_timeout_ms(project_root, "unity.tests.run_playmode", 300000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_compile(args):
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.compile.player_scripts",
        {
            "name": args.name,
            "target": args.target,
            "optionFlags": args.option_flags,
            "extraDefines": args.extra_defines,
        },
        resolve_operation_default_timeout_ms(project_root, "unity.compile.player_scripts", 180000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_compile_matrix(args):
    project_root = ensure_project_root(args.project_root)
    config_file = Path(args.config_file).expanduser().resolve()
    if not config_file.is_file():
        raise ToolInvocationError("compile_matrix_config_not_found", f"Compile matrix config file not found: {config_file}")

    try:
        matrix_args = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError("compile_matrix_config_invalid", str(exc)) from exc

    response = invoke_bridge(
        str(project_root),
        "unity.compile.matrix",
        matrix_args,
        resolve_operation_default_timeout_ms(project_root, "unity.compile.matrix", 300000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_build_config_compile_matrix(args):
    project_root = ensure_project_root(args.project_root)
    compile_plan = build_compile_matrix_args_from_build_config(
        project_root=project_root,
        build_config_asset=args.build_config_asset,
        requested_profiles=args.profile,
        requested_targets=args.target,
        stop_on_first_failure=args.stop_on_first_failure,
        tool_error_type=ToolInvocationError,
    )
    response = invoke_bridge(
        str(project_root),
        "unity.compile.matrix",
        compile_plan["matrixArgs"],
        resolve_operation_default_timeout_ms(project_root, "unity.compile.matrix", 300000) if args.timeout_ms is None else args.timeout_ms,
    )

    payload = {
        "build_config_asset": compile_plan["assetPath"],
        "profiles": compile_plan["profiles"],
        "bridge_response": response,
    }
    print_json(payload)


def load_json_file(path_value: str, error_code: str) -> Any:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ToolInvocationError(error_code, f"JSON file not found: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError(error_code, str(exc)) from exc


def ensure_batch_project_closed(project_root: Path, action_label: str):
    live_editor_pids = list_live_project_editor_pids(project_root)
    if live_editor_pids:
        raise ToolInvocationError(
            "editor_running_batch_conflict",
            (
                f"Refusing to start {action_label} while the Unity project is open in the editor. "
                f"Live editor pid(s): {', '.join(str(pid) for pid in live_editor_pids)}. "
                "Close the same project editor instance first or use the interactive MCP lane."
            ),
            {"live_editor_pids": live_editor_pids},
        )


def run_batch_operation(
    *,
    project_root: Path,
    command: list[str],
    payload: dict[str, Any],
    log_path: Path,
    result_path: Path,
    dry_run: bool,
):
    if dry_run:
        print_json(payload)
        return

    summary_path = batch_summary_artifact_path(result_path)
    payload["summary_file"] = str(summary_path)

    try:
        ensure_batch_project_closed(project_root, str(payload.get("action") or "batch operation"))
    except ToolInvocationError as exc:
        summary = build_batch_prepare_failure_summary(
            action=str(payload.get("action") or "batch operation"),
            result_path=result_path,
            log_path=log_path,
            exc=exc,
        )
        write_batch_summary_artifact(summary_path, summary)
        raise attach_batch_summary_to_error(exc, summary_path=summary_path, summary=summary)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload["stale_lock"] = clear_stale_project_lock(project_root)

    command_started_at = time.time()
    completed = subprocess.run(command, check=False)
    payload["batch_exit_code"] = completed.returncode

    result_payload = try_read_json_dict(result_path, read_json)
    payload["result_payload_present"] = result_payload is not None
    payload["succeeded"] = (
        bool(result_payload.get("succeeded", False)) and completed.returncode == 0
        if result_payload is not None
        else completed.returncode == 0
    )

    log_excerpt_hint = ""
    if completed.returncode != 0 or not bool(payload.get("succeeded")):
        log_excerpt = read_recent_editor_log(log_path, command_started_at)
        if log_excerpt:
            log_excerpt_hint = truncate_text(log_excerpt[-600:], 600)

    result_summary = build_batch_execution_summary(
        action=str(payload.get("action") or "batch operation"),
        result_payload=result_payload,
        batch_exit_code=completed.returncode,
        succeeded=bool(payload.get("succeeded")),
        result_path=result_path,
        log_path=log_path,
        log_excerpt_hint=log_excerpt_hint,
    )
    write_batch_summary_artifact(summary_path, result_summary)
    payload["result_summary"] = result_summary
    if "top_actionable_error" in result_summary:
        payload["top_actionable_error"] = result_summary["top_actionable_error"]

    print_json(payload)
    if completed.returncode != 0 or not bool(payload.get("succeeded")):
        raise SystemExit(1)


TEST_FRAMEWORK_PACKAGE_NAME = "com.unity.test-framework"
TEST_FRAMEWORK_PERFORMANCE_PACKAGE_NAME = "com.unity.test-framework.performance"
TEST_FRAMEWORK_REGRESSION_LOCK_PACKAGES = [
    TEST_FRAMEWORK_PACKAGE_NAME,
    TEST_FRAMEWORK_PERFORMANCE_PACKAGE_NAME,
    LIGHTWEIGHT_PACKAGE_NAME,
]
TEST_FRAMEWORK_REGRESSION_FOCUS_ASSEMBLIES = ["_Hub.AppLoadingSteps.Tests"]
TEST_FRAMEWORK_REGRESSION_FOCUS_TESTS = ["CheckMinSupportedVersionUpdateLinkRoutingTests"]
TEST_FRAMEWORK_REGRESSION_COMPILE_TARGET = "Android"


def test_framework_regression_result_path(project_root: Path) -> Path:
    return default_batch_operation_result_path(project_root, "test_framework_version_regression")


def test_framework_regression_artifacts_dir(result_path: Path) -> Path:
    suffix = result_path.suffix or ".json"
    stem = result_path.stem if result_path.suffix else result_path.name
    return result_path.with_name(f"{stem}_artifacts")


def normalize_requested_versions(raw_versions: list[str], versions_file: str | None) -> list[str]:
    versions: list[str] = []

    for raw_version in raw_versions:
        version = str(raw_version or "").strip()
        if version:
            versions.append(version)

    if versions_file:
        path = Path(versions_file).expanduser().resolve()
        if not path.is_file():
            raise ToolInvocationError(
                "versions_file_not_found",
                f"Version file not found: {path}",
            )

        text = path.read_text(encoding="utf-8")
        parsed_versions: list[str] = []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, list):
            parsed_versions = [str(item).strip() for item in payload]
        else:
            parsed_versions = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        versions.extend(version for version in parsed_versions if version)

    deduped: list[str] = []
    seen: set[str] = set()
    for version in versions:
        if version in seen:
            continue
        seen.add(version)
        deduped.append(version)
    return deduped


def version_slug(version: str) -> str:
    result = []
    for character in str(version or "").strip():
        if character.isalnum():
            result.append(character)
        else:
            result.append("_")
    return "".join(result).strip("_") or "unknown"


def read_declared_dependency_version(path: Path, package_name: str) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError(
            "dependency_file_unreadable",
            f"Could not read dependency file: {path}. {exc}",
        ) from exc

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ToolInvocationError(
            "dependency_missing",
            f"Dependencies object not found in: {path}",
        )

    value = dependencies.get(package_name)
    if not isinstance(value, str) or not value.strip():
        raise ToolInvocationError(
            "dependency_missing",
            f"{package_name} is not declared in: {path}",
        )

    return value.strip()


def write_declared_dependency_version(path: Path, package_name: str, version: str) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError(
            "dependency_file_unreadable",
            f"Could not update dependency file: {path}. {exc}",
        ) from exc

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ToolInvocationError(
            "dependency_missing",
            f"Dependencies object not found in: {path}",
        )

    dependencies[package_name] = version
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def remove_lock_dependencies(path: Path, package_names: list[str]) -> list[str]:
    if not path.is_file():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolInvocationError(
            "packages_lock_unreadable",
            f"Could not update packages-lock.json: {path}. {exc}",
        ) from exc

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        return []

    removed: list[str] = []
    for package_name in package_names:
        if package_name in dependencies:
            del dependencies[package_name]
            removed.append(package_name)

    if removed:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return removed


def read_locked_dependency_state(path: Path, package_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "package_name": package_name,
        "present": False,
        "version": "",
        "source": "",
        "depth": None,
    }
    if not path.is_file():
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        result["error"] = f"Could not read: {path}"
        return result

    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        return result

    package_payload = dependencies.get(package_name)
    if not isinstance(package_payload, dict):
        return result

    result["present"] = True
    result["version"] = str(package_payload.get("version") or "")
    result["source"] = str(package_payload.get("source") or "")
    result["depth"] = package_payload.get("depth")
    return result


def read_test_framework_state(
    project_root: Path,
    project_manifest_path: Path,
    package_manifest_path: Path,
    packages_lock_path: Path,
) -> dict[str, Any]:
    return {
        "project_manifest_dependency": read_declared_dependency_version(project_manifest_path, TEST_FRAMEWORK_PACKAGE_NAME),
        "package_manifest_dependency": read_declared_dependency_version(package_manifest_path, TEST_FRAMEWORK_PACKAGE_NAME),
        "locked_test_framework": read_locked_dependency_state(packages_lock_path, TEST_FRAMEWORK_PACKAGE_NAME),
        "locked_test_framework_performance": read_locked_dependency_state(
            packages_lock_path,
            TEST_FRAMEWORK_PERFORMANCE_PACKAGE_NAME,
        ),
        "locked_lightweight_package": read_locked_dependency_state(packages_lock_path, LIGHTWEIGHT_PACKAGE_NAME),
        "package_dependency_alignment": inspect_package_dependency_alignment(project_root),
    }


def write_test_framework_step_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, payload)


def run_self_json_command(command_args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, __file__, *command_args],
        check=False,
        capture_output=True,
        text=True,
    )

    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    parsed_stdout: dict[str, Any] | None = None
    parse_error = ""
    if stdout_text.strip():
        try:
            parsed_candidate = json.loads(stdout_text)
            if isinstance(parsed_candidate, dict):
                parsed_stdout = parsed_candidate
        except json.JSONDecodeError as exc:
            parse_error = str(exc)

    payload: dict[str, Any] = {
        "command": [sys.executable, __file__, *command_args],
        "exit_code": completed.returncode,
        "succeeded": completed.returncode == 0,
        "stdout_text": stdout_text,
        "stderr_text": stderr_text,
    }
    if parsed_stdout is not None:
        payload["stdout_json"] = parsed_stdout
    if parse_error:
        payload["stdout_parse_error"] = parse_error
    return payload


def decode_bridge_payload(response_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response_payload, dict):
        return {}
    payload_json = response_payload.get("payload_json")
    if not isinstance(payload_json, str) or not payload_json.strip():
        return {}
    try:
        decoded = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def extract_test_failure_names(payload: dict[str, Any]) -> list[str]:
    failures = payload.get("failures")
    if not isinstance(failures, list):
        return []

    names: list[str] = []
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        for key in ("name", "test_name", "fullName", "full_name"):
            value = str(failure.get(key) or "").strip()
            if value:
                names.append(value)
                break
    return names


def summarize_bridge_step(output: dict[str, Any]) -> dict[str, Any]:
    response_payload = output.get("stdout_json")
    decoded = decode_bridge_payload(response_payload if isinstance(response_payload, dict) else None)
    summary: dict[str, Any] = {
        "exit_code": output.get("exit_code"),
        "succeeded": output.get("succeeded"),
    }
    if isinstance(response_payload, dict):
        summary["transport_status"] = response_payload.get("status")
        error_payload = response_payload.get("error")
        if isinstance(error_payload, dict) and (error_payload.get("code") or error_payload.get("message")):
            summary["error"] = {
                "code": error_payload.get("code"),
                "message": error_payload.get("message"),
            }
    if decoded:
        summary["payload"] = decoded
    stderr_text = str(output.get("stderr_text") or "").strip()
    if stderr_text:
        summary["stderr_tail"] = truncate_text(stderr_text[-600:], 600)
    parse_error = str(output.get("stdout_parse_error") or "").strip()
    if parse_error:
        summary["stdout_parse_error"] = parse_error
    return summary


def summarize_editmode_step(output: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_bridge_step(output)
    payload = summary.get("payload") or {}
    if isinstance(payload, dict):
        summary["tests"] = {
            "status": payload.get("status"),
            "total": payload.get("total"),
            "passed": payload.get("passed"),
            "failed": payload.get("failed"),
            "skipped": payload.get("skipped"),
            "completion_basis": payload.get("completion_basis"),
            "failure_names": extract_test_failure_names(payload),
        }
    return summary


def summarize_compile_step(output: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_bridge_step(output)
    payload = summary.get("payload") or {}
    if isinstance(payload, dict):
        compile_payload = payload.get("result") if isinstance(payload.get("result"), dict) else payload
        summary["compile"] = {
            "status": compile_payload.get("status"),
            "compiled_assembly_count": compile_payload.get("compiled_assembly_count"),
            "error_count": compile_payload.get("error_count"),
            "warning_count": compile_payload.get("warning_count"),
        }
    return summary


def summarize_health_probe_step(output: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_bridge_step(output)
    payload = summary.get("payload") or {}
    report = payload.get("report") if isinstance(payload, dict) else {}
    if isinstance(report, dict):
        summary["health_probe"] = {
            "status": report.get("status"),
            "supported_operation_count": len(report.get("supported_operations") or []),
            "disabled_operation_count": len(report.get("disabled_operations") or []),
        }
    return summary


def summarize_project_refresh_step(output: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_bridge_step(output)
    payload = summary.get("payload") or {}
    if isinstance(payload, dict):
        summary["project_refresh"] = {
            "outcome": payload.get("outcome"),
            "refresh_settle_phase": payload.get("refresh_settle_phase"),
            "package_resolve_requested": payload.get("package_resolve_requested"),
            "health_probe_status": payload.get("health_probe_status"),
        }
    return summary


def summarize_batch_editmode_step(output: dict[str, Any]) -> dict[str, Any]:
    response_payload = output.get("stdout_json")
    summary: dict[str, Any] = {
        "exit_code": output.get("exit_code"),
        "succeeded": output.get("succeeded"),
    }
    if isinstance(response_payload, dict):
        summary["result_summary"] = response_payload.get("result_summary")
        summary["result_file"] = response_payload.get("result_file")
        summary["summary_file"] = response_payload.get("summary_file")
        summary["top_actionable_error"] = response_payload.get("top_actionable_error")
        result_file = response_payload.get("result_file")
        if isinstance(result_file, str) and result_file.strip():
            result_path = Path(result_file).expanduser().resolve()
            if result_path.is_file():
                try:
                    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    result_payload = None
                if isinstance(result_payload, dict):
                    tests_payload = result_payload.get("tests") or {}
                    if isinstance(tests_payload, dict):
                        summary["tests"] = {
                            "status": tests_payload.get("status"),
                            "total": tests_payload.get("total"),
                            "passed": tests_payload.get("passed"),
                            "failed": tests_payload.get("failed"),
                            "skipped": tests_payload.get("skipped"),
                            "failure_names": extract_test_failure_names(tests_payload),
                        }
    stderr_text = str(output.get("stderr_text") or "").strip()
    if stderr_text:
        summary["stderr_tail"] = truncate_text(stderr_text[-600:], 600)
    parse_error = str(output.get("stdout_parse_error") or "").strip()
    if parse_error:
        summary["stdout_parse_error"] = parse_error
    return summary


def evaluate_candidate_contract(candidate_result: dict[str, Any]) -> dict[str, Any]:
    state_after_open = candidate_result.get("state_after_open") or {}
    locked_test_framework = state_after_open.get("locked_test_framework") if isinstance(state_after_open, dict) else {}

    direct_focus = (((candidate_result.get("interactive") or {}).get("focused_editmode")) or {}).get("tests") or {}
    batch_focus = (((candidate_result.get("batch") or {}).get("focused_editmode")) or {}).get("tests") or {}
    direct_broad = (((candidate_result.get("interactive") or {}).get("broad_editmode")) or {}).get("tests") or {}
    batch_broad = (((candidate_result.get("batch") or {}).get("broad_editmode")) or {}).get("tests") or {}
    compile_summary = (((candidate_result.get("interactive") or {}).get("compile")) or {}).get("compile") or {}
    health_probe = (((candidate_result.get("interactive") or {}).get("health_probe")) or {}).get("health_probe") or {}
    project_refresh = (((candidate_result.get("interactive") or {}).get("project_refresh")) or {}).get("project_refresh") or {}

    requested_version = str(candidate_result.get("requested_version") or "")
    resolved_version = str((locked_test_framework or {}).get("version") or "")

    failures: list[str] = []
    if not requested_version or requested_version != resolved_version:
        failures.append("resolved_version_mismatch")
    if str(health_probe.get("status") or "") != "healthy":
        failures.append("health_probe_not_healthy")
    if str(project_refresh.get("outcome") or "") not in {
        "refreshed",
        "ok",
        "completed",
        "refresh_and_resolve_completed",
    }:
        failures.append("project_refresh_not_completed")
    if str(compile_summary.get("status") or "") != "passed":
        failures.append("compile_regression_failed")
    if str(direct_focus.get("status") or "") != "passed":
        failures.append("focused_direct_editmode_failed")
    if str(batch_focus.get("status") or "") != "passed":
        failures.append("focused_batch_editmode_failed")
    if direct_broad.get("total") is None:
        failures.append("broad_direct_editmode_missing")
    if batch_broad.get("total") is None:
        failures.append("broad_batch_editmode_missing")

    return {
        "requested_version": requested_version,
        "resolved_version": resolved_version,
        "broad_direct_failed": direct_broad.get("failed"),
        "broad_batch_failed": batch_broad.get("failed"),
        "focused_direct_status": direct_focus.get("status"),
        "focused_batch_status": batch_focus.get("status"),
        "compile_status": compile_summary.get("status"),
        "health_status": health_probe.get("status"),
        "project_refresh_outcome": project_refresh.get("outcome"),
        "contract_passed": len(failures) == 0,
        "contract_failures": failures,
    }


def compare_candidate_to_baseline(
    baseline_result: dict[str, Any],
    candidate_result: dict[str, Any],
) -> dict[str, Any]:
    baseline_direct = (((baseline_result.get("interactive") or {}).get("broad_editmode")) or {}).get("tests") or {}
    baseline_batch = (((baseline_result.get("batch") or {}).get("broad_editmode")) or {}).get("tests") or {}
    candidate_direct = (((candidate_result.get("interactive") or {}).get("broad_editmode")) or {}).get("tests") or {}
    candidate_batch = (((candidate_result.get("batch") or {}).get("broad_editmode")) or {}).get("tests") or {}

    baseline_direct_failures = set(baseline_direct.get("failure_names") or [])
    baseline_batch_failures = set(baseline_batch.get("failure_names") or [])
    candidate_direct_failures = set(candidate_direct.get("failure_names") or [])
    candidate_batch_failures = set(candidate_batch.get("failure_names") or [])

    return {
        "baseline_version": baseline_result.get("requested_version"),
        "direct_failed_delta": (candidate_direct.get("failed") or 0) - (baseline_direct.get("failed") or 0),
        "batch_failed_delta": (candidate_batch.get("failed") or 0) - (baseline_batch.get("failed") or 0),
        "direct_new_failures": sorted(candidate_direct_failures - baseline_direct_failures),
        "batch_new_failures": sorted(candidate_batch_failures - baseline_batch_failures),
        "direct_missing_failures": sorted(baseline_direct_failures - candidate_direct_failures),
        "batch_missing_failures": sorted(baseline_batch_failures - candidate_batch_failures),
    }


def run_single_test_framework_candidate(
    *,
    project_root: Path,
    requested_version: str,
    project_manifest_path: Path,
    package_manifest_path: Path,
    packages_lock_path: Path,
    artifacts_dir: Path,
    compile_target: str,
    focus_assemblies: list[str],
    focus_tests: list[str],
    broad_assemblies: list[str],
) -> dict[str, Any]:
    candidate_slug = version_slug(requested_version)
    candidate_dir = artifacts_dir / candidate_slug
    candidate_dir.mkdir(parents=True, exist_ok=True)

    write_declared_dependency_version(project_manifest_path, TEST_FRAMEWORK_PACKAGE_NAME, requested_version)
    write_declared_dependency_version(package_manifest_path, TEST_FRAMEWORK_PACKAGE_NAME, requested_version)
    removed_lock_entries = remove_lock_dependencies(packages_lock_path, TEST_FRAMEWORK_REGRESSION_LOCK_PACKAGES)

    result: dict[str, Any] = {
        "requested_version": requested_version,
        "candidate_slug": candidate_slug,
        "candidate_dir": str(candidate_dir),
        "removed_lock_entries": removed_lock_entries,
        "state_after_patch": read_test_framework_state(
            project_root,
            project_manifest_path,
            package_manifest_path,
            packages_lock_path,
        ),
        "interactive": {},
        "batch": {},
    }

    ensure_ready_output = run_self_json_command(
        [
            "ensure-ready",
            "--project-root",
            str(project_root),
            "--open-editor",
            "--timeout-ms",
            "180000",
        ]
    )
    write_test_framework_step_artifact(candidate_dir / "interactive_ensure_ready.json", ensure_ready_output)
    result["interactive"]["ensure_ready"] = summarize_bridge_step(ensure_ready_output)

    if ensure_ready_output.get("succeeded"):
        result["state_after_open"] = read_test_framework_state(
            project_root,
            project_manifest_path,
            package_manifest_path,
            packages_lock_path,
        )

        health_probe_output = run_self_json_command(
            [
                "request-health-probe",
                "--project-root",
                str(project_root),
                "--timeout-ms",
                "30000",
            ]
        )
        write_test_framework_step_artifact(candidate_dir / "interactive_health_probe.json", health_probe_output)
        result["interactive"]["health_probe"] = summarize_health_probe_step(health_probe_output)

        project_refresh_output = run_self_json_command(
            [
                "request-project-refresh",
                "--project-root",
                str(project_root),
                "--timeout-ms",
                "120000",
            ]
        )
        write_test_framework_step_artifact(candidate_dir / "interactive_project_refresh.json", project_refresh_output)
        result["interactive"]["project_refresh"] = summarize_project_refresh_step(project_refresh_output)

        compile_output = run_self_json_command(
            [
                "request-compile",
                "--project-root",
                str(project_root),
                "--target",
                compile_target,
                "--name",
                f"test_framework_regression_{candidate_slug}",
                "--timeout-ms",
                "180000",
            ]
        )
        write_test_framework_step_artifact(candidate_dir / "interactive_compile.json", compile_output)
        result["interactive"]["compile"] = summarize_compile_step(compile_output)

        focused_editmode_args = [
            "request-editmode-tests",
            "--project-root",
            str(project_root),
            "--timeout-ms",
            "600000",
        ]
        for assembly_name in focus_assemblies:
            focused_editmode_args.extend(["--assembly-name", assembly_name])
        for test_name in focus_tests:
            focused_editmode_args.extend(["--test-name", test_name])
        focused_editmode_output = run_self_json_command(focused_editmode_args)
        write_test_framework_step_artifact(candidate_dir / "interactive_focused_editmode.json", focused_editmode_output)
        result["interactive"]["focused_editmode"] = summarize_editmode_step(focused_editmode_output)

        broad_editmode_args = [
            "request-editmode-tests",
            "--project-root",
            str(project_root),
            "--timeout-ms",
            "600000",
        ]
        for assembly_name in broad_assemblies:
            broad_editmode_args.extend(["--assembly-name", assembly_name])
        broad_editmode_output = run_self_json_command(broad_editmode_args)
        write_test_framework_step_artifact(candidate_dir / "interactive_broad_editmode.json", broad_editmode_output)
        result["interactive"]["broad_editmode"] = summarize_editmode_step(broad_editmode_output)

    close_output = run_self_json_command(
        [
            "restore-editor-state",
            "--project-root",
            str(project_root),
            "--timeout-ms",
            "30000",
        ]
    )
    write_test_framework_step_artifact(candidate_dir / "restore_editor_state.json", close_output)
    result["restore_editor_state"] = summarize_bridge_step(close_output)

    focused_batch_args = [
        "batch-editmode-tests",
        "--project-root",
        str(project_root),
    ]
    for assembly_name in focus_assemblies:
        focused_batch_args.extend(["--assembly-name", assembly_name])
    for test_name in focus_tests:
        focused_batch_args.extend(["--test-name", test_name])
    focused_batch_output = run_self_json_command(focused_batch_args)
    write_test_framework_step_artifact(candidate_dir / "batch_focused_editmode.json", focused_batch_output)
    result["batch"]["focused_editmode"] = summarize_batch_editmode_step(focused_batch_output)

    broad_batch_args = [
        "batch-editmode-tests",
        "--project-root",
        str(project_root),
    ]
    for assembly_name in broad_assemblies:
        broad_batch_args.extend(["--assembly-name", assembly_name])
    broad_batch_output = run_self_json_command(broad_batch_args)
    write_test_framework_step_artifact(candidate_dir / "batch_broad_editmode.json", broad_batch_output)
    result["batch"]["broad_editmode"] = summarize_batch_editmode_step(broad_batch_output)

    result["contract"] = evaluate_candidate_contract(result)
    return result


def cmd_request_scenario_validate(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    response = invoke_bridge(
        args.project_root,
        "unity.scenario.validate",
        {"scenario": scenario},
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_scenario_run(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    project_root = ensure_project_root(args.project_root)
    response = invoke_bridge(
        str(project_root),
        "unity.scenario.run",
        {"scenario": scenario},
        resolve_operation_default_timeout_ms(project_root, "unity.scenario.run", 600000) if args.timeout_ms is None else args.timeout_ms,
    )
    print_json(response)


def cmd_request_scenario_run_and_wait(args):
    scenario = load_json_file(args.scenario_file, "scenario_file_invalid")
    project_root = ensure_project_root(args.project_root)
    result = call_unity_scenario_run_and_wait_tool(
        {
            "projectRoot": str(project_root),
            "scenario": scenario,
            "timeoutMs": args.timeout_ms,
            "pollIntervalMs": args.poll_interval_ms,
        }
    )
    print_json(result.get("structuredContent") or {})
    if result.get("isError"):
        raise SystemExit(1)


def cmd_request_scenario_result(args):
    bridge_args: dict[str, Any] = {}
    if args.run_id:
        bridge_args["runId"] = args.run_id
    if args.scenario_name:
        bridge_args["scenarioName"] = args.scenario_name

    response = invoke_bridge(
        args.project_root,
        "unity.scenario.result",
        bridge_args,
        args.timeout_ms,
    )
    print_json(response)


def cmd_request_scenario_result_summary(args):
    bridge_args: dict[str, Any] = {}
    if args.run_id:
        bridge_args["runId"] = args.run_id
    if args.scenario_name:
        bridge_args["scenarioName"] = args.scenario_name

    response = invoke_bridge(
        args.project_root,
        "unity.scenario.result",
        bridge_args,
        args.timeout_ms,
    )
    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        print_json(tool_result.get("structuredContent") or {})
        raise SystemExit(1)
    payload = tool_result.get("structuredContent") or {}
    print_json(build_scenario_result_summary(
        payload if isinstance(payload, dict) else {},
        SCENARIO_TERMINAL_STATUSES,
    ))


def cmd_maintenance_prune(args):
    project_root = ensure_project_root(args.project_root)
    result = prune_project_artifacts(
        project_root,
        {
            "dryRun": args.dry_run,
            "requestJournalMaxAgeHours": args.request_journal_max_age_hours,
            "requestJournalKeepLatest": args.request_journal_keep_latest,
            "scenarioSuccessMaxAgeHours": args.scenario_success_max_age_hours,
            "scenarioFailureMaxAgeHours": args.scenario_failure_max_age_hours,
            "scenarioRunningMaxAgeHours": args.scenario_running_max_age_hours,
            "scenarioKeepLatestSuccess": args.scenario_keep_latest_success,
            "scenarioKeepLatestFailure": args.scenario_keep_latest_failure,
            "scenarioKeepLatestRunning": args.scenario_keep_latest_running,
            "capturesMaxAgeHours": args.captures_max_age_hours,
            "capturesKeepLatest": args.captures_keep_latest,
            "pruneLogs": args.prune_logs,
            "logsMaxAgeHours": args.logs_max_age_hours,
            "logsKeepLatest": args.logs_keep_latest,
        },
        bridge_root=bridge_root,
        request_journal_dir=request_journal_dir,
        scenario_results_dir=scenario_results_dir,
        active_scenario_run_path=active_scenario_run_path,
        captures_dir=captures_dir,
        logs_dir=logs_dir,
        default_editor_log_path=default_editor_log_path,
        read_json=read_json,
    )
    print_json(result)


def cmd_open_editor(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    log_path = resolve_editor_log_path(project_root, args.editor_log_path)
    payload = open_unity_editor(project_root, log_path, unity_app, args.background_open)
    payload["project_root"] = str(project_root)
    print_json(payload)


def cmd_ensure_ready(args):
    project_root = ensure_project_root(args.project_root)
    log_path = resolve_editor_log_path(project_root, args.editor_log_path)

    payload: dict[str, Any] = {
        "project_root": str(project_root),
        "editor_log_path": str(log_path),
        "startup_policy": args.startup_policy,
    }

    current_state = try_read_bridge_state(project_root)

    if args.open_editor and bridge_state_is_ready(current_state, args.heartbeat_max_age_seconds):
        payload["launch"] = {
            "reused_existing_editor": True,
            "reused_via": "healthy_bridge_state",
            "editor_pid": int(current_state.get("editor_pid") or 0),
            "unity_version": str(current_state.get("unity_version") or ""),
        }
    elif args.open_editor:
        unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
        payload["launch"] = open_unity_editor(project_root, log_path, unity_app, args.background_open)

    state = wait_for_ready(
        project_root=project_root,
        timeout_ms=args.timeout_ms,
        heartbeat_max_age_seconds=args.heartbeat_max_age_seconds,
        startup_policy=args.startup_policy,
        editor_log_path=log_path,
    )
    payload["bridge_state"] = state
    if payload.get("launch") and not bool(payload["launch"].get("reused_existing_editor")):
        update_host_editor_session_pid(project_root, int(state.get("editor_pid") or 0))
    payload["package_dependency"] = inspect_package_dependency_alignment(project_root)
    print_json(payload)


def cmd_restore_editor_state(args):
    project_root = ensure_project_root(args.project_root)
    payload = restore_host_opened_editor_state(project_root, args.timeout_ms, request_editor_quit)
    print_json(payload)


def cmd_runtime_config_show(args):
    project_root = ensure_project_root(args.project_root)
    print_json(build_runtime_config_report(project_root))


def cmd_batch_test_framework_version_regression(args):
    project_root = ensure_project_root(args.project_root)
    project_manifest_path = project_root / "Packages" / "manifest.json"
    packages_lock_path = project_root / "Packages" / "packages-lock.json"

    package_source = find_repo_local_package_source(project_root)
    if package_source is None:
        raise ToolInvocationError(
            "repo_local_package_source_not_found",
            (
                "Could not locate the repo-local XUUnityLightUnityMcp package source from this project root. "
                "Run devmode first so the project points at the local AIRoot package."
            ),
        )
    package_manifest_path = package_source / "package.json"

    original_state = read_test_framework_state(
        project_root,
        project_manifest_path,
        package_manifest_path,
        packages_lock_path,
    )
    requested_versions = normalize_requested_versions(list(args.version or []), args.versions_file)
    if not requested_versions:
        requested_versions = [str(original_state.get("project_manifest_dependency") or "")]

    focus_assemblies = list(args.focus_assembly_name or TEST_FRAMEWORK_REGRESSION_FOCUS_ASSEMBLIES)
    focus_tests = list(args.focus_test_name or TEST_FRAMEWORK_REGRESSION_FOCUS_TESTS)
    broad_assemblies = list(args.broad_assembly_name or [])
    compile_target = str(args.compile_target or TEST_FRAMEWORK_REGRESSION_COMPILE_TARGET).strip()
    if not compile_target:
        raise ToolInvocationError("missing_compile_target", "--compile-target must not be empty.")

    live_editor_pids = list_live_project_editor_pids(project_root)
    host_session = try_read_host_editor_session_state(project_root) or {}
    tracked_host_pid = int(host_session.get("editor_pid") or 0)
    host_managed_live_editor = bool(host_session.get("opened_by_host")) and tracked_host_pid > 0 and tracked_host_pid in live_editor_pids
    if live_editor_pids and not host_managed_live_editor:
        raise ToolInvocationError(
            "editor_running_regression_conflict",
            (
                "Refusing to start test-framework version regression while this project is open in a non-host-managed "
                f"Unity editor session. Live editor pid(s): {', '.join(str(pid) for pid in live_editor_pids)}. "
                "Close the editor first, or reopen it through ensure-ready so the host can restore it safely."
            ),
            {
                "live_editor_pids": live_editor_pids,
                "tracked_host_pid": tracked_host_pid,
            },
        )

    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else test_framework_regression_result_path(project_root)
    )
    artifacts_dir = test_framework_regression_artifacts_dir(result_path)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    overall_result: dict[str, Any] = {
        "action": "batch_test_framework_version_regression",
        "project_root": str(project_root),
        "result_file": str(result_path),
        "artifacts_dir": str(artifacts_dir),
        "requested_versions": requested_versions,
        "initial_editor_state": {
            "live_editor_pids": live_editor_pids,
            "host_managed_live_editor": host_managed_live_editor,
            "tracked_host_pid": tracked_host_pid,
            "restore_editor_open_state": bool(live_editor_pids),
        },
        "focus_assemblies": focus_assemblies,
        "focus_tests": focus_tests,
        "broad_assemblies": broad_assemblies,
        "compile_target": compile_target,
        "original_state": original_state,
        "candidates": [],
        "restoration": {},
    }

    baseline_result: dict[str, Any] | None = None

    try:
        if live_editor_pids and host_managed_live_editor:
            preclose_output = run_self_json_command(
                [
                    "restore-editor-state",
                    "--project-root",
                    str(project_root),
                    "--timeout-ms",
                    "30000",
                ]
            )
            write_test_framework_step_artifact(artifacts_dir / "preclose_editor.json", preclose_output)
            overall_result["initial_editor_state"]["preclose"] = summarize_bridge_step(preclose_output)

        for requested_version in requested_versions:
            candidate_result = run_single_test_framework_candidate(
                project_root=project_root,
                requested_version=requested_version,
                project_manifest_path=project_manifest_path,
                package_manifest_path=package_manifest_path,
                packages_lock_path=packages_lock_path,
                artifacts_dir=artifacts_dir,
                compile_target=compile_target,
                focus_assemblies=focus_assemblies,
                focus_tests=focus_tests,
                broad_assemblies=broad_assemblies,
            )
            overall_result["candidates"].append(candidate_result)
            if requested_version == str(original_state.get("project_manifest_dependency") or ""):
                baseline_result = candidate_result
    finally:
        restoration: dict[str, Any] = {
            "restore_original_version": bool(args.restore_original_version),
        }
        if args.restore_original_version:
            write_declared_dependency_version(
                project_manifest_path,
                TEST_FRAMEWORK_PACKAGE_NAME,
                str(original_state.get("project_manifest_dependency") or ""),
            )
            write_declared_dependency_version(
                package_manifest_path,
                TEST_FRAMEWORK_PACKAGE_NAME,
                str(original_state.get("package_manifest_dependency") or ""),
            )
            restoration["removed_lock_entries"] = remove_lock_dependencies(
                packages_lock_path,
                TEST_FRAMEWORK_REGRESSION_LOCK_PACKAGES,
            )
            restoration["state_after_restore_patch"] = read_test_framework_state(
                project_root,
                project_manifest_path,
                package_manifest_path,
                packages_lock_path,
            )
            if bool(overall_result["initial_editor_state"].get("restore_editor_open_state")):
                reopen_output = run_self_json_command(
                    [
                        "ensure-ready",
                        "--project-root",
                        str(project_root),
                        "--open-editor",
                        "--timeout-ms",
                        "180000",
                    ]
                )
                write_test_framework_step_artifact(artifacts_dir / "restore_editor_open_state.json", reopen_output)
                restoration["reopen_editor"] = summarize_bridge_step(reopen_output)
                restoration["state_after_reopen"] = read_test_framework_state(
                    project_root,
                    project_manifest_path,
                    package_manifest_path,
                    packages_lock_path,
                )
        overall_result["restoration"] = restoration

    if baseline_result is not None:
        for candidate_result in overall_result["candidates"]:
            candidate_result["broad_suite_vs_baseline"] = compare_candidate_to_baseline(
                baseline_result,
                candidate_result,
            )

    overall_result["summary"] = {
        "candidate_count": len(overall_result["candidates"]),
        "contract_passed_versions": [
            candidate_result.get("requested_version")
            for candidate_result in overall_result["candidates"]
            if bool(((candidate_result.get("contract") or {}).get("contract_passed")))
        ],
        "baseline_version": baseline_result.get("requested_version") if baseline_result else "",
    }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(result_path, overall_result)
    print_json(overall_result)

    if any(not bool(((candidate_result.get("contract") or {}).get("contract_passed"))) for candidate_result in overall_result["candidates"]):
        raise SystemExit(1)


def cmd_batch_compile(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    build_target = str(args.target or "").strip()
    if not build_target:
        raise ToolInvocationError("missing_build_target", "--target is required.")

    operation_suffix = build_target if not args.name else f"{build_target}_{args.name}"
    log_path = (
        Path(args.batch_log_path).expanduser().resolve()
        if args.batch_log_path
        else default_batch_operation_log_path(project_root, f"compile_{operation_suffix}")
    )
    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else default_batch_operation_result_path(project_root, f"compile_{operation_suffix}")
    )

    extra_args = [
        "--xuunity-build-target",
        build_target,
    ]
    if args.name:
        extra_args.extend(["--xuunity-compile-name", args.name])
    for option_flag in list(args.option_flag or []):
        extra_args.extend(["--xuunity-option-flag", option_flag])
    for extra_define in list(args.extra_define or []):
        extra_args.extend(["--xuunity-extra-define", extra_define])

    command = build_batch_validation_command(
        project_root=project_root,
        unity_app=unity_app,
        log_path=log_path,
        result_path=result_path,
        action="compile-player-scripts",
        extra_args=extra_args,
    )
    payload = {
        "action": "batch_compile_player_scripts",
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "build_target": build_target,
        "compile_name": args.name or "",
        "option_flags": list(args.option_flag or []),
        "extra_defines": list(args.extra_define or []),
        "log_path": str(log_path),
        "result_file": str(result_path),
        "command": command,
        "dry_run": args.dry_run,
    }
    run_batch_operation(
        project_root=project_root,
        command=command,
        payload=payload,
        log_path=log_path,
        result_path=result_path,
        dry_run=args.dry_run,
    )


def cmd_batch_compile_matrix(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    config_file = Path(args.config_file).expanduser().resolve()
    if not config_file.is_file():
        raise ToolInvocationError("compile_matrix_config_not_found", f"Compile matrix config file not found: {config_file}")

    log_path = (
        Path(args.batch_log_path).expanduser().resolve()
        if args.batch_log_path
        else default_batch_operation_log_path(project_root, "compile_matrix")
    )
    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else default_batch_operation_result_path(project_root, "compile_matrix")
    )

    command = build_batch_validation_command(
        project_root=project_root,
        unity_app=unity_app,
        log_path=log_path,
        result_path=result_path,
        action="compile-matrix",
        extra_args=["--xuunity-config-file", str(config_file)],
    )
    payload = {
        "action": "batch_compile_matrix",
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "config_file": str(config_file),
        "log_path": str(log_path),
        "result_file": str(result_path),
        "command": command,
        "dry_run": args.dry_run,
    }
    run_batch_operation(
        project_root=project_root,
        command=command,
        payload=payload,
        log_path=log_path,
        result_path=result_path,
        dry_run=args.dry_run,
    )


def cmd_batch_build_config_compile_matrix(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    compile_plan = build_compile_matrix_args_from_build_config(
        project_root=project_root,
        build_config_asset=args.build_config_asset,
        requested_profiles=args.profile,
        requested_targets=args.target,
        stop_on_first_failure=args.stop_on_first_failure,
        tool_error_type=ToolInvocationError,
    )
    log_path = (
        Path(args.batch_log_path).expanduser().resolve()
        if args.batch_log_path
        else default_batch_operation_log_path(project_root, "build_config_compile_matrix")
    )
    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else default_batch_operation_result_path(project_root, "build_config_compile_matrix")
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="_xuunity_compile_matrix.json",
        delete=False,
    ) as temp_file:
        temp_config_path = Path(temp_file.name)
    try:
        temp_config_path.write_text(json.dumps(compile_plan["matrixArgs"], indent=2) + "\n", encoding="utf-8")
        command = build_batch_validation_command(
            project_root=project_root,
            unity_app=unity_app,
            log_path=log_path,
            result_path=result_path,
            action="compile-matrix",
            extra_args=["--xuunity-config-file", str(temp_config_path)],
        )
        payload = {
            "action": "batch_build_config_compile_matrix",
            "project_root": str(project_root),
            "unity_app": str(unity_app),
            "build_config_asset": compile_plan["assetPath"],
            "profiles": compile_plan["profiles"],
            "generated_config_file": str(temp_config_path),
            "log_path": str(log_path),
            "result_file": str(result_path),
            "command": command,
            "dry_run": False,
        }
        run_batch_operation(
            project_root=project_root,
            command=command,
            payload=payload,
            log_path=log_path,
            result_path=result_path,
            dry_run=False,
        )
    finally:
        try:
            temp_config_path.unlink()
        except OSError:
            pass


def cmd_batch_editmode_tests(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    log_path = (
        Path(args.batch_log_path).expanduser().resolve()
        if args.batch_log_path
        else default_batch_operation_log_path(project_root, "editmode_tests")
    )
    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else default_batch_operation_result_path(project_root, "editmode_tests")
    )

    extra_args: list[str] = []
    for test_name in list(args.test_names or []):
        extra_args.extend(["--xuunity-test-name", test_name])
    for group_name in list(args.group_names or []):
        extra_args.extend(["--xuunity-group-name", group_name])
    for category_name in list(args.category_names or []):
        extra_args.extend(["--xuunity-category-name", category_name])
    for assembly_name in list(args.assembly_names or []):
        extra_args.extend(["--xuunity-assembly-name", assembly_name])

    command = build_batch_validation_command(
        project_root=project_root,
        unity_app=unity_app,
        log_path=log_path,
        result_path=result_path,
        action="editmode-tests",
        extra_args=extra_args,
    )
    payload = {
        "action": "batch_editmode_tests",
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "test_names": list(args.test_names or []),
        "group_names": list(args.group_names or []),
        "category_names": list(args.category_names or []),
        "assembly_names": list(args.assembly_names or []),
        "log_path": str(log_path),
        "result_file": str(result_path),
        "command": command,
        "dry_run": args.dry_run,
    }
    run_batch_operation(
        project_root=project_root,
        command=command,
        payload=payload,
        log_path=log_path,
        result_path=result_path,
        dry_run=args.dry_run,
    )


def cmd_batch_build_player(args):
    project_root = ensure_project_root(args.project_root)
    unity_app = detect_unity_app_path_for_project(project_root, args.unity_app)
    build_target = str(args.build_target or "").strip()
    if not build_target:
        raise ToolInvocationError("missing_build_target", "--build-target is required.")

    log_path = (
        Path(args.batch_log_path).expanduser().resolve()
        if args.batch_log_path
        else default_batch_build_log_path(project_root, build_target)
    )
    result_path = (
        Path(args.result_file).expanduser().resolve()
        if args.result_file
        else default_batch_build_result_path(project_root, build_target)
    )
    output_path = resolve_batch_build_output_path(project_root, args.output_path)
    scene_paths = list(args.scene_path or [])
    build_options = list(args.build_option or [])

    command = build_plain_batch_build_command(
        project_root=project_root,
        unity_app=unity_app,
        log_path=log_path,
        result_path=result_path,
        build_target=build_target,
        output_path=output_path,
        scene_paths=scene_paths,
        build_options=build_options,
    )

    payload: dict[str, Any] = {
        "action": "plain_batch_build",
        "project_root": str(project_root),
        "unity_app": str(unity_app),
        "build_target": build_target,
        "output_path": output_path,
        "scene_paths": scene_paths,
        "build_options": build_options,
        "log_path": str(log_path),
        "result_file": str(result_path),
        "command": command,
        "dry_run": args.dry_run,
    }
    summary_path = batch_summary_artifact_path(result_path)
    payload["summary_file"] = str(summary_path)

    if args.dry_run:
        print_json(payload)
        return

    live_editor_pids = list_live_project_editor_pids(project_root)
    if live_editor_pids:
        exc = ToolInvocationError(
            "editor_running_batch_conflict",
            (
                "Refusing to start a plain batch build while the Unity project is open in the editor. "
                f"Live editor pid(s): {', '.join(str(pid) for pid in live_editor_pids)}. "
                "Close the editor first or use a host-local wrapper that manages editor shutdown/reopen explicitly."
            ),
            {"live_editor_pids": live_editor_pids},
        )
        summary = build_batch_prepare_failure_summary(
            action="plain_batch_build",
            result_path=result_path,
            log_path=log_path,
            exc=exc,
        )
        write_batch_summary_artifact(summary_path, summary)
        raise attach_batch_summary_to_error(exc, summary_path=summary_path, summary=summary)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    stale_lock = clear_stale_project_lock(project_root)
    payload["stale_lock"] = stale_lock

    command_started_at = time.time()
    completed = subprocess.run(command, check=False)
    payload["batch_exit_code"] = completed.returncode

    result_payload = try_read_json_dict(result_path, read_json)
    if result_payload is not None:
        payload["build_result_payload_present"] = True
        payload["succeeded"] = bool(result_payload.get("succeeded", False)) and completed.returncode == 0
    else:
        payload["build_result_payload_present"] = False
        payload["succeeded"] = completed.returncode == 0

    log_excerpt_hint = ""
    if completed.returncode != 0 or not bool(payload.get("succeeded")):
        log_excerpt = read_recent_editor_log(log_path, command_started_at)
        if log_excerpt:
            log_excerpt_hint = truncate_text(log_excerpt[-600:], 600)

    result_summary = build_batch_execution_summary(
        action="plain_batch_build",
        result_payload=result_payload,
        batch_exit_code=completed.returncode,
        succeeded=bool(payload.get("succeeded")),
        result_path=result_path,
        log_path=log_path,
        log_excerpt_hint=log_excerpt_hint,
    )
    write_batch_summary_artifact(summary_path, result_summary)
    payload["build_result_summary"] = result_summary
    if "top_actionable_error" in result_summary:
        payload["top_actionable_error"] = result_summary["top_actionable_error"]

    print_json(payload)
    if completed.returncode != 0 or not bool(payload.get("succeeded")):
        raise SystemExit(1)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "XUUnity Light Unity MCP server. "
            "Without arguments it serves MCP over stdio. "
            "Subcommands are local diagnostics helpers."
        )
    )
    sub = parser.add_subparsers(dest="command")

    state_cmd = sub.add_parser("bridge-state", help="Read the Unity bridge heartbeat state file.")
    state_cmd.add_argument("--project-root", required=True)
    state_cmd.set_defaults(func=cmd_bridge_state)

    status_cmd = sub.add_parser("request-status", help="Send a direct unity.status request through the active bridge transport.")
    status_cmd.add_argument("--project-root", required=True)
    status_cmd.add_argument("--timeout-ms", type=int, default=5000)
    status_cmd.set_defaults(func=cmd_request_status)

    status_summary_cmd = sub.add_parser("request-status-summary", help="Send unity.status and print a compact summary suitable for polling.")
    status_summary_cmd.add_argument("--project-root", required=True)
    status_summary_cmd.add_argument("--timeout-ms", type=int, default=5000)
    status_summary_cmd.set_defaults(func=cmd_request_status_summary)

    latest_status_cmd = sub.add_parser(
        "request-latest-status",
        help="Recover the latest request summary from the journal, optionally narrowed by one or more operation names.",
    )
    latest_status_cmd.add_argument("--project-root", required=True)
    latest_status_cmd.add_argument("--operation", action="append", default=[])
    latest_status_cmd.add_argument("--timeout-ms", type=int, default=2000)
    latest_status_cmd.set_defaults(func=cmd_request_latest_status)

    final_status_cmd = sub.add_parser("request-final-status", help="Summarize final disposition for a request id using the request journal and current bridge state.")
    final_status_cmd.add_argument("--project-root", required=True)
    final_status_cmd.add_argument("--request-id", required=True)
    final_status_cmd.add_argument("--operation")
    final_status_cmd.add_argument("--timeout-ms", type=int, default=2000)
    final_status_cmd.set_defaults(func=cmd_request_final_status)

    playmode_state_cmd = sub.add_parser("request-playmode-state", help="Send a direct unity.playmode.state request through the active bridge transport.")
    playmode_state_cmd.add_argument("--project-root", required=True)
    playmode_state_cmd.add_argument("--timeout-ms", type=int, default=5000)
    playmode_state_cmd.set_defaults(func=cmd_request_playmode_state)

    playmode_set_cmd = sub.add_parser("request-playmode-set", help="Send a direct unity.playmode.set request through the active bridge transport.")
    playmode_set_cmd.add_argument("--project-root", required=True)
    playmode_set_cmd.add_argument("--action", required=True, choices=["enter", "exit", "pause", "resume"])
    playmode_set_cmd.add_argument("--timeout-ms", type=int, default=None)
    playmode_set_cmd.set_defaults(func=cmd_request_playmode_set)

    capabilities_cmd = sub.add_parser("request-capabilities", help="Send a direct unity.capabilities.get request through the active bridge transport.")
    capabilities_cmd.add_argument("--project-root", required=True)
    capabilities_cmd.add_argument("--timeout-ms", type=int, default=5000)
    capabilities_cmd.set_defaults(func=cmd_request_capabilities)

    probe_cmd = sub.add_parser("request-health-probe", help="Send a direct unity.health.probe request through the active bridge transport.")
    probe_cmd.add_argument("--project-root", required=True)
    probe_cmd.add_argument("--timeout-ms", type=int, default=15000)
    probe_cmd.set_defaults(func=cmd_request_health_probe)

    build_target_get_cmd = sub.add_parser("request-build-target-get", help="Send a direct unity.build_target.get request through the active bridge transport.")
    build_target_get_cmd.add_argument("--project-root", required=True)
    build_target_get_cmd.add_argument("--timeout-ms", type=int, default=5000)
    build_target_get_cmd.set_defaults(func=cmd_request_build_target_get)

    build_target_switch_cmd = sub.add_parser("request-build-target-switch", help="Send a direct unity.build_target.switch request through the active bridge transport.")
    build_target_switch_cmd.add_argument("--project-root", required=True)
    build_target_switch_cmd.add_argument("--target", required=True)
    build_target_switch_cmd.add_argument("--timeout-ms", type=int, default=120000)
    build_target_switch_cmd.set_defaults(func=cmd_request_build_target_switch)

    editor_quit_cmd = sub.add_parser("request-editor-quit", help="Send a direct unity.editor.quit request through the active bridge transport.")
    editor_quit_cmd.add_argument("--project-root", required=True)
    editor_quit_cmd.add_argument("--timeout-ms", type=int, default=15000)
    editor_quit_cmd.set_defaults(func=cmd_request_editor_quit)

    project_refresh_cmd = sub.add_parser("request-project-refresh", help="Send a direct unity.project.refresh request through the active bridge transport.")
    project_refresh_cmd.add_argument("--project-root", required=True)
    project_refresh_cmd.add_argument("--force-asset-refresh", dest="force_asset_refresh", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--resolve-packages", dest="resolve_packages", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--rerun-health-probe", dest="rerun_health_probe", action=argparse.BooleanOptionalAction, default=True)
    project_refresh_cmd.add_argument("--timeout-ms", type=int, default=None)
    project_refresh_cmd.set_defaults(func=cmd_request_project_refresh)

    editmode_cmd = sub.add_parser("request-editmode-tests", help="Send a direct unity.tests.run_editmode request through the active bridge transport.")
    editmode_cmd.add_argument("--project-root", required=True)
    editmode_cmd.add_argument("--test-name", dest="test_names", action="append", default=[])
    editmode_cmd.add_argument("--group-name", dest="group_names", action="append", default=[])
    editmode_cmd.add_argument("--category-name", dest="category_names", action="append", default=[])
    editmode_cmd.add_argument("--assembly-name", dest="assembly_names", action="append", default=[])
    editmode_cmd.add_argument("--timeout-ms", type=int, default=None)
    editmode_cmd.set_defaults(func=cmd_request_editmode_tests)

    playmode_cmd = sub.add_parser("request-playmode-tests", help="Send a direct unity.tests.run_playmode request through the active bridge transport.")
    playmode_cmd.add_argument("--project-root", required=True)
    playmode_cmd.add_argument("--test-name", dest="test_names", action="append", default=[])
    playmode_cmd.add_argument("--group-name", dest="group_names", action="append", default=[])
    playmode_cmd.add_argument("--category-name", dest="category_names", action="append", default=[])
    playmode_cmd.add_argument("--assembly-name", dest="assembly_names", action="append", default=[])
    playmode_cmd.add_argument("--timeout-ms", type=int, default=None)
    playmode_cmd.set_defaults(func=cmd_request_playmode_tests)

    compile_cmd = sub.add_parser("request-compile", help="Send a direct unity.compile.player_scripts request through the active bridge transport.")
    compile_cmd.add_argument("--project-root", required=True)
    compile_cmd.add_argument("--target", required=True)
    compile_cmd.add_argument("--name", default="")
    compile_cmd.add_argument("--option-flag", dest="option_flags", action="append", default=[])
    compile_cmd.add_argument("--extra-define", dest="extra_defines", action="append", default=[])
    compile_cmd.add_argument("--timeout-ms", type=int, default=None)
    compile_cmd.set_defaults(func=cmd_request_compile)

    compile_matrix_cmd = sub.add_parser("request-compile-matrix", help="Send a direct unity.compile.matrix request using a JSON config file through the active bridge transport.")
    compile_matrix_cmd.add_argument("--project-root", required=True)
    compile_matrix_cmd.add_argument("--config-file", required=True)
    compile_matrix_cmd.add_argument("--timeout-ms", type=int, default=None)
    compile_matrix_cmd.set_defaults(func=cmd_request_compile_matrix)

    build_config_matrix_cmd = sub.add_parser(
        "request-build-config-compile-matrix",
        help="Resolve build profiles from the project's *BuildConfiguration.asset and run the Android/iOS compile matrix through unity.compile.matrix on the active bridge transport.",
    )
    build_config_matrix_cmd.add_argument("--project-root", required=True)
    build_config_matrix_cmd.add_argument("--build-config-asset")
    build_config_matrix_cmd.add_argument("--profile", action="append", default=[])
    build_config_matrix_cmd.add_argument("--target", action="append", default=[])
    build_config_matrix_cmd.add_argument("--stop-on-first-failure", action="store_true")
    build_config_matrix_cmd.add_argument("--timeout-ms", type=int, default=None)
    build_config_matrix_cmd.set_defaults(func=cmd_request_build_config_compile_matrix)

    scenario_validate_cmd = sub.add_parser("request-scenario-validate", help="Validate a Unity scenario JSON file through unity.scenario.validate on the active bridge transport.")
    scenario_validate_cmd.add_argument("--project-root", required=True)
    scenario_validate_cmd.add_argument("--scenario-file", required=True)
    scenario_validate_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_validate_cmd.set_defaults(func=cmd_request_scenario_validate)

    scenario_run_cmd = sub.add_parser("request-scenario-run", help="Start a Unity scenario JSON file through unity.scenario.run on the active bridge transport.")
    scenario_run_cmd.add_argument("--project-root", required=True)
    scenario_run_cmd.add_argument("--scenario-file", required=True)
    scenario_run_cmd.add_argument("--timeout-ms", type=int, default=None)
    scenario_run_cmd.set_defaults(func=cmd_request_scenario_run)

    scenario_run_wait_cmd = sub.add_parser("request-scenario-run-and-wait", help="Start a Unity scenario JSON file and wait until it reaches a terminal state.")
    scenario_run_wait_cmd.add_argument("--project-root", required=True)
    scenario_run_wait_cmd.add_argument("--scenario-file", required=True)
    scenario_run_wait_cmd.add_argument("--timeout-ms", type=int, default=None)
    scenario_run_wait_cmd.add_argument("--poll-interval-ms", type=int, default=1000)
    scenario_run_wait_cmd.set_defaults(func=cmd_request_scenario_run_and_wait)

    scenario_result_cmd = sub.add_parser("request-scenario-result", help="Read the current or completed result of a Unity scenario run.")
    scenario_result_cmd.add_argument("--project-root", required=True)
    scenario_result_cmd.add_argument("--run-id")
    scenario_result_cmd.add_argument("--scenario-name")
    scenario_result_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_result_cmd.set_defaults(func=cmd_request_scenario_result)

    scenario_result_summary_cmd = sub.add_parser("request-scenario-result-summary", help="Read the current or completed result of a Unity scenario run and print a compact summary.")
    scenario_result_summary_cmd.add_argument("--project-root", required=True)
    scenario_result_summary_cmd.add_argument("--run-id")
    scenario_result_summary_cmd.add_argument("--scenario-name")
    scenario_result_summary_cmd.add_argument("--timeout-ms", type=int, default=5000)
    scenario_result_summary_cmd.set_defaults(func=cmd_request_scenario_result_summary)

    open_editor_cmd = sub.add_parser("open-editor", help="Open a Unity project with a deterministic log file path for MCP startup diagnostics.")
    open_editor_cmd.add_argument("--project-root", required=True)
    open_editor_cmd.add_argument("--unity-app")
    open_editor_cmd.add_argument("--editor-log-path")
    open_editor_cmd.add_argument("--background-open", action="store_true")
    open_editor_cmd.set_defaults(func=cmd_open_editor)

    ensure_ready_cmd = sub.add_parser(
        "ensure-ready",
        help="Wait for a healthy Unity bridge heartbeat and fail fast on startup blockers visible in Editor.log.",
    )
    ensure_ready_cmd.add_argument("--project-root", required=True)
    ensure_ready_cmd.add_argument("--open-editor", action="store_true")
    ensure_ready_cmd.add_argument("--unity-app")
    ensure_ready_cmd.add_argument("--editor-log-path")
    ensure_ready_cmd.add_argument("--background-open", action="store_true")
    ensure_ready_cmd.add_argument("--timeout-ms", type=int, default=120000)
    ensure_ready_cmd.add_argument("--heartbeat-max-age-seconds", type=int, default=10)
    ensure_ready_cmd.add_argument(
        "--startup-policy",
        default="fail_fast_on_interactive_compile_block",
        choices=sorted(STARTUP_POLICIES),
    )
    ensure_ready_cmd.set_defaults(func=cmd_ensure_ready)

    restore_editor_cmd = sub.add_parser(
        "restore-editor-state",
        help="Close the Unity editor only when it was previously opened by this MCP host for the target project.",
    )
    restore_editor_cmd.add_argument("--project-root", required=True)
    restore_editor_cmd.add_argument("--timeout-ms", type=int, default=15000)
    restore_editor_cmd.set_defaults(func=cmd_restore_editor_state)

    runtime_config_cmd = sub.add_parser(
        "runtime-config-show",
        help="Print the merged runtime timeout configuration for this Unity project.",
    )
    runtime_config_cmd.add_argument("--project-root", required=True)
    runtime_config_cmd.set_defaults(func=cmd_runtime_config_show)

    batch_compile_cmd = sub.add_parser(
        "batch-compile",
        help="Run unity.compile.player_scripts through a non-interactive Unity batchmode lane when the target project is closed.",
    )
    batch_compile_cmd.add_argument("--project-root", required=True)
    batch_compile_cmd.add_argument("--target", required=True)
    batch_compile_cmd.add_argument("--name", default="")
    batch_compile_cmd.add_argument("--option-flag", action="append", default=[])
    batch_compile_cmd.add_argument("--extra-define", action="append", default=[])
    batch_compile_cmd.add_argument("--unity-app")
    batch_compile_cmd.add_argument("--batch-log-path")
    batch_compile_cmd.add_argument("--result-file")
    batch_compile_cmd.add_argument("--dry-run", action="store_true")
    batch_compile_cmd.set_defaults(func=cmd_batch_compile)

    batch_compile_matrix_cmd = sub.add_parser(
        "batch-compile-matrix",
        help="Run unity.compile.matrix through a non-interactive Unity batchmode lane from a JSON config file when the target project is closed.",
    )
    batch_compile_matrix_cmd.add_argument("--project-root", required=True)
    batch_compile_matrix_cmd.add_argument("--config-file", required=True)
    batch_compile_matrix_cmd.add_argument("--unity-app")
    batch_compile_matrix_cmd.add_argument("--batch-log-path")
    batch_compile_matrix_cmd.add_argument("--result-file")
    batch_compile_matrix_cmd.add_argument("--dry-run", action="store_true")
    batch_compile_matrix_cmd.set_defaults(func=cmd_batch_compile_matrix)

    batch_build_config_matrix_cmd = sub.add_parser(
        "batch-build-config-compile-matrix",
        help="Resolve build profiles from the project's build-config asset and run the Android/iOS compile matrix through a non-interactive Unity batchmode lane when the target project is closed.",
    )
    batch_build_config_matrix_cmd.add_argument("--project-root", required=True)
    batch_build_config_matrix_cmd.add_argument("--build-config-asset")
    batch_build_config_matrix_cmd.add_argument("--profile", action="append", default=[])
    batch_build_config_matrix_cmd.add_argument("--target", action="append", default=[])
    batch_build_config_matrix_cmd.add_argument("--stop-on-first-failure", action="store_true")
    batch_build_config_matrix_cmd.add_argument("--unity-app")
    batch_build_config_matrix_cmd.add_argument("--batch-log-path")
    batch_build_config_matrix_cmd.add_argument("--result-file")
    batch_build_config_matrix_cmd.set_defaults(func=cmd_batch_build_config_compile_matrix)

    batch_editmode_cmd = sub.add_parser(
        "batch-editmode-tests",
        help="Run unity.tests.run_editmode through a non-interactive Unity batchmode lane when the target project is closed.",
    )
    batch_editmode_cmd.add_argument("--project-root", required=True)
    batch_editmode_cmd.add_argument("--test-name", dest="test_names", action="append", default=[])
    batch_editmode_cmd.add_argument("--group-name", dest="group_names", action="append", default=[])
    batch_editmode_cmd.add_argument("--category-name", dest="category_names", action="append", default=[])
    batch_editmode_cmd.add_argument("--assembly-name", dest="assembly_names", action="append", default=[])
    batch_editmode_cmd.add_argument("--unity-app")
    batch_editmode_cmd.add_argument("--batch-log-path")
    batch_editmode_cmd.add_argument("--result-file")
    batch_editmode_cmd.add_argument("--dry-run", action="store_true")
    batch_editmode_cmd.set_defaults(func=cmd_batch_editmode_tests)

    regression_cmd = sub.add_parser(
        "batch-test-framework-version-regression",
        help="Run the Phase 0 com.unity.test-framework version sweep against the live MCP and batch EditMode validation lanes.",
    )
    regression_cmd.add_argument("--project-root", required=True)
    regression_cmd.add_argument("--version", action="append", default=[])
    regression_cmd.add_argument("--versions-file")
    regression_cmd.add_argument("--compile-target", default=TEST_FRAMEWORK_REGRESSION_COMPILE_TARGET)
    regression_cmd.add_argument("--focus-assembly-name", action="append", default=[])
    regression_cmd.add_argument("--focus-test-name", action="append", default=[])
    regression_cmd.add_argument("--broad-assembly-name", action="append", default=[])
    regression_cmd.add_argument(
        "--restore-original-version",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    regression_cmd.add_argument("--result-file")
    regression_cmd.set_defaults(func=cmd_batch_test_framework_version_regression)

    batch_build_cmd = sub.add_parser(
        "batch-build-player",
        help="Run a generic plain Unity batch build for simple projects using the public lightweight MCP package entrypoint.",
    )
    batch_build_cmd.add_argument("--project-root", required=True)
    batch_build_cmd.add_argument("--build-target", required=True)
    batch_build_cmd.add_argument("--output-path")
    batch_build_cmd.add_argument("--scene-path", action="append", default=[])
    batch_build_cmd.add_argument("--build-option", action="append", default=[])
    batch_build_cmd.add_argument("--unity-app")
    batch_build_cmd.add_argument("--batch-log-path")
    batch_build_cmd.add_argument("--result-file")
    batch_build_cmd.add_argument("--dry-run", action="store_true")
    batch_build_cmd.set_defaults(func=cmd_batch_build_player)

    maintenance_prune_cmd = sub.add_parser(
        "maintenance-prune",
        help="Prune stale request-journal, scenario-result, capture, and optional log artifacts under Library/XUUnityLightMcp.",
    )
    maintenance_prune_cmd.add_argument("--project-root", required=True)
    maintenance_prune_cmd.add_argument("--dry-run", action="store_true")
    maintenance_prune_cmd.add_argument("--request-journal-max-age-hours", type=int, default=72)
    maintenance_prune_cmd.add_argument("--request-journal-keep-latest", type=int, default=200)
    maintenance_prune_cmd.add_argument("--scenario-success-max-age-hours", type=int, default=168)
    maintenance_prune_cmd.add_argument("--scenario-failure-max-age-hours", type=int, default=336)
    maintenance_prune_cmd.add_argument("--scenario-running-max-age-hours", type=int, default=168)
    maintenance_prune_cmd.add_argument("--scenario-keep-latest-success", type=int, default=20)
    maintenance_prune_cmd.add_argument("--scenario-keep-latest-failure", type=int, default=50)
    maintenance_prune_cmd.add_argument("--scenario-keep-latest-running", type=int, default=20)
    maintenance_prune_cmd.add_argument("--captures-max-age-hours", type=int, default=168)
    maintenance_prune_cmd.add_argument("--captures-keep-latest", type=int, default=20)
    maintenance_prune_cmd.add_argument("--prune-logs", action="store_true")
    maintenance_prune_cmd.add_argument("--logs-max-age-hours", type=int, default=168)
    maintenance_prune_cmd.add_argument("--logs-keep-latest", type=int, default=10)
    maintenance_prune_cmd.set_defaults(func=cmd_maintenance_prune)

    return parser


def main():
    try:
        if len(sys.argv) == 1:
            raise SystemExit(serve_stdio())

        parser = build_parser()
        args = parser.parse_args()
        if not hasattr(args, "func"):
            parser.print_help()
            raise SystemExit(1)
        args.func(args)
    except ToolInvocationError as exc:
        payload = build_tool_error_payload(exc)
        emit_tool_error_summary(payload)
        print_json(payload)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
