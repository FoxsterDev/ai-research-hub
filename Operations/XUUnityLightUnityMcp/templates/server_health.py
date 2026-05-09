import re
from pathlib import Path
from typing import Any, Callable

FRESH_HEARTBEAT_MAX_AGE_SECONDS = 5.0
STALE_HEARTBEAT_MAX_AGE_SECONDS = 15.0
ANR_SUSPECTED_HEARTBEAT_MAX_AGE_SECONDS = 30.0
DEFAULT_LOG_TAIL_MAX_CHARS = 40000


def truncate_text(value: Any, max_length: int = 240) -> str:
    text = str(value or "")
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 3)] + "..."


def read_editor_log_tail(log_path: Path, max_chars: int = DEFAULT_LOG_TAIL_MAX_CHARS) -> str:
    if not log_path.is_file():
        return ""

    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""

    if len(text) > max_chars:
        return text[-max_chars:]
    return text


def _matching_log_lines(log_text: str, patterns: list[str], limit: int = 3) -> list[str]:
    matches: list[str] = []
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern in line for pattern in patterns):
            matches.append(truncate_text(line, 220))
        if len(matches) >= limit:
            break
    return matches


def build_editor_log_diagnosis(
    log_path: Path,
    *,
    startup_policy: str,
    classify_editor_log: Callable[[str, str], tuple[str, str] | None],
    max_chars: int = DEFAULT_LOG_TAIL_MAX_CHARS,
) -> dict[str, Any]:
    log_text = read_editor_log_tail(log_path, max_chars=max_chars)
    if not log_text:
        return {}

    classified = classify_editor_log(log_text, startup_policy)
    if classified is not None:
        code, summary = classified
        evidence_lines = _matching_log_lines(
            log_text,
            [
                "Project has invalid dependencies:",
                "An error occurred while resolving packages:",
                "Could not clone [",
                "error CS",
            ],
        )
        return {
            "code": code,
            "severity": "error",
            "summary": summary,
            "evidence_lines": evidence_lines,
        }

    runtime_exception_lines = _matching_log_lines(
        log_text,
        [
            "Exception:",
            "NullReferenceException",
            "MissingReferenceException",
            "StackOverflowException",
        ],
    )
    if runtime_exception_lines:
        return {
            "code": "runtime_exception_observed",
            "severity": "warning",
            "summary": "Editor.log contains recent runtime exception markers.",
            "evidence_lines": runtime_exception_lines,
        }

    lifecycle_lines = _matching_log_lines(
        log_text,
        [
            "ReloadAssembly",
            "AssetDatabase: script compilation time:",
            "RefreshInfo:",
            "RefreshV2(",
            "Begin MonoManager ReloadAssembly",
            "Exiting Playmode",
            "Entering Playmode",
        ],
    )
    if lifecycle_lines:
        return {
            "code": "lifecycle_activity_observed",
            "severity": "info",
            "summary": "Editor.log shows recent lifecycle activity consistent with compile/import/playmode churn.",
            "evidence_lines": lifecycle_lines,
        }

    timeout_lines = _matching_log_lines(
        log_text,
        [
            "Timeout",
            "timed out",
            "Transport connect failed",
        ],
    )
    if timeout_lines:
        return {
            "code": "timeout_markers_observed",
            "severity": "warning",
            "summary": "Editor.log contains recent timeout markers.",
            "evidence_lines": timeout_lines,
        }

    last_non_empty_lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    evidence_lines = [truncate_text(line, 220) for line in last_non_empty_lines[-3:]]
    return {
        "code": "log_tail_present_no_known_blocker",
        "severity": "info",
        "summary": "Editor.log is present, but no known startup blocker marker was identified in the recent tail.",
        "evidence_lines": evidence_lines,
    }


def _collect_progress_evidence(
    bridge_state: dict[str, Any],
    *,
    busy_reason: str,
    editor_log_diagnosis: dict[str, Any],
) -> list[str]:
    evidence: list[str] = []

    if str(bridge_state.get("active_operation") or ""):
        evidence.append("active_operation")
    if int(bridge_state.get("pending_request_count") or 0) > 0:
        evidence.append("pending_request_count")
    if str(bridge_state.get("last_processed_request_id") or ""):
        evidence.append("last_processed_request_id")
    if str(bridge_state.get("request_journal_head") or ""):
        evidence.append("request_journal_head")
    if bool(bridge_state.get("domain_reload_in_progress")):
        evidence.append("domain_reload_in_progress")
    if bool(bridge_state.get("package_operation_in_progress")):
        evidence.append("package_operation_in_progress")
    if bool(bridge_state.get("refresh_settle_pending")):
        evidence.append("refresh_settle_pending")
    if bool(bridge_state.get("compile_settle_pending")):
        evidence.append("compile_settle_pending")
    if bool(bridge_state.get("playmode_transition_pending")):
        evidence.append("playmode_transition_pending")
    if bool(bridge_state.get("is_compiling")):
        evidence.append("is_compiling")
    if bool(bridge_state.get("is_updating")):
        evidence.append("is_updating")
    if busy_reason not in {"", "idle", "bridge_state_missing"}:
        evidence.append(f"busy_reason:{busy_reason}")

    log_code = str(editor_log_diagnosis.get("code") or "")
    if log_code == "lifecycle_activity_observed":
        evidence.append("editor_log_lifecycle_activity")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def classify_project_health(
    *,
    bridge_state: dict[str, Any],
    discovery: dict[str, Any],
    editor_log_diagnosis: dict[str, Any],
    heartbeat_age_seconds: Callable[[dict[str, Any]], float | None],
    derive_busy_reason: Callable[[dict[str, Any] | None], str],
) -> dict[str, Any]:
    bridge_state_live = bool(discovery.get("bridge_state_live"))
    host_session_live = bool(discovery.get("host_session_live"))
    bridge_enabled = bool(discovery.get("bridge_enabled"))
    detected_editor_count = int(discovery.get("detected_editor_count") or 0)
    bridge_pid_alive = bool(discovery.get("bridge_pid_alive"))
    host_session_pid_alive = bool(discovery.get("host_session_pid_alive"))
    live_editor_present = bool(
        bridge_state_live
        or host_session_live
        or detected_editor_count > 0
        or bridge_pid_alive
        or host_session_pid_alive
    )

    heartbeat_age = heartbeat_age_seconds(bridge_state) if bridge_state else None
    busy_reason = derive_busy_reason(bridge_state if bridge_state else None)
    progress_evidence = _collect_progress_evidence(
        bridge_state if isinstance(bridge_state, dict) else {},
        busy_reason=busy_reason,
        editor_log_diagnosis=editor_log_diagnosis,
    )
    has_progress_evidence = bool(progress_evidence)

    classification = "offline"
    reason = "no_live_editor_process"
    recommended_next_action = str(discovery.get("reconciliation_recommended_next_action") or "open_editor_or_ensure_ready")
    termination_policy = "observe_only"
    anr_classification = "none"

    if not bridge_enabled and not live_editor_present:
        classification = "bridge_disabled"
        reason = "bridge_disabled_in_project_config"
        recommended_next_action = "enable_bridge_and_retry"
    elif not live_editor_present:
        classification = "offline"
        if str(discovery.get("discovery_classification") or "") == "stale_state":
            reason = "stale_state_without_live_editor"
        else:
            reason = "no_live_editor_process"
    elif not bridge_state_live:
        classification = "stale"
        if host_session_live or detected_editor_count > 0:
            reason = "live_editor_without_live_bridge_state"
        else:
            reason = "bridge_state_not_live"
    else:
        if heartbeat_age is None:
            classification = "stale"
            reason = "live_bridge_state_without_heartbeat_timestamp"
        elif heartbeat_age < FRESH_HEARTBEAT_MAX_AGE_SECONDS:
            classification = "fresh"
            reason = "heartbeat_fresh"
            recommended_next_action = "none"
        elif heartbeat_age < STALE_HEARTBEAT_MAX_AGE_SECONDS:
            classification = "stale"
            reason = "heartbeat_stale_but_not_anr_threshold"
        elif heartbeat_age < ANR_SUSPECTED_HEARTBEAT_MAX_AGE_SECONDS:
            if has_progress_evidence:
                classification = "stale"
                reason = "lifecycle_churn_with_progress_evidence"
            else:
                classification = "anr_suspected"
                reason = "heartbeat_stale_without_progress_evidence"
                recommended_next_action = "inspect_editor_log_and_observe"
                anr_classification = "anr_suspected"
        else:
            if has_progress_evidence:
                classification = "stale"
                reason = "prolonged_lifecycle_churn_with_progress_evidence"
            else:
                classification = "anr"
                reason = "live_editor_without_progress_evidence"
                recommended_next_action = "inspect_editor_log_and_consider_graceful_restart"
                termination_policy = "graceful_terminate"
                anr_classification = "anr"

    if editor_log_diagnosis and classification in {"stale", "anr_suspected", "anr"}:
        diagnosis_code = str(editor_log_diagnosis.get("code") or "")
        if diagnosis_code in {
            "package_resolution_failed",
            "interactive_compile_block_detected",
            "safe_mode_manual_required",
        }:
            reason = f"{reason}_with_log_blocker"
            recommended_next_action = "inspect_editor_log"
            termination_policy = "observe_only"
            if classification == "anr":
                classification = "stale"
                anr_classification = "none"

    return {
        "host_health_classification": classification,
        "host_health_reason": reason,
        "host_health_recommended_next_action": recommended_next_action,
        "host_health_termination_policy": termination_policy,
        "host_health_heartbeat_age_seconds": None if heartbeat_age is None else round(float(heartbeat_age), 3),
        "host_health_busy_reason": busy_reason,
        "host_health_progress_evidence": progress_evidence,
        "anr_classification": anr_classification,
        "editor_log_diagnosis": dict(editor_log_diagnosis or {}),
    }
