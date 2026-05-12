#!/usr/bin/env python3
import calendar
import json
import os
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from server_host_platform import current_host_platform_adapter
from server_operation_evidence import attach_operation_evidence_to_final_status

from server_core import ToolInvocationError, read_json, write_json

DEFAULT_BRIDGE_TRANSPORT = "file_ipc"
TCP_LOOPBACK_BRIDGE_TRANSPORT = "tcp_loopback"
SUPPORTED_BRIDGE_TRANSPORTS = {
    DEFAULT_BRIDGE_TRANSPORT,
    TCP_LOOPBACK_BRIDGE_TRANSPORT,
}
DEFAULT_HEARTBEAT_MAX_AGE_SECONDS = 10
DEFAULT_IDLE_STABLE_CYCLES = 2


def bridge_root(project_root: Path) -> Path:
    return project_root / "Library" / "XUUnityLightMcp"


def bridge_state_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "state" / "bridge_state.json"


def host_editor_session_state_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "state" / "host_editor_session.json"


def bridge_config_path(project_root: Path) -> Path:
    return bridge_root(project_root) / "config" / "bridge_config.json"


def inbox_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "inbox"


def outbox_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "outbox"


def response_path(project_root: Path, request_id: str) -> Path:
    return outbox_dir(project_root) / f"{request_id}.json"


def logs_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "logs"


def captures_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "captures"


def scenarios_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "scenarios"


def scenario_results_dir(project_root: Path) -> Path:
    return scenarios_dir(project_root) / "results"


def active_scenario_run_path(project_root: Path) -> Path:
    return scenarios_dir(project_root) / "active_run.json"


def default_editor_log_path(project_root: Path) -> Path:
    return logs_dir(project_root) / "unity_editor.log"


def request_journal_dir(project_root: Path) -> Path:
    return bridge_root(project_root) / "journal" / "requests"


def bridge_identity_from_state(state: dict[str, Any] | None) -> tuple[int, str]:
    if not state:
        return 0, ""

    generation = int(state.get("bridge_generation") or 0)
    session_id = str(state.get("bridge_session_id") or "")
    return generation, session_id


def emit_request_submission_ack(
    *,
    project_root: Path,
    operation: str,
    request_id: str,
    transport_name: str,
    state: dict[str, Any] | None,
) -> None:
    bridge_generation, bridge_session_id = bridge_identity_from_state(state)
    message = (
        "[xuunity-light-unity-mcp] request_submitted "
        f"operation={operation} "
        f"request_id={request_id} "
        f"transport={transport_name} "
        f"bridge_generation={bridge_generation} "
        f"bridge_session_id={bridge_session_id or '-'} "
        f"project_root={project_root}\n"
    )
    try:
        sys.stderr.write(message)
        sys.stderr.flush()
    except Exception:
        pass


def emit_request_not_submitted_ack(
    *,
    project_root: Path,
    operation: str,
    transport_name: str,
    reason: str,
) -> None:
    message = (
        "[xuunity-light-unity-mcp] request_not_submitted "
        f"operation={operation} "
        f"transport={transport_name} "
        f"reason={reason} "
        f"project_root={project_root}\n"
    )
    try:
        sys.stderr.write(message)
        sys.stderr.flush()
    except Exception:
        pass


def record_request_submission_event(
    *,
    project_root: Path,
    request_id: str,
    operation: str,
    transport_name: str,
    state: dict[str, Any] | None,
) -> Path:
    bridge_generation, bridge_session_id = bridge_identity_from_state(state)
    return write_host_request_journal_event(
        project_root,
        "request_submitted",
        {
            "request_id": request_id,
            "operation": operation,
            "transport": transport_name,
            "bridge_generation": bridge_generation,
            "bridge_session_id": bridge_session_id,
            "request_submitted": True,
            "request_ownership_acquired": False,
        },
    )


def bridge_identity_changed(
    initial_generation: int,
    initial_session_id: str,
    state: dict[str, Any] | None,
) -> bool:
    current_generation, current_session_id = bridge_identity_from_state(state)
    if current_generation <= 0 and not current_session_id:
        return False

    if initial_generation > 0 and current_generation != initial_generation:
        return True

    if initial_session_id and current_session_id and current_session_id != initial_session_id:
        return True

    return False


def write_host_request_journal_event(
    project_root: Path,
    event_type: str,
    payload: dict[str, Any],
) -> Path:
    journal_dir = request_journal_dir(project_root)
    journal_dir.mkdir(parents=True, exist_ok=True)
    compact_utc = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"{int((time.time() % 1) * 1000):03d}Z"
    event_id = f"{compact_utc}_{uuid.uuid4().hex}_{event_type}"
    path = journal_dir / f"{event_id}.json"
    data = dict(payload)
    data.setdefault("event_id", event_id)
    data.setdefault("event_type", event_type)
    data.setdefault("event_source", "host_wrapper")
    data.setdefault("event_at_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    data.setdefault("project_root", str(project_root))
    write_json(path, data)
    return path


def parse_journal_utc_timestamp(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0

    try:
        return float(calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        return 0.0


def read_request_journal_events(project_root: Path, request_id: str) -> list[dict[str, Any]]:
    journal_dir = request_journal_dir(project_root)
    if not journal_dir.is_dir():
        return []

    matched: list[dict[str, Any]] = []
    for path in journal_dir.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("request_id") or "") != request_id:
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
    return matched


def inbox_request_path(project_root: Path, request_id: str) -> Path:
    return inbox_dir(project_root) / f"{request_id}.json"


def cancel_request_best_effort(
    project_root: Path,
    request_id: str,
    *,
    operation: str = "",
    current_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_state = current_state or read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or {}
    events = read_request_journal_events(project_root, request_id)
    if not events:
        raise ToolInvocationError(
            "request_not_found",
            f"No request journal events were found for request_id={request_id}.",
            {
                "request_id": request_id,
                "request_submitted": False,
                "request_ownership_acquired": False,
                "transport_outcome": "request_not_found",
                "operation_outcome": "request_unknown",
                "recommended_next_action": "request_status_summary_then_retry",
            },
        )

    submitted_events = [event for event in events if str(event.get("event_type") or "") == "request_submitted"]
    submitted_event = submitted_events[-1] if submitted_events else None
    started_event = next((event for event in events if str(event.get("event_type") or "") == "request_started"), None)
    completed_events = [event for event in events if str(event.get("event_type") or "") == "request_completed"]
    completed_event = completed_events[-1] if completed_events else None
    cancellation_events = [
        event
        for event in events
        if str(event.get("event_type") or "") in {"request_cancelled", "request_cancel_requested"}
    ]
    cancellation_event = cancellation_events[-1] if cancellation_events else None
    request_started = started_event is not None
    request_completed = completed_event is not None
    request_submitted = submitted_event is not None
    request_ownership_acquired = request_started or request_completed
    effective_operation = str(
        (completed_event or started_event or submitted_event or {}).get("operation") or operation or ""
    )
    transport_name = str((submitted_event or {}).get("transport") or (effective_state or {}).get("transport") or "")
    stabilization = build_bridge_stabilization_summary(effective_state)
    request_path = inbox_request_path(project_root, request_id)
    request_file_exists = request_path.is_file()

    result: dict[str, Any] = {
        "action": "request_cancel",
        "project_root": str(project_root),
        "request_id": request_id,
        "operation": effective_operation,
        "transport": transport_name,
        "request_submitted": request_submitted,
        "request_started": request_started,
        "request_completed": request_completed,
        "request_ownership_acquired": request_ownership_acquired,
        "request_file_path": str(request_path),
        "request_file_present": request_file_exists,
        "bridge_stabilization": stabilization,
        "recommended_recovery_command": (
            f"request-final-status --project-root {project_root} --request-id {request_id}"
        ),
    }

    if cancellation_event is not None:
        result.update(
            {
                "cancellation_event_type": str(cancellation_event.get("event_type") or ""),
                "cancellation_status": str(
                    cancellation_event.get("cancellation_status")
                    or cancellation_event.get("reclassified_status")
                    or ""
                ),
                "cancellation_reason": str(cancellation_event.get("reason") or ""),
                "recommended_next_action": "request_final_status",
            }
        )
        return result

    if request_completed:
        result.update(
            {
                "cancellation_event_type": "",
                "cancellation_status": "request_already_completed",
                "cancellation_reason": "request_completed_before_cancellation",
                "recommended_next_action": "none",
            }
        )
        return result

    cancellation_event_type = "request_cancel_requested"
    cancellation_status = "cancellation_requested_in_flight"
    cancellation_reason = "host_requested_cancellation_after_submission"
    request_file_deleted = False

    if request_submitted and not request_started and transport_name == DEFAULT_BRIDGE_TRANSPORT and request_file_exists:
        try:
            request_path.unlink()
            request_file_deleted = True
            cancellation_event_type = "request_cancelled"
            cancellation_status = "cancelled_before_unity_start"
            cancellation_reason = "host_cancelled_file_ipc_request_before_unity_start"
        except OSError:
            cancellation_event_type = "request_cancel_requested"
            cancellation_status = "cancellation_requested_in_flight"
            cancellation_reason = "host_cancellation_unable_to_remove_pending_request_file"

    journal_path = write_host_request_journal_event(
        project_root,
        cancellation_event_type,
        {
            "request_id": request_id,
            "operation": effective_operation,
            "reason": cancellation_reason,
            "retryable": True,
            "cancellation_status": cancellation_status,
            "transport": transport_name,
            "request_submitted": request_submitted,
            "request_ownership_acquired": request_ownership_acquired,
        },
    )

    result.update(
        {
            "cancellation_event_type": cancellation_event_type,
            "cancellation_status": cancellation_status,
            "cancellation_reason": cancellation_reason,
            "request_file_deleted": request_file_deleted,
            "journal_event_path": str(journal_path),
            "recommended_next_action": (
                "retry_request"
                if cancellation_status == "cancelled_before_unity_start" and stabilization.get("safe_to_retry")
                else "wait_for_bridge_stabilization"
                if not stabilization.get("safe_to_retry")
                else "request_final_status"
            ),
        }
    )
    return result


def inspect_stale_request_artifacts(
    project_root: Path,
    *,
    current_state: dict[str, Any] | None = None,
    stale_age_seconds: int = 600,
    max_entries: int = 20,
) -> dict[str, Any]:
    effective_state = current_state or read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or {}
    stabilization = build_bridge_stabilization_summary(effective_state)
    pending_request_count = int(stabilization.get("pending_request_count") or 0)
    cutoff_unix = time.time() - max(1, int(stale_age_seconds))
    candidates: list[dict[str, Any]] = []
    classifications: dict[str, int] = {}
    candidate_paths: list[Path] = []

    def consider_path(path: Path, artifact_kind: str) -> None:
        try:
            stat_result = path.stat()
        except OSError:
            return

        if stat_result.st_mtime >= cutoff_unix:
            return

        request_id = str(path.stem or "").strip()
        if not request_id:
            return

        events = read_request_journal_events(project_root, request_id)
        event_types = {str(event.get("event_type") or "") for event in events}
        terminal_event_type = next(
            (
                str(event.get("event_type") or "")
                for event in reversed(events)
                if str(event.get("event_type") or "") in {
                    "request_completed",
                    "request_abandoned",
                    "request_reclassified",
                    "request_cancelled",
                }
            ),
            "",
        )
        request_started = "request_started" in event_types
        request_submitted = "request_submitted" in event_types
        age_seconds = max(0.0, time.time() - stat_result.st_mtime)

        classification = ""
        cleanup_candidate = False
        if artifact_kind == "inbox":
            if terminal_event_type:
                classification = "stale_inbox_after_terminal_event"
                cleanup_candidate = True
            elif request_submitted and not request_started and stabilization.get("safe_to_retry") and pending_request_count == 0:
                classification = "stale_inbox_without_unity_ownership"
                cleanup_candidate = True
        elif artifact_kind == "outbox":
            if terminal_event_type:
                classification = "stale_outbox_after_terminal_event"
                cleanup_candidate = True

        if not cleanup_candidate:
            return

        candidate_paths.append(path.resolve())
        classifications[classification] = int(classifications.get(classification) or 0) + 1
        if len(candidates) < max(0, int(max_entries)):
            candidates.append(
                {
                    "request_id": request_id,
                    "artifact_kind": artifact_kind,
                    "classification": classification,
                    "path": str(path.resolve()),
                    "age_seconds": round(age_seconds, 3),
                    "request_submitted": request_submitted,
                    "request_started": request_started,
                    "terminal_event_type": terminal_event_type,
                }
            )

    for path in inbox_dir(project_root).glob("*.json"):
        consider_path(path, "inbox")
    for path in outbox_dir(project_root).glob("*.json"):
        consider_path(path, "outbox")

    return {
        "has_stale_request_artifacts": bool(candidate_paths),
        "stale_age_seconds": max(1, int(stale_age_seconds)),
        "candidate_count": len(candidate_paths),
        "classifications": classifications,
        "candidates": candidates,
        "bridge_stabilization": stabilization,
    }


def cleanup_stale_request_artifacts(
    project_root: Path,
    *,
    current_state: dict[str, Any] | None = None,
    stale_age_seconds: int = 600,
    dry_run: bool = False,
    max_entries: int = 50,
) -> dict[str, Any]:
    inspection = inspect_stale_request_artifacts(
        project_root,
        current_state=current_state,
        stale_age_seconds=stale_age_seconds,
        max_entries=max_entries,
    )
    removal_inspection = inspect_stale_request_artifacts(
        project_root,
        current_state=current_state,
        stale_age_seconds=stale_age_seconds,
        max_entries=100000,
    )
    removed: list[str] = []
    failed: list[str] = []
    removed_bytes = 0

    for candidate in list(removal_inspection.get("candidates") or []):
        path_text = str(candidate.get("path") or "")
        if not path_text:
            continue
        path = Path(path_text)
        try:
            stat_result = path.stat()
        except OSError:
            continue

        if dry_run:
            removed.append(path_text)
            removed_bytes += int(stat_result.st_size or 0)
            continue

        try:
            path.unlink()
            removed.append(path_text)
            removed_bytes += int(stat_result.st_size or 0)
        except OSError:
            failed.append(path_text)

    return {
        "action": "request_stale_cleanup",
        "project_root": str(project_root),
        "dry_run": bool(dry_run),
        "stale_age_seconds": max(1, int(stale_age_seconds)),
        "inspection": inspection,
        "removed_count": 0 if dry_run else len(removed),
        "failed_count": 0 if dry_run else len(failed),
        "removed_bytes": 0 if dry_run else removed_bytes,
        "removed_paths": [] if dry_run else removed,
        "would_remove_count": len(removed) if dry_run else 0,
        "would_remove_bytes": removed_bytes if dry_run else 0,
        "would_remove_paths": removed if dry_run else [],
        "failed_paths": failed,
    }


def build_bridge_stabilization_summary(
    state: dict[str, Any] | None,
    *,
    editor_running: bool | None = None,
    mcp_reachable: bool | None = None,
) -> dict[str, Any]:
    effective = state or {}
    health_status = str(effective.get("health_status") or "unknown")
    transport = str(effective.get("transport") or effective.get("transport_requested") or "")
    transport_listener_state = str(effective.get("transport_listener_state") or "")
    pending_request_count = int(effective.get("pending_request_count") or 0)
    editor_running_effective = bool(editor_running if editor_running is not None else effective.get("editor_running", True))
    mcp_reachable_effective = bool(mcp_reachable if mcp_reachable is not None else effective.get("mcp_reachable", True))

    blocking_reasons: list[str] = []
    if not editor_running_effective:
        blocking_reasons.append("editor_not_running")
    if not mcp_reachable_effective:
        blocking_reasons.append("mcp_not_reachable")
    if health_status != "healthy":
        blocking_reasons.append("health_not_healthy")
    if bool(effective.get("domain_reload_in_progress")):
        blocking_reasons.append("domain_reload_in_progress")
    if bool(effective.get("asset_import_in_progress")):
        blocking_reasons.append("asset_import_in_progress")
    if bool(effective.get("package_operation_in_progress")):
        blocking_reasons.append("package_operation_in_progress")
    if bool(effective.get("compile_settle_pending")):
        blocking_reasons.append("compile_settle_pending")
    if bool(effective.get("refresh_settle_pending")):
        blocking_reasons.append("refresh_settle_pending")
    if bool(effective.get("playmode_transition_pending")):
        blocking_reasons.append("playmode_transition_pending")
    if pending_request_count > 0:
        blocking_reasons.append("pending_request_in_flight")
    if transport == TCP_LOOPBACK_BRIDGE_TRANSPORT and transport_listener_state not in {"", "listening"}:
        blocking_reasons.append("transport_listener_not_ready")

    stabilized = len(blocking_reasons) == 0
    return {
        "bridge_generation": int(effective.get("bridge_generation") or 0),
        "bridge_session_id": str(effective.get("bridge_session_id") or ""),
        "transport": transport,
        "health_status": health_status,
        "transport_listener_state": transport_listener_state,
        "pending_request_count": pending_request_count,
        "stabilized": stabilized,
        "safe_to_retry": stabilized,
        "blocking_reasons": blocking_reasons,
    }


def classify_result_trust_class(
    *,
    operation_outcome: str,
    request_started: bool,
    request_completed: bool,
    request_observed_in_unity_journal: bool,
) -> str:
    if operation_outcome == "completed_ok":
        return "unity_completed_confirmed"
    if operation_outcome == "completed_failed":
        return "unity_failed_confirmed"
    if operation_outcome == "settled_after_lifecycle_reset":
        return "unity_completed_after_lifecycle_reset"
    if operation_outcome in {
        "retryable_after_lifecycle_reset",
        "abandoned_after_lifecycle_reset",
        "submitted_lost_after_lifecycle_churn",
        "cancellation_requested_in_flight",
    }:
        return "wrapper_failed_unity_unproven"
    if operation_outcome in {
        "cancelled_before_unity_start",
        "submitted_no_unity_journal_confirmation",
    }:
        return "request_not_observed"
    if request_completed:
        return "unity_failed_confirmed"
    if request_started or request_observed_in_unity_journal:
        return "wrapper_failed_unity_unproven"
    return "request_not_observed"


def build_safe_retry_budget(
    *,
    operation_outcome: str,
    recommended_next_action: str,
    retryable: bool,
) -> dict[str, Any]:
    retry_budget_total = 1 if (
        retryable
        or operation_outcome in {
            "retryable_after_lifecycle_reset",
            "abandoned_after_lifecycle_reset",
            "submitted_lost_after_lifecycle_churn",
            "submitted_no_unity_journal_confirmation",
            "cancelled_before_unity_start",
            "cancellation_requested_in_flight",
        }
    ) else 0
    retry_budget_remaining = 1 if (
        retry_budget_total > 0
        and recommended_next_action in {
            "retry_request",
            "wait_for_bridge_stabilization",
            "verify_effect_or_retry",
        }
    ) else 0
    return {
        "safe_retry_budget_total": retry_budget_total,
        "safe_retry_budget_remaining": retry_budget_remaining,
        "safe_retry_budget_exhausted": retry_budget_total > 0 and retry_budget_remaining == 0,
        "safe_retry_budget_blocked": retry_budget_total > 0 and recommended_next_action == "wait_for_bridge_stabilization",
    }


def build_request_final_status(
    project_root: Path,
    request_id: str,
    operation: str = "",
    *,
    current_state: dict[str, Any] | None = None,
    read_current_state: Callable[[Path], dict[str, Any] | None] | None = None,
    poll_timeout_ms: int = 0,
    poll_interval_ms: int = 200,
    return_reclassified_terminal_immediately: bool = True,
) -> dict[str, Any]:
    deadline = time.time() + max(0.0, poll_timeout_ms / 1000.0)

    while True:
        events = read_request_journal_events(project_root, request_id)
        if read_current_state is not None:
            active_state = read_current_state(project_root) or current_state or {}
        else:
            active_state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or current_state or {}
        stabilization = build_bridge_stabilization_summary(active_state)

        submitted_events = [event for event in events if str(event.get("event_type") or "") == "request_submitted"]
        submitted_event = submitted_events[-1] if submitted_events else None
        started_event = next((event for event in events if str(event.get("event_type") or "") == "request_started"), None)
        completed_events = [event for event in events if str(event.get("event_type") or "") == "request_completed"]
        completed_event = completed_events[-1] if completed_events else None
        cancellation_events = [
            event
            for event in events
            if str(event.get("event_type") or "") in {"request_cancelled", "request_cancel_requested"}
        ]
        cancellation_event = cancellation_events[-1] if cancellation_events else None
        reclassified_events = [
            event
            for event in events
            if str(event.get("event_type") or "") in {"request_reclassified", "request_abandoned"}
        ]
        reclassified_event = reclassified_events[-1] if reclassified_events else None
        last_event = events[-1] if events else None

        request_submitted = submitted_event is not None
        completion_status = str((completed_event or {}).get("operation_status") or "")
        request_started = started_event is not None
        request_completed = completed_event is not None
        cancellation_event_type = str((cancellation_event or {}).get("event_type") or "")
        cancellation_status = str(
            (cancellation_event or {}).get("cancellation_status")
            or (cancellation_event or {}).get("reclassified_status")
            or ""
        )
        cancellation_reason = str((cancellation_event or {}).get("reason") or "")
        cancellation_requested = cancellation_event_type == "request_cancel_requested"
        request_cancelled = cancellation_event_type == "request_cancelled"
        reclassified = reclassified_event is not None
        retryable = bool((reclassified_event or {}).get("retryable")) if reclassified else False
        request_observed_in_unity_journal = request_started or request_completed

        submitted_generation = int((submitted_event or {}).get("bridge_generation") or 0)
        submitted_session_id = str((submitted_event or {}).get("bridge_session_id") or "")
        bridge_changed_since_submission = request_submitted and bridge_identity_changed(
            submitted_generation,
            submitted_session_id,
            active_state,
        )
        recovery_gap_detected = (
            request_submitted
            and not request_observed_in_unity_journal
            and bridge_changed_since_submission
            and stabilization["stabilized"]
        )

        reclassified_event_type = str((reclassified_event or {}).get("event_type") or "")
        reclassified_status = str((reclassified_event or {}).get("reclassified_status") or "")
        reclassified_reason = str((reclassified_event or {}).get("reason") or "")

        if request_completed and completion_status == "ok":
            operation_outcome = "completed_ok"
        elif request_completed:
            operation_outcome = "completed_failed"
        elif reclassified_event_type == "request_abandoned" and reclassified_status:
            operation_outcome = reclassified_status
        elif reclassified_event_type == "request_reclassified" and reclassified_status:
            operation_outcome = reclassified_status
        elif request_cancelled and cancellation_status:
            operation_outcome = cancellation_status
        elif cancellation_requested and cancellation_status:
            operation_outcome = cancellation_status
        elif recovery_gap_detected:
            operation_outcome = "submitted_lost_after_lifecycle_churn"
        elif request_submitted and not request_observed_in_unity_journal:
            operation_outcome = "submitted_no_unity_journal_confirmation"
        else:
            operation_outcome = "unknown"

        if operation_outcome == "completed_ok":
            recommended_next_action = "none"
        elif operation_outcome == "completed_failed":
            recommended_next_action = "inspect_request_journal"
        elif operation_outcome in {"retryable_after_lifecycle_reset", "abandoned_after_lifecycle_reset"}:
            recommended_next_action = (
                "retry_request" if stabilization["safe_to_retry"] else "wait_for_bridge_stabilization"
            )
        elif operation_outcome == "cancelled_before_unity_start":
            recommended_next_action = (
                "retry_request" if stabilization["safe_to_retry"] else "wait_for_bridge_stabilization"
            )
        elif operation_outcome == "cancellation_requested_in_flight":
            recommended_next_action = (
                "verify_effect_or_retry" if stabilization["safe_to_retry"] else "wait_for_bridge_stabilization"
            )
        elif operation_outcome == "settled_after_lifecycle_reset":
            recommended_next_action = "verify_effect_or_retry"
        elif operation_outcome == "submitted_lost_after_lifecycle_churn":
            recommended_next_action = "verify_effect_or_retry"
        elif operation_outcome == "submitted_no_unity_journal_confirmation" and stabilization["safe_to_retry"]:
            recommended_next_action = "retry_request"
        elif reclassified and retryable and stabilization["safe_to_retry"]:
            recommended_next_action = "retry_request"
        elif reclassified and not stabilization["safe_to_retry"]:
            recommended_next_action = "wait_for_bridge_stabilization"
        elif not request_started and stabilization["safe_to_retry"]:
            recommended_next_action = "retry_request"
        elif not stabilization["safe_to_retry"]:
            recommended_next_action = "wait_for_bridge_stabilization"
        else:
            recommended_next_action = "inspect_request_journal"

        result_trust_class = classify_result_trust_class(
            operation_outcome=operation_outcome,
            request_started=request_started,
            request_completed=request_completed,
            request_observed_in_unity_journal=request_observed_in_unity_journal,
        )
        retry_budget = build_safe_retry_budget(
            operation_outcome=operation_outcome,
            recommended_next_action=recommended_next_action,
            retryable=retryable,
        )

        summary = {
            "request_id": request_id,
            "operation": str((started_event or completed_event or reclassified_event or submitted_event or {}).get("operation") or operation or ""),
            "request_submitted": request_submitted,
            "request_started": request_started,
            "request_completed": request_completed,
            "request_cancelled": request_cancelled,
            "cancellation_requested": cancellation_requested,
            "cancellation_event_type": cancellation_event_type,
            "cancellation_status": cancellation_status,
            "cancellation_reason": cancellation_reason,
            "completion_status": completion_status,
            "operation_outcome": operation_outcome,
            "reclassified": reclassified,
            "reclassified_event_type": reclassified_event_type,
            "reclassified_status": reclassified_status,
            "reclassified_reason": reclassified_reason,
            "retryable": retryable,
            "recommended_next_action": recommended_next_action,
            "result_trust_class": result_trust_class,
            "recommended_recovery_command": (
                f"request-final-status --project-root {project_root} --request-id {request_id}"
                if request_id
                else ""
            ),
            "request_submitted_at_utc": str((submitted_event or {}).get("event_at_utc") or ""),
            "request_started_at_utc": str((started_event or {}).get("started_at_utc") or (started_event or {}).get("event_at_utc") or ""),
            "request_completed_at_utc": str((completed_event or {}).get("completed_at_utc") or (completed_event or {}).get("event_at_utc") or ""),
            "last_event_type": str((last_event or {}).get("event_type") or ""),
            "last_event_at_utc": str((last_event or {}).get("event_at_utc") or ""),
            "last_bridge_generation_seen": int((last_event or {}).get("bridge_generation") or active_state.get("bridge_generation") or 0),
            "last_bridge_session_id_seen": str((last_event or {}).get("bridge_session_id") or active_state.get("bridge_session_id") or ""),
            "request_observed_in_unity_journal": request_observed_in_unity_journal,
            "bridge_changed_since_submission": bridge_changed_since_submission,
            "recovery_gap_detected": recovery_gap_detected,
            "journal_event_count": len(events),
            "journal_event_paths": [str(event.get("_path") or "") for event in events],
            "bridge_stabilization": stabilization,
            **retry_budget,
        }

        reclassified_terminal = (
            return_reclassified_terminal_immediately
            and reclassified
            and bool(reclassified_status)
            and recommended_next_action != "wait_for_bridge_stabilization"
        )

        if request_completed or recovery_gap_detected or reclassified_terminal or time.time() >= deadline:
            return attach_operation_evidence_to_final_status(
                summary,
                project_root=project_root,
                payload=peek_response_payload(project_root, request_id),
                editor_log_path=default_editor_log_path(project_root),
            )

        time.sleep(max(0.05, poll_interval_ms / 1000.0))


def try_take_recovered_response(project_root: Path, request_id: str) -> dict[str, Any] | None:
    path = response_path(project_root, request_id)
    if not path.is_file():
        return None

    try:
        return read_json(path)
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def peek_response_payload(project_root: Path, request_id: str) -> dict[str, Any] | None:
    path = response_path(project_root, request_id)
    if not path.is_file():
        return None

    try:
        response = read_json(path)
    except Exception:
        return None

    if not isinstance(response, dict):
        return None

    payload_json = response.get("payload_json")
    if not isinstance(payload_json, str) or not payload_json:
        return None

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def try_recover_completed_response_after_reset(
    project_root: Path,
    *,
    request_id: str,
    operation: str,
    current_state: dict[str, Any] | None,
    poll_timeout_ms: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    final_status = build_request_final_status(
        project_root,
        request_id,
        operation,
        current_state=current_state,
        poll_timeout_ms=poll_timeout_ms,
        return_reclassified_terminal_immediately=False,
    )

    if bool(final_status.get("request_completed")):
        recovered_response = try_take_recovered_response(project_root, request_id)
        if recovered_response is not None:
            return recovered_response, final_status

    return None, final_status


def resolve_post_reset_recovery_timeout_ms(
    request_deadline_unix: float,
    post_reset_recovery_cap_ms: int,
) -> int:
    remaining_ms = max(0, int((request_deadline_unix - time.time()) * 1000))
    if remaining_ms <= 0:
        return 0

    cap_ms = max(0, int(post_reset_recovery_cap_ms or 0))
    if cap_ms > 0:
        return min(remaining_ms, cap_ms)
    return remaining_ms


def build_lifecycle_reset_tool_error(
    project_root: Path,
    *,
    request_id: str,
    operation: str,
    transport: str,
    initial_bridge_generation: int,
    initial_bridge_session_id: str,
    current_state: dict[str, Any] | None,
    journal_event_path: Path | None = None,
    retryable_hint: bool | None = None,
    request_processed_hint: bool | None = None,
    transport_host: str = "",
    transport_port: int = 0,
    poll_timeout_ms: int = 1500,
) -> ToolInvocationError:
    _, final_status = try_recover_completed_response_after_reset(
        project_root,
        request_id=request_id,
        operation=operation,
        current_state=current_state,
        poll_timeout_ms=poll_timeout_ms,
    )
    stabilization = final_status.get("bridge_stabilization") or {}
    current_generation = int(stabilization.get("bridge_generation") or 0)
    current_session_id = str(stabilization.get("bridge_session_id") or "")
    operation_outcome = str(final_status.get("operation_outcome") or "unknown")
    recommended_next_action = str(final_status.get("recommended_next_action") or "inspect_request_journal")
    result_trust_class = str(final_status.get("result_trust_class") or "")
    recommended_recovery_command = (
        f"request-final-status --project-root {project_root} --request-id {request_id}"
    )

    message = (
        "The response channel reset before the wrapper could return the result. "
        f"request_id: {request_id} "
        "transport_outcome: reset_before_response_commit "
        f"operation_outcome: {operation_outcome} "
        f"result_trust_class: {result_trust_class or 'unknown'} "
        f"recommended_next_action: {recommended_next_action} "
        f"next_step: {recommended_recovery_command}"
    )
    code = "request_lifecycle_reset"
    if operation_outcome == "completed_ok":
        message = (
            "The response channel reset before the wrapper could return the result. "
            "The Unity operation completed successfully, but the response payload was not observed. "
            f"request_id: {request_id} "
            "transport_outcome: reset_before_response_commit "
            "operation_outcome: completed_ok "
            "result_trust_class: unity_completed_confirmed "
            "recommended_next_action: none "
            f"next_step: {recommended_recovery_command}"
        )
        code = "response_missing_after_lifecycle_reset"
    elif operation_outcome == "completed_failed":
        message = (
            "The response channel reset before the wrapper could return the result. "
            "The Unity operation completed with a failure status, but the response payload was not observed. "
            f"request_id: {request_id} "
            "transport_outcome: reset_before_response_commit "
            "operation_outcome: completed_failed "
            "result_trust_class: unity_failed_confirmed "
            "recommended_next_action: inspect_request_journal "
            f"next_step: {recommended_recovery_command}"
        )
        code = "response_missing_after_lifecycle_reset"
    else:
        message = (
            message + ". The Unity operation may still have completed."
        )

    details: dict[str, Any] = {
        "request_id": request_id,
        "operation": operation,
        "transport": transport,
        "transport_outcome": "reset_before_response_commit",
        "operation_outcome": operation_outcome,
        "recommended_next_action": recommended_next_action,
        "result_trust_class": result_trust_class,
        "recommended_recovery_command": recommended_recovery_command,
        "initial_bridge_generation": initial_bridge_generation,
        "initial_bridge_session_id": initial_bridge_session_id,
        "current_bridge_generation": current_generation,
        "current_bridge_session_id": current_session_id,
        "retryable": bool(retryable_hint if retryable_hint is not None else final_status.get("retryable")),
        "request_processed": bool(request_processed_hint if request_processed_hint is not None else final_status.get("request_completed")),
        "request_final_status": final_status,
        "bridge_stabilization": stabilization,
        "safe_retry_budget_total": int(final_status.get("safe_retry_budget_total") or 0),
        "safe_retry_budget_remaining": int(final_status.get("safe_retry_budget_remaining") or 0),
        "safe_retry_budget_exhausted": bool(final_status.get("safe_retry_budget_exhausted")),
        "safe_retry_budget_blocked": bool(final_status.get("safe_retry_budget_blocked")),
    }
    if journal_event_path is not None:
        details["journal_event_path"] = str(journal_event_path)
    if transport_host:
        details["host"] = transport_host
    if transport_port > 0:
        details["port"] = transport_port
    return ToolInvocationError(code, message, details)


def build_transport_response_missing_tool_error(
    project_root: Path,
    *,
    request_id: str,
    operation: str,
    transport: str,
    current_state: dict[str, Any] | None,
    transport_host: str = "",
    transport_port: int = 0,
    poll_timeout_ms: int = 1000,
) -> ToolInvocationError:
    final_status = build_request_final_status(
        project_root,
        request_id,
        operation,
        current_state=current_state,
        poll_timeout_ms=poll_timeout_ms,
    )
    stabilization = final_status.get("bridge_stabilization") or {}
    operation_outcome = str(final_status.get("operation_outcome") or "unknown")
    result_trust_class = str(final_status.get("result_trust_class") or "")
    request_processed = bool(final_status.get("request_started") or final_status.get("request_completed"))
    recommended_next_action = str(final_status.get("recommended_next_action") or "retry_request")
    recommended_recovery_command = (
        f"request-final-status --project-root {project_root} --request-id {request_id}"
    )

    if request_processed:
        message = (
            "The TCP loopback transport closed before the wrapper observed a response payload. "
            f"request_id: {request_id} "
            "transport_outcome: response_missing_without_reset_signal "
            f"operation_outcome: {operation_outcome} "
            f"result_trust_class: {result_trust_class or 'unknown'} "
            f"recommended_next_action: {recommended_next_action} "
            f"next_step: {recommended_recovery_command}"
        )
    else:
        message = (
            "The TCP loopback transport closed before the request was observed in the Unity request journal. "
            f"request_id: {request_id} "
            "transport_outcome: response_missing_without_reset_signal "
            "operation_outcome: unknown "
            "recommended_next_action: retry_request "
            f"next_step: {recommended_recovery_command}"
        )

    details: dict[str, Any] = {
        "request_id": request_id,
        "operation": operation,
        "transport": transport,
        "transport_outcome": "response_missing_without_reset_signal",
        "operation_outcome": operation_outcome,
        "recommended_next_action": recommended_next_action,
        "result_trust_class": result_trust_class,
        "recommended_recovery_command": recommended_recovery_command,
        "retryable": bool(final_status.get("retryable")) if request_processed else True,
        "request_processed": request_processed,
        "request_final_status": final_status,
        "bridge_stabilization": stabilization,
        "safe_retry_budget_total": int(final_status.get("safe_retry_budget_total") or 0),
        "safe_retry_budget_remaining": int(final_status.get("safe_retry_budget_remaining") or 0),
        "safe_retry_budget_exhausted": bool(final_status.get("safe_retry_budget_exhausted")),
        "safe_retry_budget_blocked": bool(final_status.get("safe_retry_budget_blocked")),
    }
    if transport_host:
        details["host"] = transport_host
    if transport_port > 0:
        details["port"] = transport_port
    return ToolInvocationError("transport_response_missing", message, details)


def maybe_record_settle_lifecycle_transition(
    project_root: Path,
    operation: str,
    request_id: str,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    initial_generation, initial_session_id = bridge_identity_from_state(before_state)
    current_generation, current_session_id = bridge_identity_from_state(after_state)
    if not bridge_identity_changed(initial_generation, initial_session_id, after_state):
        return None

    journal_path = write_host_request_journal_event(
        project_root,
        "request_reclassified",
        {
            "request_id": request_id,
            "operation": operation,
            "reason": "bridge_generation_changed_during_post_request_settle",
            "retryable": False,
            "reclassified_status": "settled_after_lifecycle_reset",
            "previous_bridge_generation": initial_generation,
            "previous_bridge_session_id": initial_session_id,
            "bridge_generation": current_generation,
            "bridge_session_id": current_session_id,
        },
    )
    return {
        "request_id": request_id,
        "operation": operation,
        "previous_bridge_generation": initial_generation,
        "previous_bridge_session_id": initial_session_id,
        "current_bridge_generation": current_generation,
        "current_bridge_session_id": current_session_id,
        "journal_event_path": str(journal_path),
        "reclassified_status": "settled_after_lifecycle_reset",
    }


def bridge_enabled(project_root: Path) -> bool:
    config_path = bridge_config_path(project_root)
    if not config_path.is_file():
        return False

    try:
        data = read_json(config_path)
    except Exception:
        return False

    return bool(data.get("enabled"))


def try_read_bridge_config(project_root: Path) -> dict[str, Any] | None:
    config_path = bridge_config_path(project_root)
    if not config_path.is_file():
        return None

    try:
        data = read_json(config_path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def try_read_bridge_state(project_root: Path) -> dict[str, Any] | None:
    path = bridge_state_path(project_root)
    if not path.is_file():
        return None

    try:
        data = read_json(path)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def pid_is_alive(pid: int) -> bool:
    return current_host_platform_adapter().pid_is_alive(pid)


def try_read_live_editor_state(project_root: Path) -> dict[str, Any] | None:
    state = try_read_bridge_state(project_root)
    if not state:
        return None

    pid = int(state.get("editor_pid") or 0)
    if not pid_is_alive(pid):
        return None

    return state


def read_best_effort_bridge_state(project_root: Path) -> dict[str, Any] | None:
    live_state = try_read_live_editor_state(project_root)
    if live_state is not None:
        return live_state

    state = try_read_bridge_state(project_root)
    if state is None:
        return None

    pid = int(state.get("editor_pid") or 0)
    if pid > 0 and not pid_is_alive(pid):
        return None

    return state


class BridgeTransportAdapter:
    name = "unknown"

    def metadata(self, project_root: Path) -> dict[str, Any]:
        return {
            "name": self.name,
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
        post_reset_recovery_cap_ms: int = 0,
    ) -> tuple[dict[str, Any], str, float]:
        raise NotImplementedError


class FileIpcBridgeTransport(BridgeTransportAdapter):
    name = DEFAULT_BRIDGE_TRANSPORT

    def metadata(self, project_root: Path) -> dict[str, Any]:
        return {
            "name": self.name,
            "state_path": str(bridge_state_path(project_root)),
            "request_directory": str(inbox_dir(project_root)),
            "response_directory": str(outbox_dir(project_root)),
            "journal_directory": str(request_journal_dir(project_root)),
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
        post_reset_recovery_cap_ms: int = 0,
    ) -> tuple[dict[str, Any], str, float]:
        state_path = bridge_state_path(project_root)
        if not state_path.is_file():
            emit_request_not_submitted_ack(
                project_root=project_root,
                operation=operation,
                transport_name=self.name,
                reason="bridge_state_missing",
            )
            raise ToolInvocationError(
                "editor_not_running",
                f"Bridge state file not found: {state_path}",
                {
                    "request_submitted": False,
                    "request_ownership_acquired": False,
                    "transport_outcome": "request_not_submitted",
                    "operation_outcome": "request_not_dispatched",
                    "recommended_next_action": "start_or_recover_editor",
                    "transport": self.name,
                },
            )

        in_dir = inbox_dir(project_root)
        out_dir = outbox_dir(project_root)
        in_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        request_id = str(uuid.uuid4())
        request_path = in_dir / f"{request_id}.json"
        response_path = out_dir / f"{request_id}.json"
        request_started_at = time.time()
        initial_state = read_best_effort_bridge_state(project_root)
        initial_generation, initial_session_id = bridge_identity_from_state(initial_state)
        observed_reset_state: dict[str, Any] | None = None

        request = {
            "request_id": request_id,
            "operation": operation,
            "project_root": str(project_root),
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timeout_ms": timeout_ms,
            "args_json": json.dumps(args, ensure_ascii=True, separators=(",", ":")),
        }

        write_json(request_path, request)
        emit_request_submission_ack(
            project_root=project_root,
            operation=operation,
            request_id=request_id,
            transport_name=self.name,
            state=initial_state,
        )
        record_request_submission_event(
            project_root=project_root,
            request_id=request_id,
            operation=operation,
            transport_name=self.name,
            state=initial_state,
        )

        deadline = time.time() + (timeout_ms / 1000.0)
        while time.time() < deadline:
            if response_path.is_file():
                try:
                    response = read_json(response_path)
                finally:
                    try:
                        response_path.unlink()
                    except OSError:
                        pass
                return response, request_id, request_started_at

            current_state = read_best_effort_bridge_state(project_root)
            if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                observed_reset_state = current_state

            time.sleep(0.2)

        state = read_best_effort_bridge_state(project_root)
        if observed_reset_state is not None:
            state = state or observed_reset_state
            recovery_timeout_ms = resolve_post_reset_recovery_timeout_ms(deadline, post_reset_recovery_cap_ms)
            recovered_response, _ = try_recover_completed_response_after_reset(
                project_root,
                request_id=request_id,
                operation=operation,
                current_state=state,
                poll_timeout_ms=recovery_timeout_ms,
            )
            if recovered_response is not None:
                return recovered_response, request_id, request_started_at

            current_generation, current_session_id = bridge_identity_from_state(state)
            processed = str((state or {}).get("last_processed_request_id") or "") == request_id
            retryable = not processed
            journal_path = write_host_request_journal_event(
                project_root,
                "request_reclassified",
                {
                    "request_id": request_id,
                    "operation": operation,
                    "reason": "bridge_generation_changed_before_response",
                    "retryable": retryable,
                    "reclassified_status": (
                        "retryable_after_lifecycle_reset"
                        if retryable
                        else "response_missing_after_lifecycle_reset"
                    ),
                    "previous_bridge_generation": initial_generation,
                    "previous_bridge_session_id": initial_session_id,
                    "bridge_generation": current_generation,
                    "bridge_session_id": current_session_id,
                },
            )
            try:
                if request_path.exists():
                    request_path.unlink()
            except OSError:
                pass
            raise build_lifecycle_reset_tool_error(
                project_root,
                request_id=request_id,
                operation=operation,
                transport=self.name,
                initial_bridge_generation=initial_generation,
                initial_bridge_session_id=initial_session_id,
                current_state=state,
                journal_event_path=journal_path,
                retryable_hint=retryable,
                request_processed_hint=processed,
                poll_timeout_ms=recovery_timeout_ms,
            )

        raise ToolInvocationError(
            "operation_timeout",
            f"Timed out waiting for {response_path}. transport={self.name}. {summarize_state_for_error(state)}",
        )


class TcpLoopbackBridgeTransport(BridgeTransportAdapter):
    name = TCP_LOOPBACK_BRIDGE_TRANSPORT

    def metadata(self, project_root: Path) -> dict[str, Any]:
        state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or {}
        return {
            "name": self.name,
            "requested_transport": str(state.get("transport_requested") or self.name),
            "listener_state": str(state.get("transport_listener_state") or ""),
            "host": str(state.get("transport_host") or "127.0.0.1"),
            "port": int(state.get("transport_port") or 0),
            "state_path": str(bridge_state_path(project_root)),
            "journal_directory": str(request_journal_dir(project_root)),
        }

    def invoke(
        self,
        project_root: Path,
        operation: str,
        args: dict[str, Any],
        timeout_ms: int,
        post_reset_recovery_cap_ms: int = 0,
    ) -> tuple[dict[str, Any], str, float]:
        raw_state = try_read_bridge_state(project_root)
        state = read_best_effort_bridge_state(project_root)
        if state is None and raw_state is not None:
            liveness = inspect_bridge_state_liveness(raw_state)
            if not bool(liveness.get("editor_pid_alive")):
                stale_pid = int(liveness.get("editor_pid") or 0)
                stale_listener_state = str(raw_state.get("transport_listener_state") or "")
                stale_host = str(raw_state.get("transport_host") or "127.0.0.1")
                stale_port = int(raw_state.get("transport_port") or 0)
                raise ToolInvocationError(
                    "editor_not_running",
                    (
                        "Unity editor is not running for this project. "
                        f"Found stale bridge state with editor_pid={stale_pid}, "
                        f"listener_state={stale_listener_state or 'unknown'}, "
                        f"host={stale_host}, port={stale_port}. "
                        "Reopen Unity or run ensure-ready --open-editor."
                    ),
                    {
                        "transport": self.name,
                        "state_path": str(bridge_state_path(project_root)),
                        "state_liveness": liveness,
                    },
                )

        host = str((state or {}).get("transport_host") or "127.0.0.1")
        port = int((state or {}).get("transport_port") or 0)
        listener_state = str((state or {}).get("transport_listener_state") or "")
        if port <= 0:
            raise ToolInvocationError(
                "transport_not_ready",
                (
                    f"TCP loopback transport is not ready. "
                    f"listener_state={listener_state or 'unknown'} host={host} port={port}."
                ),
            )

        request_id = str(uuid.uuid4())
        request_started_at = time.time()
        initial_state = state
        initial_generation, initial_session_id = bridge_identity_from_state(initial_state)
        observed_reset_state: dict[str, Any] | None = None
        request = {
            "request_id": request_id,
            "operation": operation,
            "project_root": str(project_root),
            "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timeout_ms": timeout_ms,
            "args_json": json.dumps(args, ensure_ascii=True, separators=(",", ":")),
        }
        payload = (json.dumps(request, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        deadline = time.time() + (timeout_ms / 1000.0)
        chunks: list[bytes] = []

        try:
            connect_timeout = max(1.0, min(5.0, timeout_ms / 1000.0))
            with socket.create_connection((host, port), timeout=connect_timeout) as sock:
                sock.settimeout(0.2)
                sock.sendall(payload)
                emit_request_submission_ack(
                    project_root=project_root,
                    operation=operation,
                    request_id=request_id,
                    transport_name=self.name,
                    state=initial_state,
                )
                record_request_submission_event(
                    project_root=project_root,
                    request_id=request_id,
                    operation=operation,
                    transport_name=self.name,
                    state=initial_state,
                )
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

                while time.time() < deadline:
                    try:
                        chunk = sock.recv(65536)
                        if chunk:
                            chunks.append(chunk)
                            continue
                        break
                    except socket.timeout:
                        current_state = read_best_effort_bridge_state(project_root)
                        if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                            observed_reset_state = current_state
                        continue
                    except OSError as exc:
                        current_state = read_best_effort_bridge_state(project_root)
                        if observed_reset_state is None and bridge_identity_changed(initial_generation, initial_session_id, current_state):
                            observed_reset_state = current_state
                            break
                        raise ToolInvocationError(
                            "transport_io_failed",
                            (
                                f"TCP loopback transport failed for {operation}: {exc}. "
                                f"host={host} port={port}."
                            ),
                            {
                                "request_id": request_id,
                                "operation": operation,
                                "transport": self.name,
                                "host": host,
                                "port": port,
                            },
                        ) from exc
        except ToolInvocationError:
            raise
        except OSError as exc:
            emit_request_not_submitted_ack(
                project_root=project_root,
                operation=operation,
                transport_name=self.name,
                reason="transport_connect_failed",
            )
            raise ToolInvocationError(
                "transport_connect_failed",
                (
                    f"Failed to connect to TCP loopback transport for {operation}: {exc}. "
                    f"host={host} port={port} listener_state={listener_state or 'unknown'}."
                ),
                {
                    "request_id": request_id,
                    "request_submitted": False,
                    "request_ownership_acquired": False,
                    "operation": operation,
                    "transport_outcome": "request_not_submitted",
                    "operation_outcome": "request_not_dispatched",
                    "recommended_next_action": "request_status_summary_then_retry",
                    "transport": self.name,
                    "host": host,
                    "port": port,
                    "listener_state": listener_state,
                },
            ) from exc

        if chunks:
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ToolInvocationError(
                    "transport_response_invalid",
                    f"TCP loopback transport returned invalid JSON for {operation}: {exc}.",
                    {
                        "request_id": request_id,
                        "operation": operation,
                        "transport": self.name,
                        "host": host,
                        "port": port,
                    },
                ) from exc
            if response.get("status") == "error":
                error = response.get("error") or {}
                error_code = str(error.get("code") or "")
                if error_code == "transport_restarting":
                    current_state = read_best_effort_bridge_state(project_root)
                    recovery_timeout_ms = resolve_post_reset_recovery_timeout_ms(deadline, post_reset_recovery_cap_ms)
                    recovered_response, _ = try_recover_completed_response_after_reset(
                        project_root,
                        request_id=request_id,
                        operation=operation,
                        current_state=current_state,
                        poll_timeout_ms=recovery_timeout_ms,
                    )
                    if recovered_response is not None:
                        return recovered_response, request_id, request_started_at

                    current_generation, current_session_id = bridge_identity_from_state(current_state)
                    journal_path = write_host_request_journal_event(
                        project_root,
                        "request_reclassified",
                        {
                            "request_id": request_id,
                            "operation": operation,
                            "reason": "bridge_generation_changed_before_response",
                            "retryable": True,
                            "reclassified_status": "retryable_after_lifecycle_reset",
                            "previous_bridge_generation": initial_generation,
                            "previous_bridge_session_id": initial_session_id,
                            "bridge_generation": current_generation,
                            "bridge_session_id": current_session_id,
                        },
                    )
                    raise build_lifecycle_reset_tool_error(
                        project_root,
                        request_id=request_id,
                        operation=operation,
                        transport=self.name,
                        initial_bridge_generation=initial_generation,
                        initial_bridge_session_id=initial_session_id,
                        current_state=current_state,
                        journal_event_path=journal_path,
                        retryable_hint=True,
                        transport_host=host,
                        transport_port=port,
                        poll_timeout_ms=recovery_timeout_ms,
                    )
            return response, request_id, request_started_at

        state = read_best_effort_bridge_state(project_root)
        if observed_reset_state is not None:
            state = state or observed_reset_state
            recovery_timeout_ms = resolve_post_reset_recovery_timeout_ms(deadline, post_reset_recovery_cap_ms)
            recovered_response, _ = try_recover_completed_response_after_reset(
                project_root,
                request_id=request_id,
                operation=operation,
                current_state=state,
                poll_timeout_ms=recovery_timeout_ms,
            )
            if recovered_response is not None:
                return recovered_response, request_id, request_started_at

            current_generation, current_session_id = bridge_identity_from_state(state)
            processed = str((state or {}).get("last_processed_request_id") or "") == request_id
            retryable = not processed
            journal_path = write_host_request_journal_event(
                project_root,
                "request_reclassified",
                {
                    "request_id": request_id,
                    "operation": operation,
                    "reason": "bridge_generation_changed_before_response",
                    "retryable": retryable,
                    "reclassified_status": (
                        "retryable_after_lifecycle_reset"
                        if retryable
                        else "response_missing_after_lifecycle_reset"
                    ),
                    "previous_bridge_generation": initial_generation,
                    "previous_bridge_session_id": initial_session_id,
                    "bridge_generation": current_generation,
                    "bridge_session_id": current_session_id,
                },
            )
            raise build_lifecycle_reset_tool_error(
                project_root,
                request_id=request_id,
                operation=operation,
                transport=self.name,
                initial_bridge_generation=initial_generation,
                initial_bridge_session_id=initial_session_id,
                current_state=state,
                journal_event_path=journal_path,
                retryable_hint=retryable,
                request_processed_hint=processed,
                transport_host=host,
                transport_port=port,
                poll_timeout_ms=recovery_timeout_ms,
            )

        raise build_transport_response_missing_tool_error(
            project_root,
            request_id=request_id,
            operation=operation,
            transport=self.name,
            current_state=state,
            transport_host=host,
            transport_port=port,
        )


def resolve_bridge_transport(project_root: Path) -> BridgeTransportAdapter:
    config = try_read_bridge_config(project_root) or {}
    state = read_best_effort_bridge_state(project_root) or {}
    state_transport = str(state.get("transport") or "").strip().lower()
    if state_transport:
        configured_transport = state_transport
    else:
        bridge_version = int(state.get("bridge_version") or 0)
        configured_transport = (
            DEFAULT_BRIDGE_TRANSPORT
            if bridge_version > 0
            else str(
                config.get("transport")
                or config.get("bridge_transport")
                or DEFAULT_BRIDGE_TRANSPORT
            ).strip().lower()
        )
    if not configured_transport:
        configured_transport = DEFAULT_BRIDGE_TRANSPORT

    if configured_transport == DEFAULT_BRIDGE_TRANSPORT:
        return FileIpcBridgeTransport()

    if configured_transport == TCP_LOOPBACK_BRIDGE_TRANSPORT:
        return TcpLoopbackBridgeTransport()

    supported = ", ".join(sorted(SUPPORTED_BRIDGE_TRANSPORTS))
    raise ToolInvocationError(
        "unsupported_bridge_transport",
        (
            f"Unsupported bridge transport '{configured_transport}'. "
            f"Supported transports: {supported}."
        ),
    )


def invoke_bridge_transport(
    project_root: Path,
    operation: str,
    args: dict[str, Any],
    timeout_ms: int,
    post_reset_recovery_cap_ms: int = 0,
) -> tuple[dict[str, Any], str, float, dict[str, Any]]:
    if not bridge_enabled(project_root):
        emit_request_not_submitted_ack(
            project_root=project_root,
            operation=operation,
            transport_name="disabled",
            reason="bridge_disabled",
        )
        raise ToolInvocationError(
            "bridge_disabled",
            (
                "Unity bridge is disabled for this project. "
                "Enable it with init_xuunity_light_unity_mcp.sh --project-root <path> --enable-project "
                "and reopen Unity."
            ),
            {
                "request_submitted": False,
                "request_ownership_acquired": False,
                "transport_outcome": "request_not_submitted",
                "operation_outcome": "request_not_dispatched",
                "recommended_next_action": "enable_bridge_and_retry",
                "transport": "disabled",
            },
        )

    transport = resolve_bridge_transport(project_root)
    response, request_id, request_started_at = transport.invoke(
        project_root,
        operation,
        args,
        timeout_ms,
        post_reset_recovery_cap_ms=post_reset_recovery_cap_ms,
    )
    return response, request_id, request_started_at, transport.metadata(project_root)


def heartbeat_age_seconds(state: dict[str, Any]) -> float | None:
    heartbeat_utc = state.get("heartbeat_utc")
    if not isinstance(heartbeat_utc, str) or not heartbeat_utc:
        return None

    try:
        heartbeat_unix = calendar.timegm(time.strptime(heartbeat_utc, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None

    return max(0.0, time.time() - heartbeat_unix)


def inspect_bridge_state_liveness(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {
            "state_present": False,
            "state_is_live": False,
            "editor_pid": 0,
            "editor_pid_alive": False,
            "heartbeat_age_seconds": None,
            "stale_reason": "state_missing",
        }

    pid = int(state.get("editor_pid") or 0)
    pid_alive = pid > 0 and pid_is_alive(pid)
    heartbeat_age = heartbeat_age_seconds(state)
    stale_reason = ""

    if pid <= 0:
        stale_reason = "missing_editor_pid"
    elif not pid_alive:
        stale_reason = "editor_pid_not_alive"

    return {
        "state_present": True,
        "state_is_live": pid_alive,
        "editor_pid": pid,
        "editor_pid_alive": pid_alive,
        "heartbeat_age_seconds": round(heartbeat_age, 3) if heartbeat_age is not None else None,
        "stale_reason": stale_reason,
    }


def annotate_bridge_state_with_liveness(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not state:
        return None

    annotated = dict(state)
    annotated["_xuunity_bridge_state"] = inspect_bridge_state_liveness(state)
    return annotated


def parse_utc_timestamp(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return float(calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        return None


def state_is_idle(state: dict[str, Any]) -> bool:
    return (
        not bool(state.get("domain_reload_in_progress"))
        and not bool(state.get("package_operation_in_progress"))
        and not bool(state.get("script_reload_pending"))
        and not bool(state.get("asset_import_in_progress"))
        and not bool(state.get("refresh_settle_pending"))
        and not bool(state.get("compile_settle_pending"))
        and not bool(state.get("playmode_transition_pending"))
        and not bool(state.get("is_compiling"))
        and not bool(state.get("is_updating"))
        and not bool(state.get("active_operation"))
        and (bool(state.get("is_playing")) or not bool(state.get("is_playing_or_will_change_playmode")))
    )


def derive_busy_reason(state: dict[str, Any] | None) -> str:
    if not state:
        return "bridge_state_missing"

    busy_reason = state.get("busy_reason")
    if isinstance(busy_reason, str) and busy_reason:
        return busy_reason

    if bool(state.get("domain_reload_in_progress")):
        return "domain_reload"

    if bool(state.get("package_operation_in_progress")):
        return "package_operation"

    if bool(state.get("refresh_settle_pending")):
        return "refresh_settle"

    if bool(state.get("compile_settle_pending")):
        return "compile_settle"

    if bool(state.get("playmode_transition_pending")):
        return "playmode_settle"

    if bool(state.get("is_compiling")):
        return "compiling"

    if bool(state.get("script_reload_pending")):
        return "script_reload_pending"

    if bool(state.get("asset_import_in_progress")):
        return "asset_import"

    if bool(state.get("is_updating")):
        return "updating"

    if state.get("active_operation"):
        return "processing_request"

    if not bool(state.get("is_playing")) and bool(state.get("is_playing_or_will_change_playmode")):
        return "playmode_transition"

    if int(state.get("pending_request_count") or 0) > 0:
        return "request_queue_pending"

    return "idle"


def summarize_state_for_error(state: dict[str, Any] | None) -> str:
    if not state:
        return "No live bridge state was available."

    heartbeat_age = heartbeat_age_seconds(state)
    heartbeat_summary = "unknown"
    if heartbeat_age is not None:
        heartbeat_summary = f"{round(heartbeat_age, 3)}s"

    return (
        f"bridge_version={state.get('bridge_version') or 'unknown'}, "
        f"bridge_generation={state.get('bridge_generation') or 'unknown'}, "
        f"bridge_session_id={state.get('bridge_session_id') or ''}, "
        f"busy_reason={derive_busy_reason(state)}, "
        f"heartbeat_age={heartbeat_summary}, "
        f"domain_reload_in_progress={bool(state.get('domain_reload_in_progress'))}, "
        f"package_operation_in_progress={bool(state.get('package_operation_in_progress'))}, "
        f"package_operation_name={state.get('package_operation_name') or ''}, "
        f"package_operation_phase={state.get('package_operation_phase') or ''}, "
        f"refresh_settle_pending={bool(state.get('refresh_settle_pending'))}, "
        f"refresh_settle_phase={state.get('refresh_settle_phase') or ''}, "
        f"compile_settle_pending={bool(state.get('compile_settle_pending'))}, "
        f"compile_settle_phase={state.get('compile_settle_phase') or ''}, "
        f"playmode_transition_pending={bool(state.get('playmode_transition_pending'))}, "
        f"playmode_transition_phase={state.get('playmode_transition_phase') or ''}, "
        f"playmode_transition_target_state={state.get('playmode_transition_target_state') or ''}, "
        f"script_reload_pending={bool(state.get('script_reload_pending'))}, "
        f"asset_import_in_progress={bool(state.get('asset_import_in_progress'))}, "
        f"is_compiling={bool(state.get('is_compiling'))}, "
        f"is_updating={bool(state.get('is_updating'))}, "
        f"is_playing={bool(state.get('is_playing'))}, "
        f"is_playing_or_will_change_playmode={bool(state.get('is_playing_or_will_change_playmode'))}, "
        f"health_status={state.get('health_status') or 'unknown'}, "
        f"active_operation={state.get('active_operation') or ''}, "
        f"busy_reason_detail={state.get('busy_reason_detail') or ''}, "
        f"last_processed_request_id={state.get('last_processed_request_id') or ''}, "
        f"request_journal_head={state.get('request_journal_head') or ''}, "
        f"pending_request_count={int(state.get('pending_request_count') or 0)}"
    )


def wait_for_editor_idle(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    reason: str,
    *,
    after_request_id: str | None = None,
    not_before_unix: float | None = None,
    require_healthy_bridge: bool = True,
    stable_cycles: int = DEFAULT_IDLE_STABLE_CYCLES,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    stable_matches = 0
    last_state: dict[str, Any] | None = None

    while time.time() < deadline:
        state = try_read_live_editor_state(project_root)
        if state:
            last_state = state
            age_seconds = heartbeat_age_seconds(state)
            heartbeat_is_fresh = age_seconds is not None and age_seconds <= heartbeat_max_age_seconds
            bridge_is_healthy = not require_healthy_bridge or state.get("health_status") == "healthy"
            last_processed_request_id = str(state.get("last_processed_request_id") or "")
            last_pump_unix = parse_utc_timestamp(state.get("last_pump_utc"))
            request_match = (
                after_request_id is None
                or last_processed_request_id == after_request_id
                or (not_before_unix is not None and last_pump_unix is not None and last_pump_unix >= not_before_unix)
            )
            editor_is_idle = state_is_idle(state)

            if heartbeat_is_fresh and bridge_is_healthy and request_match and editor_is_idle:
                stable_matches += 1
                if stable_matches >= max(1, stable_cycles):
                    result = dict(state)
                    result["heartbeat_age_seconds"] = round(age_seconds or 0.0, 3)
                    result["idle_wait_reason"] = reason
                    result["idle_wait_duration_seconds"] = round(time.time() - started_at, 3)
                    return result
            else:
                stable_matches = 0
        else:
            stable_matches = 0

        time.sleep(0.5)

    request_summary = ""
    if after_request_id:
        request_summary = f" request_id={after_request_id}."

    raise ToolInvocationError(
        "editor_idle_timeout",
        (
            f"Timed out waiting for Unity editor idle ({reason})."
            f"{request_summary} {summarize_state_for_error(last_state)}"
        ),
    )


def wait_for_playmode_state(
    project_root: Path,
    timeout_ms: int,
    heartbeat_max_age_seconds: int,
    expected_state: str,
    reason: str,
    *,
    after_request_id: str | None = None,
    not_before_unix: float | None = None,
    stable_cycles: int = DEFAULT_IDLE_STABLE_CYCLES,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    stable_matches = 0
    last_state: dict[str, Any] | None = None

    while time.time() < deadline:
        state = try_read_live_editor_state(project_root)
        if state:
            last_state = state
            age_seconds = heartbeat_age_seconds(state)
            heartbeat_is_fresh = age_seconds is not None and age_seconds <= heartbeat_max_age_seconds
            request_match = (
                after_request_id is None
                or str(state.get("last_processed_request_id") or "") == after_request_id
                or (
                    not_before_unix is not None
                    and parse_utc_timestamp(state.get("last_pump_utc")) is not None
                    and parse_utc_timestamp(state.get("last_pump_utc")) >= not_before_unix
                )
            )
            playmode_state = str(state.get("playmode_state") or "")
            transition_request_id = str(state.get("playmode_transition_request_id") or "")
            transition_phase = str(state.get("playmode_transition_phase") or "")
            transition_contract_applies = after_request_id is not None and transition_request_id == after_request_id
            transition_settled = (not transition_contract_applies) or transition_phase == "settled"

            if heartbeat_is_fresh and request_match and playmode_state == expected_state and transition_settled:
                stable_matches += 1
                if stable_matches >= max(1, stable_cycles):
                    result = dict(state)
                    result["heartbeat_age_seconds"] = round(age_seconds or 0.0, 3)
                    result["playmode_wait_reason"] = reason
                    result["playmode_wait_duration_seconds"] = round(time.time() - started_at, 3)
                    return result
            else:
                stable_matches = 0
        else:
            stable_matches = 0

        time.sleep(0.5)

    request_summary = ""
    if after_request_id:
        request_summary = f" request_id={after_request_id}."

    raise ToolInvocationError(
        "playmode_state_timeout",
        (
            f"Timed out waiting for play mode state '{expected_state}' ({reason})."
            f"{request_summary} {summarize_state_for_error(last_state)}"
        ),
    )


def expected_playmode_state_for_action(action: str) -> str | None:
    normalized = (action or "").strip().lower()
    mapping = {
        "enter": "playing",
        "exit": "edit",
        "pause": "paused",
        "resume": "playing",
    }
    return mapping.get(normalized)
