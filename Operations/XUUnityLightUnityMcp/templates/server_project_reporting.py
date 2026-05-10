from pathlib import Path
from typing import Any, Callable

from server_core import ToolInvocationError


def build_registry_context_report_data(
    contexts: list[Any],
    *,
    now: float,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for context in contexts:
        items.append(
            {
                "project_root": str(context.project_root),
                "instance_key": str(context.instance_key),
                "active_transport": str(context.active_transport or ""),
                "health_classification": str(context.health_classification or ""),
                "discovery_classification": str(context.discovery_classification or ""),
                "last_seen_pid": int(context.last_seen_pid or 0),
                "last_seen_generation": int(context.last_seen_generation or 0),
                "last_refresh_unix": float(context.last_refresh_unix or 0.0),
                "last_access_unix": float(getattr(context, "last_access_unix", 0.0) or 0.0),
                "idle_seconds": round(context.idle_seconds(now), 3),
                "live_runtime_evidence": bool(context.has_live_runtime_evidence()),
            }
        )
    return {
        "context_count": len(items),
        "contexts": items,
    }


def build_project_discovery_report_data(
    project_root: Path,
    *,
    context: Any,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    editor_log_diagnosis = dict(discovery.get("editor_log_diagnosis") or {})
    return {
        "project_root": str(project_root),
        "instance_key": str(getattr(context, "instance_key", project_root)),
        "last_seen_pid": int(getattr(context, "last_seen_pid", 0) or 0),
        "last_seen_generation": int(getattr(context, "last_seen_generation", 0) or 0),
        "last_seen_session_id": str(getattr(context, "last_seen_session_id", "") or ""),
        "active_transport": str(getattr(context, "active_transport", "") or ""),
        "health_classification": str(getattr(context, "health_classification", "") or ""),
        "host_health_classification": str(discovery.get("host_health_classification") or ""),
        "host_health_reason": str(discovery.get("host_health_reason") or ""),
        "host_health_recommended_next_action": str(discovery.get("host_health_recommended_next_action") or ""),
        "host_health_termination_policy": str(discovery.get("host_health_termination_policy") or ""),
        "host_health_heartbeat_age_seconds": discovery.get("host_health_heartbeat_age_seconds"),
        "host_health_busy_reason": str(discovery.get("host_health_busy_reason") or ""),
        "host_health_progress_evidence": list(discovery.get("host_health_progress_evidence") or []),
        "anr_classification": str(discovery.get("anr_classification") or ""),
        "discovery_classification": str(discovery.get("discovery_classification") or ""),
        "discovery_reason": str(discovery.get("discovery_reason") or ""),
        "authoritative_state_source": str(discovery.get("authoritative_state_source") or ""),
        "reconciliation_case": str(discovery.get("reconciliation_case") or ""),
        "reconciliation_status": str(discovery.get("reconciliation_status") or ""),
        "reconciliation_reason": str(discovery.get("reconciliation_reason") or ""),
        "reconciliation_recommended_next_action": str(discovery.get("reconciliation_recommended_next_action") or ""),
        "detected_editor_count": int(discovery.get("detected_editor_count") or 0),
        "detected_editor_pids": list(discovery.get("detected_editor_pids") or []),
        "bridge_state_live": bool(discovery.get("bridge_state_live")),
        "host_session_live": bool(discovery.get("host_session_live")),
        "bridge_enabled": bool(discovery.get("bridge_enabled")),
        "stale_request_artifacts": dict(discovery.get("stale_request_artifacts") or {}),
        "host_prerequisites": dict(discovery.get("host_prerequisites") or {}),
        "transport_metadata": dict(getattr(context, "transport_metadata", {}) or {}),
        "transport_state": dict(discovery.get("transport_state") or getattr(context, "transport_state", {}) or {}),
        "state_groups": dict(discovery.get("state_groups") or getattr(context, "state_groups", {}) or {}),
        "editor_log_diagnosis": editor_log_diagnosis,
        "editor_log_diagnosis_code": str(editor_log_diagnosis.get("code") or ""),
        "editor_log_diagnosis_summary": str(editor_log_diagnosis.get("summary") or ""),
        "context_cache": {
            "created_unix": float(getattr(context, "created_unix", 0.0) or 0.0),
            "last_access_unix": float(getattr(context, "last_access_unix", 0.0) or 0.0),
            "last_refresh_unix": float(getattr(context, "last_refresh_unix", 0.0) or 0.0),
            "idle_seconds": round(context.idle_seconds(), 3),
            "live_runtime_evidence": bool(context.has_live_runtime_evidence()),
        },
        "last_refresh_utc": str(getattr(context, "last_refresh_utc", "") or ""),
    }


def apply_discovery_to_final_status_summary_data(
    summary: dict[str, Any],
    *,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    result = dict(summary or {})
    if discovery:
        result.update(
            {
                "host_health_classification": str(discovery.get("host_health_classification") or ""),
                "host_health_reason": str(discovery.get("host_health_reason") or ""),
                "host_health_recommended_next_action": str(discovery.get("host_health_recommended_next_action") or ""),
                "host_health_termination_policy": str(discovery.get("host_health_termination_policy") or ""),
                "host_health_heartbeat_age_seconds": discovery.get("host_health_heartbeat_age_seconds"),
                "host_health_busy_reason": str(discovery.get("host_health_busy_reason") or ""),
                "host_health_progress_evidence": list(discovery.get("host_health_progress_evidence") or []),
                "anr_classification": str(discovery.get("anr_classification") or ""),
                "discovery_classification": str(discovery.get("discovery_classification") or ""),
                "discovery_reason": str(discovery.get("discovery_reason") or ""),
                "authoritative_state_source": str(discovery.get("authoritative_state_source") or ""),
                "reconciliation_case": str(discovery.get("reconciliation_case") or ""),
                "reconciliation_status": str(discovery.get("reconciliation_status") or ""),
                "reconciliation_reason": str(discovery.get("reconciliation_reason") or ""),
                "reconciliation_recommended_next_action": str(discovery.get("reconciliation_recommended_next_action") or ""),
                "detected_editor_count": int(discovery.get("detected_editor_count") or 0),
                "detected_editor_pids": list(discovery.get("detected_editor_pids") or []),
                "editor_log_diagnosis": dict(discovery.get("editor_log_diagnosis") or {}),
                "stale_request_artifacts": dict(discovery.get("stale_request_artifacts") or {}),
                "host_prerequisites": dict(discovery.get("host_prerequisites") or {}),
                "transport_state": dict(discovery.get("transport_state") or {}),
                "state_groups": dict(discovery.get("state_groups") or {}),
            }
        )

        if (
            not bool(result.get("request_completed"))
            and str(result.get("recommended_next_action") or "") in {
                "",
                "inspect_request_journal",
                "retry_request",
                "wait_for_bridge_stabilization",
            }
        ):
            preferred_next_action = str(
                discovery.get("host_health_recommended_next_action")
                or discovery.get("reconciliation_recommended_next_action")
                or ""
            )
            if preferred_next_action:
                result["recommended_next_action"] = preferred_next_action
    return result


def apply_discovery_to_scenario_payload_data(
    payload: dict[str, Any],
    *,
    project_root: Path,
    discovery: dict[str, Any],
) -> dict[str, Any]:
    result = dict(payload or {})
    result["project_root"] = str(result.get("project_root") or project_root)
    if not discovery:
        return result

    result.update(
        {
            "host_health_classification": str(discovery.get("host_health_classification") or ""),
            "host_health_reason": str(discovery.get("host_health_reason") or ""),
            "host_health_recommended_next_action": str(discovery.get("host_health_recommended_next_action") or ""),
            "host_health_termination_policy": str(discovery.get("host_health_termination_policy") or ""),
            "host_health_heartbeat_age_seconds": discovery.get("host_health_heartbeat_age_seconds"),
            "host_health_busy_reason": str(discovery.get("host_health_busy_reason") or ""),
            "host_health_progress_evidence": list(discovery.get("host_health_progress_evidence") or []),
            "anr_classification": str(discovery.get("anr_classification") or ""),
            "discovery_classification": str(discovery.get("discovery_classification") or ""),
            "discovery_reason": str(discovery.get("discovery_reason") or ""),
            "authoritative_state_source": str(discovery.get("authoritative_state_source") or ""),
            "reconciliation_case": str(discovery.get("reconciliation_case") or ""),
            "reconciliation_status": str(discovery.get("reconciliation_status") or ""),
            "reconciliation_reason": str(discovery.get("reconciliation_reason") or ""),
            "reconciliation_recommended_next_action": str(discovery.get("reconciliation_recommended_next_action") or ""),
            "detected_editor_count": int(discovery.get("detected_editor_count") or 0),
            "detected_editor_pids": list(discovery.get("detected_editor_pids") or []),
            "editor_log_diagnosis": dict(discovery.get("editor_log_diagnosis") or {}),
            "stale_request_artifacts": dict(discovery.get("stale_request_artifacts") or {}),
            "host_prerequisites": dict(discovery.get("host_prerequisites") or {}),
            "transport_state": dict(discovery.get("transport_state") or {}),
            "state_groups": dict(discovery.get("state_groups") or {}),
        }
    )

    if (
        not bool(result.get("terminal"))
        and str(result.get("recommended_next_action") or "") in {"", "retry_request", "wait_for_bridge_stabilization"}
    ):
        preferred_next_action = str(
            discovery.get("host_health_recommended_next_action")
            or discovery.get("reconciliation_recommended_next_action")
            or ""
        )
        if preferred_next_action:
            result["recommended_next_action"] = preferred_next_action
    return result


def enrich_error_details_with_discovery_data(
    project_root: Path,
    *,
    details: dict[str, Any] | None,
    discovery: dict[str, Any],
    recommended_recovery_command_for_project: Callable[[Path, str], str],
) -> dict[str, Any]:
    enriched = dict(details or {})
    if not discovery:
        return enriched

    for key in (
        "host_health_classification",
        "host_health_reason",
        "host_health_recommended_next_action",
        "host_health_termination_policy",
        "host_health_busy_reason",
        "anr_classification",
        "discovery_classification",
        "discovery_reason",
        "authoritative_state_source",
        "reconciliation_case",
        "reconciliation_status",
        "reconciliation_reason",
        "reconciliation_recommended_next_action",
        "detected_editor_count",
        "detected_editor_pids",
    ):
        if key not in enriched and key in discovery:
            enriched[key] = discovery.get(key)

    for key in ("host_health_heartbeat_age_seconds",):
        if key not in enriched and key in discovery:
            enriched[key] = discovery.get(key)

    if "host_health_progress_evidence" not in enriched and "host_health_progress_evidence" in discovery:
        enriched["host_health_progress_evidence"] = list(discovery.get("host_health_progress_evidence") or [])
    if "editor_log_diagnosis" not in enriched and "editor_log_diagnosis" in discovery:
        enriched["editor_log_diagnosis"] = dict(discovery.get("editor_log_diagnosis") or {})
    if "stale_request_artifacts" not in enriched and "stale_request_artifacts" in discovery:
        enriched["stale_request_artifacts"] = dict(discovery.get("stale_request_artifacts") or {})
    if "host_prerequisites" not in enriched and "host_prerequisites" in discovery:
        enriched["host_prerequisites"] = dict(discovery.get("host_prerequisites") or {})
    if "transport_state" not in enriched and "transport_state" in discovery:
        enriched["transport_state"] = dict(discovery.get("transport_state") or {})
    if "state_groups" not in enriched and "state_groups" in discovery:
        enriched["state_groups"] = dict(discovery.get("state_groups") or {})

    current_next_action = str(enriched.get("recommended_next_action") or "")
    preferred_next_action = str(
        discovery.get("host_health_recommended_next_action")
        or discovery.get("reconciliation_recommended_next_action")
        or ""
    )
    if (
        preferred_next_action
        and current_next_action in {
            "",
            "inspect_request_journal",
            "retry_request",
            "wait_for_bridge_stabilization",
            "request_status_summary_then_retry",
            "none",
        }
    ):
        enriched["recommended_next_action"] = preferred_next_action

    next_action = str(enriched.get("recommended_next_action") or "")
    if next_action and not str(enriched.get("recommended_recovery_command") or ""):
        command = recommended_recovery_command_for_project(project_root, next_action)
        if command:
            enriched["recommended_recovery_command"] = command

    return enriched


def build_discovery_status_summary_for_error_data(
    project_root: Path,
    *,
    exc: ToolInvocationError | None,
    discovery: dict[str, Any],
    build_status_summary_from_context: Callable[[Path, dict[str, Any]], dict[str, Any]],
    enrich_error_details_with_discovery: Callable[[Path, dict[str, Any] | None], dict[str, Any]],
) -> dict[str, Any]:
    reconciliation_status = str(discovery.get("reconciliation_status") or "")
    payload = {
        "editor_running": bool(
            discovery.get("bridge_state_live")
            or discovery.get("host_session_live")
            or int(discovery.get("detected_editor_count") or 0) > 0
        ),
        "mcp_reachable": bool(discovery.get("bridge_state_live")),
        "health_status": reconciliation_status or "unknown",
        "transport": str(discovery.get("active_transport") or ""),
    }
    if exc is not None:
        payload["offline_error_code"] = exc.code
        payload["offline_error_message"] = exc.message
    summary = build_status_summary_from_context(project_root, payload)
    if exc is not None:
        summary["error"] = {
            "code": exc.code,
            "message": exc.message,
            "details": enrich_error_details_with_discovery(project_root, exc.details),
        }
    return summary


def build_scenario_result_summary_from_context_data(
    project_root: Path,
    payload: dict[str, Any],
    *,
    discovery: dict[str, Any],
    build_scenario_result_summary: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    scenario_terminal_statuses: set[str],
) -> dict[str, Any]:
    return build_scenario_result_summary(
        apply_discovery_to_scenario_payload_data(
            payload if isinstance(payload, dict) else {},
            project_root=project_root,
            discovery=discovery,
        ),
        scenario_terminal_statuses,
    )


def build_discovery_scenario_result_summary_for_error_data(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    exc: ToolInvocationError,
    *,
    build_scenario_result_summary_from_context: Callable[[Path, dict[str, Any]], dict[str, Any]],
    enrich_error_details_with_discovery: Callable[[Path, dict[str, Any] | None], dict[str, Any]],
) -> dict[str, Any]:
    summary = build_scenario_result_summary_from_context(
        project_root,
        {
            "project_root": str(project_root),
            "run_id": run_id,
            "scenario_name": scenario_name,
            "status": "offline",
            "recommended_next_action": "",
            "offline_error_code": exc.code,
            "offline_error_message": exc.message,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )
    summary["error"] = {
        "code": exc.code,
        "message": exc.message,
        "details": enrich_error_details_with_discovery(project_root, exc.details),
    }
    return summary


def build_request_final_status_from_context_data(
    project_root: Path,
    request_id: str,
    *,
    operation: str,
    poll_timeout_ms: int,
    build_request_final_status: Callable[..., dict[str, Any]],
    current_project_context_bridge_state: Callable[[Path], dict[str, Any]],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    return apply_discovery_to_final_status_summary_data(
        build_request_final_status(
            project_root,
            request_id,
            operation,
            current_state=current_project_context_bridge_state(project_root),
            read_current_state=current_project_context_bridge_state,
            poll_timeout_ms=poll_timeout_ms,
        ),
        discovery=discovery,
    )
