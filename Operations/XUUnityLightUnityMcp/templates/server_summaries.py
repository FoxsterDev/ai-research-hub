import time
from pathlib import Path
from typing import Any, Callable

from server_bridge_runtime import build_bridge_stabilization_summary


def truncate_text(value: Any, max_length: int = 240) -> str:
    text = str(value or "")
    if len(text) <= max_length:
        return text
    return text[: max(0, max_length - 3)] + "..."


def normalize_scenario_payload(payload: dict[str, Any], scenario_terminal_statuses: set[str]) -> dict[str, Any]:
    normalized = dict(payload)
    status = str(normalized.get("status") or "")
    terminal = status in scenario_terminal_statuses
    normalized["terminal"] = terminal
    normalized["succeeded"] = status == "passed"
    normalized["terminal_status"] = status if terminal else ""
    normalized["terminal_statuses"] = sorted(scenario_terminal_statuses)
    return normalized


def build_status_summary(
    project_root: Path,
    payload: dict[str, Any],
    *,
    read_best_effort_bridge_state: Callable[[Path], dict[str, Any] | None],
    try_read_bridge_state: Callable[[Path], dict[str, Any] | None],
    pid_is_alive: Callable[[int], bool],
    heartbeat_age_seconds: Callable[[dict[str, Any]], float | None],
    derive_busy_reason: Callable[[dict[str, Any] | None], str],
    summarize_state_for_error: Callable[[dict[str, Any] | None], str],
    discovery_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = read_best_effort_bridge_state(project_root) or try_read_bridge_state(project_root) or {}
    effective = dict(state)
    effective.update(payload or {})

    editor_pid = int(effective.get("editor_pid") or 0)
    editor_running = bool(payload.get("editor_running", editor_pid > 0))
    if editor_pid > 0:
        editor_running = editor_running and pid_is_alive(editor_pid)

    heartbeat_age = heartbeat_age_seconds(effective)
    busy_reason = derive_busy_reason(effective)
    summary = {
        "action": "unity_status_summary",
        "project_root": str(project_root),
        "editor_running": editor_running,
        "editor_pid": editor_pid,
        "mcp_reachable": bool(payload.get("mcp_reachable", True)),
        "health_status": str(effective.get("health_status") or "unknown"),
        "transport": str(effective.get("transport") or effective.get("transport_requested") or ""),
        "transport_listener_state": str(effective.get("transport_listener_state") or ""),
        "bridge_generation": int(effective.get("bridge_generation") or 0),
        "bridge_session_id": str(effective.get("bridge_session_id") or ""),
        "playmode_state": str(effective.get("playmode_state") or ""),
        "busy_reason": busy_reason,
        "busy_reason_detail": truncate_text(effective.get("busy_reason_detail") or ""),
        "pending_request_count": int(effective.get("pending_request_count") or 0),
        "active_operation": str(effective.get("active_operation") or ""),
        "last_completed_operation": str(effective.get("last_completed_operation") or ""),
        "last_completed_operation_status": str(effective.get("last_completed_operation_status") or ""),
        "last_completed_operation_duration_seconds": round(float(effective.get("last_completed_operation_duration_seconds") or 0.0), 3),
        "heartbeat_age_seconds": None if heartbeat_age is None else round(heartbeat_age, 3),
        "request_journal_head": str(effective.get("request_journal_head") or ""),
        "state_summary": summarize_state_for_error(effective),
    }
    discovery = dict(discovery_details or {})
    if discovery:
        summary.update(
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
                "transport_state": dict(discovery.get("transport_state") or {}),
                "state_groups": dict(discovery.get("state_groups") or {}),
            }
        )
    summary.update(
        build_bridge_stabilization_summary(
            effective,
            editor_running=editor_running,
            mcp_reachable=bool(payload.get("mcp_reachable", True)),
        )
    )
    return summary


def summarize_scenario_step(step: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(step, dict):
        return None

    summary = {
        "step_id": str(step.get("stepId") or ""),
        "kind": str(step.get("kind") or ""),
        "status": str(step.get("status") or ""),
        "outcome": str(step.get("outcome") or ""),
        "duration_seconds": round(float(step.get("duration_seconds") or 0.0), 3),
    }

    error_code = str(step.get("error_code") or "")
    error_message = str(step.get("error_message") or "")
    if error_code:
        summary["error_code"] = error_code
    if error_message:
        summary["error_message"] = truncate_text(error_message, 320)
    return summary


def build_scenario_result_summary(payload: dict[str, Any], scenario_terminal_statuses: set[str]) -> dict[str, Any]:
    normalized = normalize_scenario_payload(payload, scenario_terminal_statuses)
    steps = normalized.get("steps")
    step_items = steps if isinstance(steps, list) else []

    first_failed_step = None
    last_completed_step = None
    active_step = None
    current_step_index = int(normalized.get("current_step_index") or -1)

    for index, raw_step in enumerate(step_items):
        if not isinstance(raw_step, dict):
            continue

        status = str(raw_step.get("status") or "")
        if first_failed_step is None and status == "failed":
            first_failed_step = summarize_scenario_step(raw_step)
        if status not in {"pending", ""}:
            last_completed_step = summarize_scenario_step(raw_step)
        if index == current_step_index:
            active_step = summarize_scenario_step(raw_step)

    summary = {
        "action": "unity_scenario_result_summary",
        "project_root": str(normalized.get("project_root") or ""),
        "run_id": str(normalized.get("run_id") or ""),
        "scenario_name": str(normalized.get("scenario_name") or ""),
        "status": str(normalized.get("status") or ""),
        "terminal": bool(normalized.get("terminal")),
        "succeeded": bool(normalized.get("succeeded")),
        "terminal_status": str(normalized.get("terminal_status") or ""),
        "started_at_utc": str(normalized.get("started_at_utc") or ""),
        "updated_at_utc": str(normalized.get("updated_at_utc") or ""),
        "completed_at_utc": str(normalized.get("completed_at_utc") or ""),
        "duration_seconds": round(float(normalized.get("duration_seconds") or 0.0), 3),
        "total_steps": int(normalized.get("total_steps") or 0),
        "passed_steps": int(normalized.get("passed_steps") or 0),
        "failed_steps": int(normalized.get("failed_steps") or 0),
        "skipped_steps": int(normalized.get("skipped_steps") or 0),
        "current_step_index": current_step_index,
        "result_path": str(normalized.get("result_path") or ""),
        "active_step": active_step,
        "last_completed_step": last_completed_step,
        "first_failed_step": first_failed_step,
    }

    if "recommended_next_action" in normalized:
        summary["recommended_next_action"] = str(normalized.get("recommended_next_action") or "")
    if "waited_for_terminal_state" in normalized:
        summary["waited_for_terminal_state"] = bool(normalized.get("waited_for_terminal_state"))
    if "wait_duration_seconds" in normalized:
        summary["wait_duration_seconds"] = round(float(normalized.get("wait_duration_seconds") or 0.0), 3)
    if "recovery_attempt_count" in normalized:
        summary["recovery_attempt_count"] = int(normalized.get("recovery_attempt_count") or 0)
    if "offline_error_code" in normalized:
        summary["offline_error_code"] = str(normalized.get("offline_error_code") or "")
    if "offline_error_message" in normalized:
        summary["offline_error_message"] = truncate_text(normalized.get("offline_error_message") or "", 320)

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
    ):
        if key in normalized:
            summary[key] = str(normalized.get(key) or "")

    for key in ("detected_editor_count",):
        if key in normalized:
            summary[key] = int(normalized.get(key) or 0)

    for key in ("host_health_heartbeat_age_seconds",):
        if key in normalized:
            summary[key] = normalized.get(key)

    if "detected_editor_pids" in normalized:
        summary["detected_editor_pids"] = list(normalized.get("detected_editor_pids") or [])
    if "host_health_progress_evidence" in normalized:
        summary["host_health_progress_evidence"] = list(normalized.get("host_health_progress_evidence") or [])
    if "editor_log_diagnosis" in normalized:
        summary["editor_log_diagnosis"] = dict(normalized.get("editor_log_diagnosis") or {})
    if "transport_state" in normalized:
        summary["transport_state"] = dict(normalized.get("transport_state") or {})
    if "state_groups" in normalized:
        summary["state_groups"] = dict(normalized.get("state_groups") or {})

    error = normalized.get("error")
    if isinstance(error, dict):
        summary["error"] = {
            "code": str(error.get("code") or ""),
            "message": truncate_text(error.get("message") or "", 320),
        }

    return summary

def list_files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


def try_read_json_dict(path: Path, read_json: Callable[[Path], Any]) -> dict[str, Any] | None:
    try:
        payload = read_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def summarize_prune_group(
    *,
    name: str,
    paths: list[Path],
    keep_latest: int,
    max_age_hours: int,
    dry_run: bool,
    protected_paths: set[Path] | None = None,
) -> dict[str, Any]:
    protected_paths = protected_paths or set()
    now = time.time()
    cutoff = now - (max_age_hours * 3600.0)
    ranked_paths = sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)

    removed_files = 0
    removed_bytes = 0
    kept_files = 0

    for index, path in enumerate(ranked_paths):
        try:
            stat_result = path.stat()
        except OSError:
            continue

        resolved_path = path.resolve()
        if resolved_path in protected_paths:
            kept_files += 1
            continue

        if index < keep_latest or stat_result.st_mtime >= cutoff:
            kept_files += 1
            continue

        removed_files += 1
        removed_bytes += stat_result.st_size
        if dry_run:
            continue
        try:
            path.unlink()
        except OSError:
            kept_files += 1
            removed_files -= 1
            removed_bytes -= stat_result.st_size

    return {
        "name": name,
        "total_files": len(ranked_paths),
        "kept_files": kept_files,
        "removed_files": removed_files,
        "removed_bytes": removed_bytes,
        "keep_latest": keep_latest,
        "max_age_hours": max_age_hours,
        "dry_run": dry_run,
    }


def read_active_scenario_result_path(
    project_root: Path,
    *,
    active_scenario_run_path: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
) -> Path | None:
    state_path = active_scenario_run_path(project_root)
    if not state_path.is_file():
        return None

    payload = try_read_json_dict(state_path, read_json) or {}
    result_path_value = str(payload.get("resultPath") or payload.get("result_path") or "")
    if not result_path_value:
        return None

    try:
        return Path(result_path_value).expanduser().resolve()
    except OSError:
        return None


def categorize_scenario_result(path: Path, read_json: Callable[[Path], Any]) -> str:
    payload = try_read_json_dict(path, read_json) or {}
    status = str(payload.get("status") or "")
    if status == "passed":
        return "success"
    if status == "failed":
        return "failure"
    return "running"


def prune_project_artifacts(
    project_root: Path,
    arguments: dict[str, Any],
    *,
    bridge_root: Callable[[Path], Path],
    request_journal_dir: Callable[[Path], Path],
    scenario_results_dir: Callable[[Path], Path],
    active_scenario_run_path: Callable[[Path], Path],
    captures_dir: Callable[[Path], Path],
    logs_dir: Callable[[Path], Path],
    default_editor_log_path: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
) -> dict[str, Any]:
    dry_run = bool(arguments.get("dryRun", False))
    categories: list[dict[str, Any]] = []

    categories.append(
        summarize_prune_group(
            name="request_journal",
            paths=list_files_under(request_journal_dir(project_root)),
            keep_latest=max(0, int(arguments.get("requestJournalKeepLatest", 200))),
            max_age_hours=max(1, int(arguments.get("requestJournalMaxAgeHours", 72))),
            dry_run=dry_run,
        )
    )

    active_result_path = read_active_scenario_result_path(
        project_root,
        active_scenario_run_path=active_scenario_run_path,
        read_json=read_json,
    )
    protected_paths = {active_result_path} if active_result_path else set()
    scenario_groups = {
        "success": [],
        "failure": [],
        "running": [],
    }
    for path in list_files_under(scenario_results_dir(project_root)):
        category = categorize_scenario_result(path, read_json)
        scenario_groups.setdefault(category, []).append(path)

    categories.append(
        summarize_prune_group(
            name="scenario_results_success",
            paths=scenario_groups.get("success", []),
            keep_latest=max(0, int(arguments.get("scenarioKeepLatestSuccess", 20))),
            max_age_hours=max(1, int(arguments.get("scenarioSuccessMaxAgeHours", 168))),
            dry_run=dry_run,
            protected_paths=protected_paths,
        )
    )
    categories.append(
        summarize_prune_group(
            name="scenario_results_failure",
            paths=scenario_groups.get("failure", []),
            keep_latest=max(0, int(arguments.get("scenarioKeepLatestFailure", 50))),
            max_age_hours=max(1, int(arguments.get("scenarioFailureMaxAgeHours", 336))),
            dry_run=dry_run,
            protected_paths=protected_paths,
        )
    )
    categories.append(
        summarize_prune_group(
            name="scenario_results_running",
            paths=scenario_groups.get("running", []),
            keep_latest=max(0, int(arguments.get("scenarioKeepLatestRunning", 20))),
            max_age_hours=max(1, int(arguments.get("scenarioRunningMaxAgeHours", 168))),
            dry_run=dry_run,
            protected_paths=protected_paths,
        )
    )

    categories.append(
        summarize_prune_group(
            name="captures",
            paths=list_files_under(captures_dir(project_root)),
            keep_latest=max(0, int(arguments.get("capturesKeepLatest", 20))),
            max_age_hours=max(1, int(arguments.get("capturesMaxAgeHours", 168))),
            dry_run=dry_run,
        )
    )

    if bool(arguments.get("pruneLogs", False)):
        protected_log_paths = {default_editor_log_path(project_root).resolve()} if default_editor_log_path(project_root).exists() else set()
        categories.append(
            summarize_prune_group(
                name="logs",
                paths=list_files_under(logs_dir(project_root)),
                keep_latest=max(0, int(arguments.get("logsKeepLatest", 10))),
                max_age_hours=max(1, int(arguments.get("logsMaxAgeHours", 168))),
                dry_run=dry_run,
                protected_paths=protected_log_paths,
            )
        )

    removed_file_count = sum(int(category.get("removed_files") or 0) for category in categories)
    removed_bytes = sum(int(category.get("removed_bytes") or 0) for category in categories)
    kept_file_count = sum(int(category.get("kept_files") or 0) for category in categories)
    total_file_count = sum(int(category.get("total_files") or 0) for category in categories)

    return {
        "action": "unity_maintenance_prune",
        "project_root": str(project_root),
        "bridge_root": str(bridge_root(project_root)),
        "dry_run": dry_run,
        "active_scenario_result_protected": active_result_path is not None,
        "active_scenario_result_path": str(active_result_path) if active_result_path else "",
        "total_file_count": total_file_count,
        "kept_file_count": kept_file_count,
        "removed_file_count": removed_file_count,
        "removed_bytes": removed_bytes,
        "categories": categories,
    }
