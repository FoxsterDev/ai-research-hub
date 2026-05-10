#!/usr/bin/env python3
import argparse
from contextlib import nullcontext
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from server_build_config import build_compile_matrix_args_from_build_config
from server_batch_reporting import (
    attach_batch_summary_to_error,
    batch_summary_artifact_path,
    build_batch_execution_summary,
    build_batch_prepare_failure_summary,
    first_non_empty_line,
    write_batch_summary_artifact,
)
from server_bridge_payloads import (
    bridge_response_to_tool_result as bridge_response_to_tool_result_data,
    normalize_response_payload_from_lifecycle as normalize_response_payload_from_lifecycle_data,
    scenario_failure_tool_result as scenario_failure_tool_result_data,
)
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
    pid_is_alive,
    read_best_effort_bridge_state,
    read_request_journal_events,
    request_journal_dir,
    scenario_results_dir,
    summarize_state_for_error,
    try_read_bridge_state,
    try_read_live_editor_state,
    wait_for_editor_idle,
    wait_for_playmode_state,
)
from server_core import ToolInvocationError, read_json, write_json
from server_discovery import discover_project_context_state
from server_editor_host import (
    activate_unity_editor,
    bridge_state_is_ready,
    build_batch_validation_command,
    build_plain_batch_build_command,
    classify_editor_log,
    clear_stale_project_lock,
    default_batch_build_log_path,
    default_batch_operation_log_path,
    default_batch_operation_result_path,
    default_batch_build_result_path,
    detect_unity_app_path_for_project,
    find_running_unity_editors_for_project,
    list_live_project_editor_pids,
    open_unity_editor,
    read_recent_editor_log,
    resolve_batch_build_output_path,
    resolve_editor_log_path,
    restore_host_opened_editor_state,
    terminate_editor_pid,
    try_read_host_editor_session_state,
    update_host_editor_session_pid,
    wait_for_ready,
)
from server_health import (
    FRESH_HEARTBEAT_MAX_AGE_SECONDS,
    build_editor_log_diagnosis,
    classify_project_health,
)
from server_host_platform import current_host_platform_adapter
from server_mcp_protocol import (
    JsonRpcError,
    build_initialize_result as build_initialize_result_base,
    handle_json_rpc_message as handle_json_rpc_message_base,
    list_tools_result as list_tools_result_base,
    serve_stdio as serve_stdio_base,
)
from server_mcp_tools import (
    call_tool as call_tool_base,
    call_unity_compile_build_config_matrix_tool as call_unity_compile_build_config_matrix_tool_base,
    call_unity_maintenance_prune_tool as call_unity_maintenance_prune_tool_base,
    call_unity_request_final_status_tool as call_unity_request_final_status_tool_base,
    call_unity_scenario_result_summary_tool as call_unity_scenario_result_summary_tool_base,
    call_unity_scenario_run_and_wait_tool as call_unity_scenario_run_and_wait_tool_base,
    call_unity_status_summary_tool as call_unity_status_summary_tool_base,
)
from server_operation_evidence import (
    attach_operation_evidence_to_payload,
    attach_persisted_scenario_result_evidence,
    parse_utc_timestamp,
)
from server_project_context import (
    ensure_project_root as ensure_project_root_base,
    find_latest_request_event,
    find_repo_local_package_source,
    inspect_package_dependency_alignment,
)
from server_project_reporting import (
    apply_discovery_to_final_status_summary_data,
    apply_discovery_to_scenario_payload_data,
    build_discovery_scenario_result_summary_for_error_data,
    build_discovery_status_summary_for_error_data,
    build_project_discovery_report_data,
    build_registry_context_report_data,
    build_request_final_status_from_context_data,
    build_scenario_result_summary_from_context_data,
    enrich_error_details_with_discovery_data,
)
from server_registry import BridgeRegistry, ProjectContext
from server_scenario_polling import (
    is_terminal_scenario_status as is_terminal_scenario_status_data,
    wait_for_scenario_result_data,
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
from server_scenario_results import (
    latest_persisted_scenario_result_summary,
    list_persisted_scenario_result_summaries,
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
    "version": "0.3.10",
}
LIGHTWEIGHT_PACKAGE_NAME = "com.xuunity.light-mcp"


def _build_project_health_details(
    *,
    project_root: Path,
    bridge_state: dict[str, Any],
    host_editor_session_state: dict[str, Any],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    startup_policy = str(
        bridge_state.get("startup_policy")
        or host_editor_session_state.get("startup_policy")
        or "fail_fast_on_interactive_compile_block"
    )
    heartbeat_age = heartbeat_age_seconds(bridge_state) if bridge_state else None
    needs_log_diagnosis = bool(
        not discovery.get("bridge_state_live")
        or (
            heartbeat_age is not None
            and heartbeat_age >= FRESH_HEARTBEAT_MAX_AGE_SECONDS
        )
    )
    editor_log_diagnosis = (
        build_editor_log_diagnosis(
            default_editor_log_path(project_root),
            startup_policy=startup_policy,
            classify_editor_log=classify_editor_log,
        )
        if needs_log_diagnosis
        else {}
    )
    return classify_project_health(
        bridge_state=bridge_state,
        discovery=discovery,
        editor_log_diagnosis=editor_log_diagnosis,
        heartbeat_age_seconds=heartbeat_age_seconds,
        derive_busy_reason=derive_busy_reason,
    )


def _refresh_project_context_state(project_root: Path) -> dict[str, Any]:
    platform_adapter = current_host_platform_adapter()
    discovery = discover_project_context_state(
        project_root,
        try_read_bridge_state=try_read_bridge_state,
        try_read_host_editor_session_state=try_read_host_editor_session_state,
        find_running_unity_editors_for_project=find_running_unity_editors_for_project,
        pid_is_alive=platform_adapter.pid_is_alive,
        bridge_enabled=bridge_enabled,
        build_project_health=_build_project_health_details,
    )
    bridge_state = dict(discovery.get("last_bridge_state") or {})
    host_editor_session_state = dict(discovery.get("last_host_editor_session_state") or {})
    bridge_generation, bridge_session_id = bridge_identity_from_state(bridge_state)

    return {
        "last_bridge_state": bridge_state,
        "last_host_editor_session_state": host_editor_session_state,
        "active_transport": str(discovery.get("active_transport") or ""),
        "transport_metadata": dict(discovery.get("transport_metadata") or {}),
        "last_seen_pid": int(discovery.get("last_seen_pid") or 0),
        "last_seen_generation": bridge_generation,
        "last_seen_session_id": bridge_session_id,
        "last_refresh_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "last_refresh_unix": time.time(),
        "health_classification": str(
            discovery.get("host_health_classification")
            or bridge_state.get("health_status")
            or discovery.get("discovery_classification")
            or ""
        ),
        "discovery_classification": str(discovery.get("discovery_classification") or ""),
        "discovery_details": discovery,
    }


_BRIDGE_REGISTRY = BridgeRegistry(
    ensure_project_root=ensure_project_root_base,
    refresh_context_state=_refresh_project_context_state,
)
MUTATING_BRIDGE_OPERATIONS = frozenset(
    {
        "unity.project.refresh",
        "unity.compile.player_scripts",
        "unity.compile.matrix",
        "unity.tests.run_editmode",
        "unity.tests.run_playmode",
        "unity.playmode.set",
        "unity.build_target.switch",
        "unity.editor.quit",
    }
)
TProjectOperationResult = TypeVar("TProjectOperationResult")


def get_project_context(project_root: str) -> ProjectContext:
    return _BRIDGE_REGISTRY.get_or_discover(project_root)


def refresh_project_context(project_root: str | Path) -> ProjectContext:
    return _BRIDGE_REGISTRY.refresh_context(str(project_root))


def list_active_project_contexts() -> list[ProjectContext]:
    return _BRIDGE_REGISTRY.list_active_contexts()


def forget_project_context(project_root: str) -> None:
    _BRIDGE_REGISTRY.forget(project_root)


def prune_stale_project_contexts(
    *,
    offline_context_max_idle_seconds: float | None = None,
    general_context_max_idle_seconds: float | None = None,
) -> list[dict[str, Any]]:
    return _BRIDGE_REGISTRY.prune_stale_contexts(
        offline_context_max_idle_seconds=offline_context_max_idle_seconds,
        general_context_max_idle_seconds=general_context_max_idle_seconds,
    )


def build_registry_context_report() -> dict[str, Any]:
    return build_registry_context_report_data(
        list_active_project_contexts(),
        now=time.time(),
    )


def ensure_project_root(project_root: str) -> Path:
    return get_project_context(project_root).project_root


def bridge_operation_requires_request_lock(operation: str) -> bool:
    return str(operation or "").strip() in MUTATING_BRIDGE_OPERATIONS


def run_in_project_request_lock(
    context: ProjectContext,
    operation: str,
    callback: Callable[[], TProjectOperationResult],
) -> TProjectOperationResult:
    lock_scope = context.request_lock if bridge_operation_requires_request_lock(operation) else nullcontext()
    with lock_scope:
        return callback()


def current_project_context_bridge_state(project_root: Path) -> dict[str, Any]:
    context = refresh_project_context(project_root)
    return read_best_effort_bridge_state(project_root) or dict(context.last_bridge_state or {})


def current_project_context_host_session_state(project_root: Path) -> dict[str, Any]:
    context = refresh_project_context(project_root)
    return dict(context.last_host_editor_session_state or {})


def current_project_context_discovery_details(project_root: Path) -> dict[str, Any]:
    context = refresh_project_context(project_root)
    details = context.discovery_details if isinstance(getattr(context, "discovery_details", None), dict) else {}
    return dict(details or {})


def build_project_discovery_report(project_root: Path) -> dict[str, Any]:
    context = refresh_project_context(project_root)
    discovery = current_project_context_discovery_details(project_root)
    return build_project_discovery_report_data(
        project_root,
        context=context,
        discovery=discovery,
    )


RECOVERY_RECONCILIATION_ACTIONS = frozenset(
    {
        "ensure_ready_or_recover_bridge",
        "open_editor_or_ensure_ready",
        "start_or_recover_editor",
        "clear_stale_host_session_and_retry",
    }
)


def build_status_summary_from_context(
    project_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return build_status_summary(
        project_root,
        payload if isinstance(payload, dict) else {},
        read_best_effort_bridge_state=current_project_context_bridge_state,
        try_read_bridge_state=lambda path: dict(refresh_project_context(path).last_bridge_state or {}),
        pid_is_alive=pid_is_alive,
        heartbeat_age_seconds=heartbeat_age_seconds,
        derive_busy_reason=derive_busy_reason,
        summarize_state_for_error=summarize_state_for_error,
        discovery_details=current_project_context_discovery_details(project_root),
    )


DISCOVERY_STATUS_FALLBACK_ERROR_CODES = frozenset(
    {
        "editor_not_running",
        "transport_not_ready",
        "bridge_disabled",
    }
)

SCENARIO_RECOVERY_ERROR_CODES = frozenset(
    {
        "editor_not_running",
        "transport_not_ready",
        "transport_connect_failed",
        "transport_response_missing",
        "request_lifecycle_reset",
        "response_missing_after_lifecycle_reset",
    }
)


DISCOVERY_NEXT_ACTION_COMMANDS = {
    "enable_bridge_and_retry": "init_xuunity_light_unity_mcp.sh --project-root {project_root} --enable-project",
    "open_editor_or_ensure_ready": "xuunity_light_unity_mcp.sh ensure-ready --project-root {project_root} --open-editor",
    "ensure_ready_or_recover_bridge": "xuunity_light_unity_mcp.sh ensure-ready --project-root {project_root} --open-editor",
    "start_or_recover_editor": "xuunity_light_unity_mcp.sh ensure-ready --project-root {project_root} --open-editor",
    "clear_stale_host_session_and_retry": "xuunity_light_unity_mcp.sh restore-editor-state --project-root {project_root} --timeout-ms 15000",
    "refresh_host_session_if_needed": "xuunity_light_unity_mcp.sh request-status-summary --project-root {project_root} --timeout-ms 5000",
    "inspect_editor_log": "xuunity_light_unity_mcp.sh project-discovery-report --project-root {project_root}",
    "inspect_editor_log_and_observe": "xuunity_light_unity_mcp.sh project-discovery-report --project-root {project_root}",
    "inspect_editor_log_and_consider_graceful_restart": "xuunity_light_unity_mcp.sh ensure-ready --project-root {project_root} --open-editor",
}


def recommended_recovery_command_for_project(project_root: Path, next_action: str) -> str:
    template = DISCOVERY_NEXT_ACTION_COMMANDS.get(str(next_action or "").strip())
    if not template:
        return ""
    return template.format(project_root=str(project_root))


def enrich_error_details_with_discovery(project_root: Path, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return enrich_error_details_with_discovery_data(
        project_root,
        details=details,
        discovery=current_project_context_discovery_details(project_root),
        recommended_recovery_command_for_project=recommended_recovery_command_for_project,
    )


def enrich_tool_invocation_error_with_discovery(project_root: Path, exc: ToolInvocationError) -> ToolInvocationError:
    return ToolInvocationError(
        exc.code,
        exc.message,
        enrich_error_details_with_discovery(project_root, exc.details),
    )


def execute_host_health_recovery_policy(
    project_root: Path,
    *,
    timeout_ms: int,
    startup_policy: str,
    allow_open_editor: bool,
    background_open: bool = False,
) -> dict[str, Any]:
    discovery = current_project_context_discovery_details(project_root)
    termination_policy = str(discovery.get("host_health_termination_policy") or "observe_only")
    health_classification = str(discovery.get("host_health_classification") or "")
    result: dict[str, Any] = {
        "host_health_classification": health_classification,
        "termination_policy": termination_policy,
        "action": "none",
    }

    if health_classification not in {"anr", "anr_suspected"}:
        return result

    if termination_policy == "observe_only":
        result["action"] = "observe_only"
        return result

    candidate_pid = 0
    for value in (
        int(discovery.get("bridge_pid") or 0),
        int(discovery.get("host_session_pid") or 0),
    ):
        if value > 0:
            candidate_pid = value
            break
    if candidate_pid <= 0:
        detected_pids = list(discovery.get("detected_editor_pids") or [])
        candidate_pid = int(detected_pids[0] or 0) if detected_pids else 0

    if candidate_pid <= 0:
        result["action"] = "no_live_pid_for_termination"
        return result

    result["target_editor_pid"] = candidate_pid
    if not allow_open_editor:
        result["action"] = "termination_deferred_no_open"
        return result

    result["terminated"] = terminate_editor_pid(candidate_pid, min(timeout_ms, 15000))
    if not bool(result.get("terminated")):
        result["action"] = "termination_failed"
        return result

    result["action"] = "terminated_editor"
    refresh_project_context(project_root)

    if not allow_open_editor:
        return result

    unity_app = detect_unity_app_path_for_project(project_root, None)
    log_path = default_editor_log_path(project_root)
    launch = open_unity_editor(project_root, log_path, unity_app, background_open)
    state = wait_for_ready(
        project_root=project_root,
        timeout_ms=timeout_ms,
        heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
        startup_policy=startup_policy,
        editor_log_path=log_path,
    )
    result["launch"] = launch
    result["bridge_state"] = state
    if not bool((launch or {}).get("reused_existing_editor")):
        update_host_editor_session_pid(project_root, int(state.get("editor_pid") or 0))
    refresh_project_context(project_root)
    result["action"] = "terminated_and_reopened"
    return result


def recover_project_bridge_for_reconciliation(
    project_root: Path,
    *,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    startup_policy: str,
    allow_open_editor: bool,
    background_open: bool = False,
) -> dict[str, Any]:
    current_state = current_project_context_bridge_state(project_root)
    discovery = current_project_context_discovery_details(project_root)
    next_action = str(discovery.get("reconciliation_recommended_next_action") or "")

    recovery: dict[str, Any] = {
        "reconciliation_case": str(discovery.get("reconciliation_case") or ""),
        "reconciliation_status": str(discovery.get("reconciliation_status") or ""),
        "reconciliation_recommended_next_action": next_action,
        "allow_open_editor": allow_open_editor,
        "action": "none",
    }

    if bridge_state_is_ready(current_state, heartbeat_max_age_seconds):
        recovery["action"] = "already_ready"
        return recovery

    host_health_recovery = execute_host_health_recovery_policy(
        project_root,
        timeout_ms=timeout_ms,
        startup_policy=startup_policy,
        allow_open_editor=allow_open_editor,
        background_open=background_open,
    )
    recovery["host_health_recovery"] = host_health_recovery
    if str(host_health_recovery.get("action") or "") in {
        "terminated_editor",
        "terminated_and_reopened",
        "termination_failed",
        "no_live_pid_for_termination",
        "termination_deferred_no_open",
    }:
        recovery["action"] = str(host_health_recovery.get("action") or "none")
        return recovery

    if next_action == "enable_bridge_and_retry":
        raise enrich_tool_invocation_error_with_discovery(
            project_root,
            ToolInvocationError(
                "bridge_disabled",
                (
                    "Unity bridge is disabled for this project. "
                    "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                    "and reopen Unity."
                ),
            ),
        )

    if next_action == "refresh_host_session_if_needed":
        refresh_project_context(project_root)
        recovery["action"] = "refreshed_context"
        return recovery

    if next_action not in RECOVERY_RECONCILIATION_ACTIONS:
        return recovery

    detected_editor_count = int(discovery.get("detected_editor_count") or 0)
    log_path = default_editor_log_path(project_root)
    if detected_editor_count > 0:
        recovery["activation"] = activate_unity_editor(project_root)
        recovery["action"] = "activated_existing_editor"
    elif allow_open_editor:
        unity_app = detect_unity_app_path_for_project(project_root, None)
        launch = open_unity_editor(project_root, log_path, unity_app, background_open)
        recovery["launch"] = launch
        recovery["action"] = "opened_editor"
    else:
        recovery["action"] = "recovery_deferred_no_open"
        return recovery

    state = wait_for_ready(
        project_root=project_root,
        timeout_ms=timeout_ms,
        heartbeat_max_age_seconds=heartbeat_max_age_seconds,
        startup_policy=startup_policy,
        editor_log_path=log_path,
    )
    recovery["bridge_state"] = state
    launch_payload = recovery.get("launch")
    if isinstance(launch_payload, dict) and not bool(launch_payload.get("reused_existing_editor")):
        update_host_editor_session_pid(project_root, int(state.get("editor_pid") or 0))
    refresh_project_context(project_root)
    return recovery


def build_discovery_status_summary_for_error(
    project_root: Path,
    exc: ToolInvocationError | None = None,
) -> dict[str, Any]:
    return build_discovery_status_summary_for_error_data(
        project_root,
        exc=exc,
        discovery=current_project_context_discovery_details(project_root),
        build_status_summary_from_context=build_status_summary_from_context,
        enrich_error_details_with_discovery=enrich_error_details_with_discovery,
    )


def apply_discovery_to_final_status_summary(
    summary: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    return apply_discovery_to_final_status_summary_data(
        summary,
        discovery=current_project_context_discovery_details(project_root),
    )


def apply_discovery_to_scenario_payload(
    payload: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    return apply_discovery_to_scenario_payload_data(
        payload,
        project_root=project_root,
        discovery=current_project_context_discovery_details(project_root),
    )


def build_scenario_result_summary_from_context(
    project_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return build_scenario_result_summary_from_context_data(
        project_root,
        payload,
        discovery=current_project_context_discovery_details(project_root),
        build_scenario_result_summary=build_scenario_result_summary,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
    )


def build_discovery_scenario_result_summary_for_error(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    exc: ToolInvocationError,
) -> dict[str, Any]:
    return build_discovery_scenario_result_summary_for_error_data(
        project_root,
        run_id,
        scenario_name,
        exc,
        build_scenario_result_summary_from_context=build_scenario_result_summary_from_context,
        enrich_error_details_with_discovery=enrich_error_details_with_discovery,
    )


def build_request_final_status_from_context(
    project_root: Path,
    request_id: str,
    operation: str = "",
    poll_timeout_ms: int = 0,
) -> dict[str, Any]:
    return build_request_final_status_from_context_data(
        project_root,
        request_id,
        operation=operation,
        poll_timeout_ms=poll_timeout_ms,
        build_request_final_status=build_request_final_status,
        current_project_context_bridge_state=current_project_context_bridge_state,
        discovery=current_project_context_discovery_details(project_root),
    )

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
    message = first_non_empty_line(str(error.get("message") or ""), limit=200, truncate_text=truncate_text)
    request_id = str(payload.get("request_id") or "")
    request_submitted = payload.get("request_submitted")
    request_ownership_acquired = payload.get("request_ownership_acquired")
    recommended_next_action = str(payload.get("recommended_next_action") or "")
    recommended_recovery_command = str(payload.get("recommended_recovery_command") or "")
    transport_outcome = str(payload.get("transport_outcome") or "")
    operation_outcome = str(payload.get("operation_outcome") or "")
    closeout_classification = str(payload.get("closeout_classification") or "")

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
    if closeout_classification:
        parts.append(f"closeout_classification={closeout_classification}")
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
        "closeout_classification",
        "closeout_verified",
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
        "live_project_editor_pids",
        "batch_summary_file",
        "batch_failure_summary",
    ):
        if key in details:
            payload[key] = details[key]
    return payload

def request_editor_quit(project_root: Path, timeout_ms: int) -> dict[str, Any]:
    return invoke_bridge(project_root, "unity.editor.quit", {}, timeout_ms)

def wait_for_scenario_result(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    timeout_ms: int,
    poll_interval_ms: int,
) -> dict[str, Any]:
    return wait_for_scenario_result_data(
        project_root,
        run_id,
        scenario_name,
        timeout_ms,
        poll_interval_ms,
        scenario_recovery_error_codes=SCENARIO_RECOVERY_ERROR_CODES,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
        default_heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
        try_read_live_editor_state=try_read_live_editor_state,
        activate_unity_editor=activate_unity_editor,
        invoke_bridge=invoke_bridge,
        recover_project_bridge_for_reconciliation=recover_project_bridge_for_reconciliation,
        current_project_context_bridge_state=current_project_context_bridge_state,
        enrich_tool_invocation_error_with_discovery=enrich_tool_invocation_error_with_discovery,
        bridge_response_to_tool_result=bridge_response_to_tool_result,
        normalize_scenario_payload=normalize_scenario_payload,
        apply_discovery_to_scenario_payload=apply_discovery_to_scenario_payload,
        tool_invocation_error_type=ToolInvocationError,
    )

def is_terminal_scenario_status(status: Any) -> bool:
    return is_terminal_scenario_status_data(status, SCENARIO_TERMINAL_STATUSES)


def normalize_response_payload_from_lifecycle(response: dict[str, Any], lifecycle: dict[str, Any]) -> dict[str, Any]:
    return normalize_response_payload_from_lifecycle_data(
        response,
        lifecycle,
        normalize_scenario_payload=normalize_scenario_payload,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
    )


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
    context = get_project_context(project_root_value)
    project_root = context.project_root

    def perform_invoke() -> dict[str, Any]:
        policy = resolve_operation_lifecycle_policy(project_root, operation)
        max_attempts = 2 if (
            bool(policy.get("retry_on_lifecycle_reset"))
            or bool(policy.get("retry_on_transport_response_missing"))
            or bool(policy.get("retry_on_transport_connect_failed"))
        ) else 1

        for attempt_index in range(max_attempts):
            pre_request_state = try_read_live_editor_state(project_root) or current_project_context_bridge_state(project_root)
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
                    lifecycle["activation"] = recover_project_bridge_for_reconciliation(
                        project_root,
                        timeout_ms=min(timeout_ms, 180000),
                        heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        startup_policy=str(
                            pre_request_state.get("startup_policy")
                            or "fail_fast_on_interactive_compile_block"
                        ),
                        allow_open_editor=True,
                    )

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
                    payload_json = response.get("payload_json")
                    if isinstance(payload_json, str) and payload_json:
                        try:
                            parsed_payload = json.loads(payload_json)
                        except json.JSONDecodeError:
                            parsed_payload = None
                        if isinstance(parsed_payload, dict):
                            journal_events = read_request_journal_events(project_root, request_id)
                            response["payload_json"] = json.dumps(
                                attach_operation_evidence_to_payload(
                                    parsed_payload,
                                    project_root=project_root,
                                    operation=operation,
                                    request_id=request_id,
                                    request_submitted_at_utc=next(
                                        (
                                            str(event.get("event_at_utc") or "")
                                            for event in reversed(journal_events)
                                            if str(event.get("event_type") or "") == "request_submitted"
                                        ),
                                        "",
                                    ),
                                    request_started_at_utc=next(
                                        (
                                            str(event.get("started_at_utc") or event.get("event_at_utc") or "")
                                            for event in journal_events
                                            if str(event.get("event_type") or "") == "request_started"
                                        ),
                                        "",
                                    ),
                                    request_completed_at_utc=next(
                                        (
                                            str(event.get("completed_at_utc") or event.get("event_at_utc") or "")
                                            for event in reversed(journal_events)
                                            if str(event.get("event_type") or "") == "request_completed"
                                        ),
                                        "",
                                    ),
                                    response_completed_at_utc=str(response.get("completed_at_utc") or ""),
                                    editor_log_path=default_editor_log_path(project_root),
                                    journal_event_paths=[str(event.get("_path") or "") for event in journal_events],
                                    lifecycle=lifecycle,
                                    host_started_unix=request_started_at,
                                    host_completed_unix=time.time(),
                                ),
                                ensure_ascii=True,
                                separators=(",", ":"),
                            )
                    response["_xuunity_lifecycle"] = lifecycle

                refresh_project_context(project_root)
                return response
            except ToolInvocationError as exc:
                if exc.code == "request_lifecycle_reset" and attempt_index + 1 < max_attempts:
                    lifecycle["lifecycle_reset_retry"] = exc.details
                    lifecycle["lifecycle_reset_recovery"] = recover_project_bridge_for_reconciliation(
                        project_root,
                        timeout_ms=min(timeout_ms, 10000),
                        heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        startup_policy=str(
                            (current_project_context_bridge_state(project_root) or pre_request_state or {}).get("startup_policy")
                            or "fail_fast_on_interactive_compile_block"
                        ),
                        allow_open_editor=False,
                    )
                    continue
                if (
                    exc.code == "transport_response_missing"
                    and bool(policy.get("retry_on_transport_response_missing"))
                    and attempt_index + 1 < max_attempts
                    and not bool((exc.details or {}).get("request_processed"))
                ):
                    lifecycle["transport_response_missing_retry"] = exc.details
                    lifecycle["transport_response_missing_recovery"] = recover_project_bridge_for_reconciliation(
                        project_root,
                        timeout_ms=min(timeout_ms, 10000),
                        heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        startup_policy=str(
                            (current_project_context_bridge_state(project_root) or pre_request_state or {}).get("startup_policy")
                            or "fail_fast_on_interactive_compile_block"
                        ),
                        allow_open_editor=False,
                    )
                    continue
                if (
                    exc.code == "transport_connect_failed"
                    and bool(policy.get("retry_on_transport_connect_failed"))
                    and attempt_index + 1 < max_attempts
                ):
                    lifecycle["transport_connect_failed_retry"] = exc.details
                    retry_state = current_project_context_bridge_state(project_root) or pre_request_state or {}
                    lifecycle["transport_connect_failed_recovery"] = recover_project_bridge_for_reconciliation(
                        project_root,
                        timeout_ms=min(timeout_ms, 10000),
                        heartbeat_max_age_seconds=DEFAULT_HEARTBEAT_MAX_AGE_SECONDS,
                        startup_policy=str(
                            retry_state.get("startup_policy")
                            or "fail_fast_on_interactive_compile_block"
                        ),
                        allow_open_editor=False,
                    )
                    continue
                raise enrich_tool_invocation_error_with_discovery(project_root, exc)

        raise ToolInvocationError("unreachable", f"Unexpected lifecycle retry state for {operation}.")

    return run_in_project_request_lock(context, operation, perform_invoke)

def bridge_response_to_tool_result(response: dict[str, Any]) -> dict[str, Any]:
    return bridge_response_to_tool_result_data(
        response,
        normalize_scenario_payload=normalize_scenario_payload,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
    )


def scenario_failure_tool_result(result_payload: dict[str, Any]) -> dict[str, Any]:
    return scenario_failure_tool_result_data(result_payload)


def call_unity_compile_build_config_matrix_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return call_unity_compile_build_config_matrix_tool_base(
        arguments,
        tool_invocation_error_type=ToolInvocationError,
        ensure_project_root=ensure_project_root,
        resolve_operation_timeout_ms=resolve_operation_timeout_ms,
        build_compile_matrix_args_from_build_config=build_compile_matrix_args_from_build_config,
        invoke_bridge=invoke_bridge,
        build_tool_error_payload=build_tool_error_payload,
        bridge_response_to_tool_result=bridge_response_to_tool_result,
    )


def call_unity_scenario_run_and_wait_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return call_unity_scenario_run_and_wait_tool_base(
        arguments,
        tool_invocation_error_type=ToolInvocationError,
        ensure_project_root=ensure_project_root,
        resolve_operation_timeout_ms=resolve_operation_timeout_ms,
        invoke_bridge=invoke_bridge,
        bridge_response_to_tool_result=bridge_response_to_tool_result,
        wait_for_scenario_result=wait_for_scenario_result,
        build_tool_error_payload=build_tool_error_payload,
        scenario_failure_tool_result=scenario_failure_tool_result,
    )


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
        if exc.code in DISCOVERY_STATUS_FALLBACK_ERROR_CODES:
            summary = build_discovery_status_summary_for_error(project_root, exc)
            return {
                "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=True)}],
                "structuredContent": summary,
                "isError": False,
            }
        return {
            "content": [{"type": "text", "text": json.dumps(build_tool_error_payload(exc), ensure_ascii=True)}],
            "structuredContent": build_tool_error_payload(exc),
            "isError": True,
        }

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        return tool_result

    payload = tool_result.get("structuredContent") or {}
    summary = build_status_summary_from_context(project_root, payload if isinstance(payload, dict) else {})
    return {
        "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=True)}],
        "structuredContent": summary,
        "isError": False,
    }


def call_unity_request_final_status_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return call_unity_request_final_status_tool_base(
        arguments,
        ensure_project_root=ensure_project_root,
        build_request_final_status_summary=build_request_final_status_from_context,
    )


def call_unity_scenario_result_summary_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    timeout_ms = arguments.get("timeoutMs", 5000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    project_root = ensure_project_root(project_root_value)
    bridge_args: dict[str, Any] = {}
    run_id = arguments.get("runId")
    if isinstance(run_id, str) and run_id.strip():
        bridge_args["runId"] = run_id.strip()
    scenario_name = arguments.get("scenarioName")
    if isinstance(scenario_name, str) and scenario_name.strip():
        bridge_args["scenarioName"] = scenario_name.strip()

    try:
        response = invoke_bridge(str(project_root), "unity.scenario.result", bridge_args, timeout_ms)
    except ToolInvocationError as exc:
        if exc.code in DISCOVERY_STATUS_FALLBACK_ERROR_CODES.union(SCENARIO_RECOVERY_ERROR_CODES):
            summary = build_discovery_scenario_result_summary_for_error(
                project_root,
                bridge_args.get("runId", ""),
                bridge_args.get("scenarioName", ""),
                exc,
            )
            return {
                "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=True)}],
                "structuredContent": summary,
                "isError": False,
            }
        return {
            "content": [{"type": "text", "text": json.dumps(build_tool_error_payload(exc), ensure_ascii=True)}],
            "structuredContent": build_tool_error_payload(exc),
            "isError": True,
        }

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        return tool_result

    payload = tool_result.get("structuredContent") or {}
    summary = build_scenario_result_summary_from_context(project_root, payload if isinstance(payload, dict) else {})
    return {
        "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=True)}],
        "structuredContent": summary,
        "isError": False,
    }


def call_unity_scenario_results_list_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    scenario_name = arguments.get("scenarioName")
    if scenario_name is not None and not isinstance(scenario_name, str):
        raise JsonRpcError(-32602, "scenarioName must be a string when provided.")

    limit = arguments.get("limit", 20)
    if not isinstance(limit, int):
        raise JsonRpcError(-32602, "limit must be an integer.")

    project_root = ensure_project_root(project_root_value)
    result = list_persisted_scenario_result_summaries(
        project_root,
        scenario_results_dir=scenario_results_dir,
        read_json=read_json,
        parse_utc_timestamp=parse_utc_timestamp,
        attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
        build_scenario_result_summary=build_scenario_result_summary,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
        scenario_name=scenario_name.strip() if isinstance(scenario_name, str) else "",
        limit=limit,
    )
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=True)}],
        "structuredContent": result,
        "isError": False,
    }


def call_unity_scenario_result_latest_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    scenario_name = arguments.get("scenarioName")
    if scenario_name is not None and not isinstance(scenario_name, str):
        raise JsonRpcError(-32602, "scenarioName must be a string when provided.")

    project_root = ensure_project_root(project_root_value)
    result = latest_persisted_scenario_result_summary(
        project_root,
        scenario_results_dir=scenario_results_dir,
        read_json=read_json,
        parse_utc_timestamp=parse_utc_timestamp,
        attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
        build_scenario_result_summary=build_scenario_result_summary,
        scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
        scenario_name=scenario_name.strip() if isinstance(scenario_name, str) else "",
    )
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=True)}],
        "structuredContent": result,
        "isError": False,
    }


def call_unity_maintenance_prune_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return call_unity_maintenance_prune_tool_base(
        arguments,
        ensure_project_root=ensure_project_root,
        prune_project_artifacts=prune_project_artifacts,
        bridge_root=bridge_root,
        request_journal_dir=request_journal_dir,
        scenario_results_dir=scenario_results_dir,
        active_scenario_run_path=active_scenario_run_path,
        captures_dir=captures_dir,
        logs_dir=logs_dir,
        default_editor_log_path=default_editor_log_path,
        read_json=read_json,
    )


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    return call_tool_base(
        name,
        arguments,
        tools=TOOLS,
        special_tool_handlers={
            "unity_status_summary": call_unity_status_summary_tool,
            "unity_request_final_status": call_unity_request_final_status_tool,
            "unity_scenario_result_summary": call_unity_scenario_result_summary_tool,
            "unity_scenario_results_list": call_unity_scenario_results_list_tool,
            "unity_scenario_result_latest": call_unity_scenario_result_latest_tool,
            "unity_maintenance_prune": call_unity_maintenance_prune_tool,
            "unity_compile_build_config_matrix": call_unity_compile_build_config_matrix_tool,
            "unity_scenario_run_and_wait": call_unity_scenario_run_and_wait_tool,
        },
        tool_invocation_error_type=ToolInvocationError,
        ensure_project_root=ensure_project_root,
        resolve_operation_timeout_ms=resolve_operation_timeout_ms,
        invoke_bridge=invoke_bridge,
        build_tool_error_payload=build_tool_error_payload,
        bridge_response_to_tool_result=bridge_response_to_tool_result,
    )


def build_initialize_result(requested_version: str | None) -> dict[str, Any]:
    return build_initialize_result_base(
        requested_version,
        protocol_version=PROTOCOL_VERSION,
        server_info=SERVER_INFO,
    )


def list_tools_result() -> dict[str, Any]:
    return list_tools_result_base(TOOLS)


def handle_json_rpc_message(message: dict[str, Any], session: dict[str, Any]) -> dict[str, Any] | None:
    return handle_json_rpc_message_base(
        message,
        session,
        protocol_version=PROTOCOL_VERSION,
        server_info=SERVER_INFO,
        tools=TOOLS,
        call_tool=call_tool,
    )


def serve_stdio() -> int:
    return serve_stdio_base(
        protocol_version=PROTOCOL_VERSION,
        handle_message=handle_json_rpc_message,
    )


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
    try:
        response = invoke_bridge(str(project_root), "unity.status", {}, args.timeout_ms)
    except ToolInvocationError as exc:
        if exc.code in DISCOVERY_STATUS_FALLBACK_ERROR_CODES:
            print_json(build_discovery_status_summary_for_error(project_root, exc))
            return
        raise

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        print_json(tool_result.get("structuredContent") or {})
        raise SystemExit(1)
    payload = tool_result.get("structuredContent") or {}
    print_json(build_status_summary_from_context(project_root, payload if isinstance(payload, dict) else {}))


def cmd_request_latest_status(args):
    project_root = ensure_project_root(args.project_root)
    operations = [str(operation).strip() for operation in list(args.operation or []) if str(operation).strip()]
    current_state = current_project_context_bridge_state(project_root)
    latest_event = find_latest_request_event(project_root, operations)

    if latest_event is None:
        stabilization = build_bridge_stabilization_summary(current_state)
        print_json(apply_discovery_to_final_status_summary({
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
        }, project_root))
        return

    request_id = str(latest_event.get("request_id") or "").strip()
    operation = str(latest_event.get("operation") or "").strip()
    summary = build_request_final_status_from_context(project_root, request_id, operation, args.timeout_ms)
    summary["lookup_mode"] = "latest_request_by_operation"
    summary["lookup_found"] = True
    summary["matched_operations"] = operations
    summary["lookup_event_type"] = str(latest_event.get("event_type") or "")
    summary["lookup_event_at_utc"] = str(latest_event.get("event_at_utc") or "")
    summary["lookup_event_path"] = str(latest_event.get("_path") or "")
    print_json(summary)


def cmd_request_final_status(args):
    project_root = ensure_project_root(args.project_root)
    summary = build_request_final_status_from_context(project_root, args.request_id, args.operation or "", args.timeout_ms)
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
            truncate_text=truncate_text,
        )
        write_batch_summary_artifact(summary_path, summary)
        raise attach_batch_summary_to_error(
            exc,
            summary_path=summary_path,
            summary=summary,
            tool_invocation_error_type=ToolInvocationError,
        )

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
        truncate_text=truncate_text,
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
    project_root = ensure_project_root(args.project_root)
    bridge_args: dict[str, Any] = {}
    if args.run_id:
        bridge_args["runId"] = args.run_id
    if args.scenario_name:
        bridge_args["scenarioName"] = args.scenario_name

    try:
        response = invoke_bridge(
            str(project_root),
            "unity.scenario.result",
            bridge_args,
            args.timeout_ms,
        )
    except ToolInvocationError as exc:
        if exc.code in DISCOVERY_STATUS_FALLBACK_ERROR_CODES.union(SCENARIO_RECOVERY_ERROR_CODES):
            print_json(
                build_discovery_scenario_result_summary_for_error(
                    project_root,
                    bridge_args.get("runId", ""),
                    bridge_args.get("scenarioName", ""),
                    exc,
                )
            )
            return
        raise

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        print_json(tool_result.get("structuredContent") or {})
        raise SystemExit(1)
    payload = tool_result.get("structuredContent") or {}
    print_json(build_scenario_result_summary_from_context(project_root, payload if isinstance(payload, dict) else {}))


def cmd_request_scenario_results_list(args):
    project_root = ensure_project_root(args.project_root)
    print_json(
        list_persisted_scenario_result_summaries(
            project_root,
            scenario_results_dir=scenario_results_dir,
            read_json=read_json,
            parse_utc_timestamp=parse_utc_timestamp,
            attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
            build_scenario_result_summary=build_scenario_result_summary,
            scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
            scenario_name=str(args.scenario_name or ""),
            limit=int(args.limit or 20),
        )
    )


def cmd_request_scenario_result_latest(args):
    project_root = ensure_project_root(args.project_root)
    print_json(
        latest_persisted_scenario_result_summary(
            project_root,
            scenario_results_dir=scenario_results_dir,
            read_json=read_json,
            parse_utc_timestamp=parse_utc_timestamp,
            attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
            build_scenario_result_summary=build_scenario_result_summary,
            scenario_terminal_statuses=SCENARIO_TERMINAL_STATUSES,
            scenario_name=str(args.scenario_name or ""),
        )
    )


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
    refresh_project_context(project_root)
    print_json(payload)


def cmd_ensure_ready(args):
    project_root = ensure_project_root(args.project_root)
    log_path = resolve_editor_log_path(project_root, args.editor_log_path)

    payload: dict[str, Any] = {
        "project_root": str(project_root),
        "editor_log_path": str(log_path),
        "startup_policy": args.startup_policy,
    }
    payload["discovery"] = build_project_discovery_report(project_root)

    current_state = current_project_context_bridge_state(project_root)

    try:
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
    except ToolInvocationError as exc:
        raise enrich_tool_invocation_error_with_discovery(project_root, exc)

    payload["bridge_state"] = state
    if payload.get("launch") and not bool(payload["launch"].get("reused_existing_editor")):
        update_host_editor_session_pid(project_root, int(state.get("editor_pid") or 0))
    refresh_project_context(project_root)
    payload["discovery_after_ready"] = build_project_discovery_report(project_root)
    payload["package_dependency"] = inspect_package_dependency_alignment(project_root)
    print_json(payload)


def cmd_restore_editor_state(args):
    project_root = ensure_project_root(args.project_root)
    payload = restore_host_opened_editor_state(project_root, args.timeout_ms, request_editor_quit)
    refresh_project_context(project_root)
    if bool(payload.get("host_opened_session_found")) and not bool(payload.get("closeout_verified")):
        closeout_classification = str(payload.get("closeout_classification") or "restore_editor_state_incomplete")
        recommended_next_action = str(payload.get("recommended_next_action") or "inspect_project_editor_processes")
        recommended_recovery_command = str(payload.get("recommended_recovery_command") or "")
        message = (
            "Host-opened editor closeout did not reach verified process exit. "
            f"closeout_classification: {closeout_classification} "
            f"recommended_next_action: {recommended_next_action}"
        )
        if recommended_recovery_command:
            message += f" next_step: {recommended_recovery_command}"
        raise ToolInvocationError("restore_editor_state_incomplete", message, payload)
    print_json(payload)


def cmd_runtime_config_show(args):
    project_root = ensure_project_root(args.project_root)
    print_json(build_runtime_config_report(project_root))


def cmd_project_discovery_report(args):
    project_root = ensure_project_root(args.project_root)
    print_json(build_project_discovery_report(project_root))


def cmd_registry_context_report(args):
    print_json(build_registry_context_report())


def cmd_registry_prune_contexts(args):
    pruned = prune_stale_project_contexts(
        offline_context_max_idle_seconds=args.offline_context_max_idle_seconds,
        general_context_max_idle_seconds=args.general_context_max_idle_seconds,
    )
    print_json(
        {
            "pruned_count": len(pruned),
            "pruned": pruned,
            "remaining": build_registry_context_report(),
        }
    )


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
    host_session = current_project_context_host_session_state(project_root)
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
            truncate_text=truncate_text,
        )
        write_batch_summary_artifact(summary_path, summary)
        raise attach_batch_summary_to_error(
            exc,
            summary_path=summary_path,
            summary=summary,
            tool_invocation_error_type=ToolInvocationError,
        )

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
        truncate_text=truncate_text,
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

    scenario_results_list_cmd = sub.add_parser("request-scenario-results-list", help="List persisted Unity scenario results with compact summaries.")
    scenario_results_list_cmd.add_argument("--project-root", required=True)
    scenario_results_list_cmd.add_argument("--scenario-name")
    scenario_results_list_cmd.add_argument("--limit", type=int, default=20)
    scenario_results_list_cmd.set_defaults(func=cmd_request_scenario_results_list)

    scenario_result_latest_cmd = sub.add_parser("request-scenario-result-latest", help="Read the latest persisted Unity scenario result summary, optionally filtered by scenario name.")
    scenario_result_latest_cmd.add_argument("--project-root", required=True)
    scenario_result_latest_cmd.add_argument("--scenario-name")
    scenario_result_latest_cmd.set_defaults(func=cmd_request_scenario_result_latest)

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

    discovery_report_cmd = sub.add_parser(
        "project-discovery-report",
        help="Print the current project discovery and reconciliation report from the host registry.",
    )
    discovery_report_cmd.add_argument("--project-root", required=True)
    discovery_report_cmd.set_defaults(func=cmd_project_discovery_report)

    registry_report_cmd = sub.add_parser(
        "registry-context-report",
        help="Print the current in-memory per-project registry context cache report.",
    )
    registry_report_cmd.set_defaults(func=cmd_registry_context_report)

    registry_prune_cmd = sub.add_parser(
        "registry-prune-contexts",
        help="Prune stale in-memory per-project registry contexts and print the remaining cache report.",
    )
    registry_prune_cmd.add_argument("--offline-context-max-idle-seconds", type=float)
    registry_prune_cmd.add_argument("--general-context-max-idle-seconds", type=float)
    registry_prune_cmd.set_defaults(func=cmd_registry_prune_contexts)

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
