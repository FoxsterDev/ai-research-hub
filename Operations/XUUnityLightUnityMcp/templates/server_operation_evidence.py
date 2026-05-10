import calendar
import json
import time
from pathlib import Path
from typing import Any


ARTIFACT_GROUP_NAMES = (
    "request_journal",
    "logs",
    "captures",
    "scenario_results",
    "compile_outputs",
    "test_outputs",
)


def parse_utc_timestamp(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        return float(calendar.timegm(time.strptime(text, "%Y-%m-%dT%H:%M:%SZ")))
    except ValueError:
        return None


def _normalize_path(project_root: Path, path_value: Any) -> Path | None:
    text = str(path_value or "").strip()
    if not text:
        return None

    path = Path(text).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _empty_artifact_groups() -> dict[str, list[dict[str, Any]]]:
    return {group_name: [] for group_name in ARTIFACT_GROUP_NAMES}


def _add_artifact(
    groups: dict[str, list[dict[str, Any]]],
    seen: set[tuple[str, str, str, str]],
    *,
    project_root: Path,
    group_name: str,
    kind: str,
    path_value: Any,
    step_id: str = "",
) -> None:
    normalized_path = _normalize_path(project_root, path_value)
    if normalized_path is None:
        return

    path_text = str(normalized_path)
    dedupe_key = (group_name, kind, path_text, step_id)
    if dedupe_key in seen:
        return
    seen.add(dedupe_key)

    item: dict[str, Any] = {
        "kind": kind,
        "path": path_text,
        "exists": normalized_path.exists(),
    }
    if item["exists"]:
        item["path_type"] = "directory" if normalized_path.is_dir() else "file"
    if step_id:
        item["step_id"] = step_id
    groups[group_name].append(item)


def _try_parse_json_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _collect_payload_artifacts(
    payload: dict[str, Any] | None,
    *,
    project_root: Path,
    groups: dict[str, list[dict[str, Any]]],
    seen: set[tuple[str, str, str, str]],
    step_id: str = "",
) -> None:
    if not isinstance(payload, dict):
        return

    capture_source = str(payload.get("capture_source") or "capture")
    _add_artifact(
        groups,
        seen,
        project_root=project_root,
        group_name="captures",
        kind=capture_source,
        path_value=payload.get("file_path"),
        step_id=step_id,
    )
    _add_artifact(
        groups,
        seen,
        project_root=project_root,
        group_name="scenario_results",
        kind="scenario_result",
        path_value=payload.get("result_path"),
        step_id=step_id,
    )

    result_payload = payload.get("result")
    if isinstance(result_payload, dict):
        _add_artifact(
            groups,
            seen,
            project_root=project_root,
            group_name="compile_outputs",
            kind="compile_output_directory",
            path_value=result_payload.get("output_directory"),
            step_id=step_id,
        )

    results_payload = payload.get("results")
    if isinstance(results_payload, list):
        for index, item in enumerate(results_payload):
            if not isinstance(item, dict):
                continue
            nested_step_id = step_id or f"result_{index}"
            _add_artifact(
                groups,
                seen,
                project_root=project_root,
                group_name="compile_outputs",
                kind="compile_output_directory",
                path_value=item.get("output_directory"),
                step_id=nested_step_id,
            )

    steps_payload = payload.get("steps")
    if isinstance(steps_payload, list):
        for index, step in enumerate(steps_payload):
            if not isinstance(step, dict):
                continue
            nested_payload = _try_parse_json_dict(step.get("payload_json"))
            nested_step_id = str(step.get("stepId") or f"step_{index}")
            _collect_payload_artifacts(
                nested_payload,
                project_root=project_root,
                groups=groups,
                seen=seen,
                step_id=nested_step_id,
            )


def build_artifact_manifest(
    *,
    project_root: Path,
    operation: str,
    request_id: str,
    payload: dict[str, Any] | None,
    editor_log_path: Path | None,
    journal_event_paths: list[str] | None,
) -> dict[str, Any]:
    groups = _empty_artifact_groups()
    seen: set[tuple[str, str, str, str]] = set()

    if isinstance(journal_event_paths, list):
        for path_text in journal_event_paths:
            _add_artifact(
                groups,
                seen,
                project_root=project_root,
                group_name="request_journal",
                kind="request_journal_event",
                path_value=path_text,
            )

    if editor_log_path is not None:
        _add_artifact(
            groups,
            seen,
            project_root=project_root,
            group_name="logs",
            kind="editor_log",
            path_value=editor_log_path,
        )

    _collect_payload_artifacts(
        payload,
        project_root=project_root,
        groups=groups,
        seen=seen,
    )

    artifact_count = sum(len(items) for items in groups.values())
    existing_artifact_count = sum(1 for items in groups.values() for item in items if bool(item.get("exists")))
    return {
        "operation": operation,
        "request_id": request_id,
        "artifact_count": artifact_count,
        "existing_artifact_count": existing_artifact_count,
        "groups": groups,
    }


def _resolve_duration_seconds(
    payload: dict[str, Any] | None,
    *,
    started_at_utc: str,
    completed_at_utc: str,
    host_started_unix: float | None,
    host_completed_unix: float | None,
) -> float | None:
    if isinstance(payload, dict):
        raw_value = payload.get("duration_seconds")
        if isinstance(raw_value, (int, float)):
            return round(float(raw_value), 3)

    started_unix = parse_utc_timestamp(started_at_utc)
    completed_unix = parse_utc_timestamp(completed_at_utc)
    if started_unix is not None and completed_unix is not None and completed_unix >= started_unix:
        return round(completed_unix - started_unix, 3)

    if host_started_unix is not None and host_completed_unix is not None and host_completed_unix >= host_started_unix:
        return round(host_completed_unix - host_started_unix, 3)

    return None


def _resolve_settle_timestamp(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("settled_at_utc") or "")


def _resolve_host_wait_duration_seconds(lifecycle: dict[str, Any] | None) -> float | None:
    if not isinstance(lifecycle, dict):
        return None

    for field_name in ("playmode_wait_after", "idle_wait_after"):
        field_value = lifecycle.get(field_name)
        if not isinstance(field_value, dict):
            continue
        for duration_field in ("playmode_wait_duration_seconds", "idle_wait_duration_seconds"):
            raw_value = field_value.get(duration_field)
            if isinstance(raw_value, (int, float)):
                return round(float(raw_value), 3)
    return None


def build_structured_timing(
    *,
    operation: str,
    request_id: str,
    payload: dict[str, Any] | None,
    request_submitted_at_utc: str,
    request_started_at_utc: str,
    request_completed_at_utc: str,
    response_completed_at_utc: str,
    lifecycle: dict[str, Any] | None,
    host_started_unix: float | None,
    host_completed_unix: float | None,
) -> dict[str, Any]:
    started_at_utc = str(request_started_at_utc or (payload or {}).get("started_at_utc") or "")
    completed_at_utc = str(
        request_completed_at_utc
        or (payload or {}).get("completed_at_utc")
        or (payload or {}).get("request_completed_at_utc")
        or response_completed_at_utc
        or ""
    )
    settled_at_utc = _resolve_settle_timestamp(payload)
    duration_seconds = _resolve_duration_seconds(
        payload,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        host_started_unix=host_started_unix,
        host_completed_unix=host_completed_unix,
    )

    settled_unix = parse_utc_timestamp(settled_at_utc)
    completed_unix = parse_utc_timestamp(completed_at_utc)
    settle_duration_seconds = None
    if settled_unix is not None and completed_unix is not None and settled_unix >= completed_unix:
        settle_duration_seconds = round(settled_unix - completed_unix, 3)

    host_round_trip_seconds = None
    if host_started_unix is not None and host_completed_unix is not None and host_completed_unix >= host_started_unix:
        host_round_trip_seconds = round(host_completed_unix - host_started_unix, 3)

    return {
        "operation": operation,
        "request_id": request_id,
        "request_submitted_at_utc": str(request_submitted_at_utc or ""),
        "request_started_at_utc": started_at_utc,
        "request_completed_at_utc": completed_at_utc,
        "settled_at_utc": settled_at_utc,
        "duration_seconds": duration_seconds,
        "settle_duration_seconds": settle_duration_seconds,
        "host_round_trip_seconds": host_round_trip_seconds,
        "host_wait_duration_seconds": _resolve_host_wait_duration_seconds(lifecycle),
    }


def attach_operation_evidence_to_payload(
    payload: dict[str, Any] | None,
    *,
    project_root: Path,
    operation: str,
    request_id: str,
    request_submitted_at_utc: str,
    request_started_at_utc: str,
    request_completed_at_utc: str,
    response_completed_at_utc: str,
    editor_log_path: Path | None,
    journal_event_paths: list[str] | None,
    lifecycle: dict[str, Any] | None,
    host_started_unix: float | None,
    host_completed_unix: float | None,
) -> dict[str, Any]:
    enriched = dict(payload or {})
    enriched["structured_timing"] = build_structured_timing(
        operation=operation,
        request_id=request_id,
        payload=enriched,
        request_submitted_at_utc=request_submitted_at_utc,
        request_started_at_utc=request_started_at_utc,
        request_completed_at_utc=request_completed_at_utc,
        response_completed_at_utc=response_completed_at_utc,
        lifecycle=lifecycle,
        host_started_unix=host_started_unix,
        host_completed_unix=host_completed_unix,
    )
    enriched["artifact_manifest"] = build_artifact_manifest(
        project_root=project_root,
        operation=operation,
        request_id=request_id,
        payload=enriched,
        editor_log_path=editor_log_path,
        journal_event_paths=journal_event_paths,
    )
    return enriched


def attach_operation_evidence_to_final_status(
    summary: dict[str, Any],
    *,
    project_root: Path,
    payload: dict[str, Any] | None,
    editor_log_path: Path | None,
) -> dict[str, Any]:
    enriched = dict(summary or {})
    operation = str(enriched.get("operation") or "")
    request_id = str(enriched.get("request_id") or "")
    journal_event_paths = list(enriched.get("journal_event_paths") or [])
    enriched["structured_timing"] = build_structured_timing(
        operation=operation,
        request_id=request_id,
        payload=payload,
        request_submitted_at_utc=str(enriched.get("request_submitted_at_utc") or ""),
        request_started_at_utc=str(enriched.get("request_started_at_utc") or ""),
        request_completed_at_utc=str(enriched.get("request_completed_at_utc") or ""),
        response_completed_at_utc="",
        lifecycle=None,
        host_started_unix=None,
        host_completed_unix=None,
    )
    enriched["artifact_manifest"] = build_artifact_manifest(
        project_root=project_root,
        operation=operation,
        request_id=request_id,
        payload=payload,
        editor_log_path=editor_log_path,
        journal_event_paths=journal_event_paths,
    )
    return enriched


def attach_persisted_scenario_result_evidence(
    payload: dict[str, Any] | None,
    project_root: Path,
    result_path: Path,
) -> dict[str, Any]:
    enriched = dict(payload or {})
    enriched["result_path"] = str(enriched.get("result_path") or result_path)
    enriched["structured_timing"] = build_structured_timing(
        operation="unity.scenario.result.persisted",
        request_id="",
        payload=enriched,
        request_submitted_at_utc="",
        request_started_at_utc=str(enriched.get("started_at_utc") or ""),
        request_completed_at_utc=str(enriched.get("completed_at_utc") or ""),
        response_completed_at_utc=str(enriched.get("completed_at_utc") or ""),
        lifecycle=None,
        host_started_unix=None,
        host_completed_unix=None,
    )
    enriched["artifact_manifest"] = build_artifact_manifest(
        project_root=project_root,
        operation="unity.scenario.result.persisted",
        request_id="",
        payload=enriched,
        editor_log_path=None,
        journal_event_paths=[],
    )
    return enriched
