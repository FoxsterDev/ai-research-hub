from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def _parse_sort_timestamp(value: Any, *, parse_utc_timestamp: Callable[[Any], float | None]) -> float:
    parsed = parse_utc_timestamp(value)
    return parsed if parsed is not None else 0.0


def read_persisted_scenario_result_payload(
    path: Path,
    *,
    read_json: Callable[[Path], Any],
) -> dict[str, Any] | None:
    try:
        payload = read_json(path)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def enrich_persisted_scenario_result_payload(
    project_root: Path,
    path: Path,
    payload: dict[str, Any],
    *,
    attach_persisted_scenario_result_evidence: Callable[[dict[str, Any], Path, Path], dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(payload or {})
    normalized.setdefault("project_root", str(project_root))
    normalized["result_path"] = str(normalized.get("result_path") or path.resolve())
    return attach_persisted_scenario_result_evidence(normalized, project_root, path.resolve())


def build_persisted_scenario_result_summary(
    project_root: Path,
    path: Path,
    payload: dict[str, Any],
    *,
    attach_persisted_scenario_result_evidence: Callable[[dict[str, Any], Path, Path], dict[str, Any]],
    build_scenario_result_summary: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    scenario_terminal_statuses: set[str],
) -> dict[str, Any]:
    summary = build_scenario_result_summary(
        enrich_persisted_scenario_result_payload(
            project_root,
            path,
            payload,
            attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
        ),
        scenario_terminal_statuses,
    )
    summary["result_path"] = str(summary.get("result_path") or path.resolve())
    return summary


def _scenario_matches(payload: dict[str, Any], scenario_name: str) -> bool:
    if not scenario_name:
        return True
    candidate = str(payload.get("scenario_name") or "").strip()
    return candidate.lower() == scenario_name.strip().lower()


def _run_id_matches(payload: dict[str, Any], run_id: str) -> bool:
    if not run_id:
        return True
    candidate = str(payload.get("run_id") or "").strip()
    return candidate == run_id.strip()


def _is_terminal_status(status: Any, scenario_terminal_statuses: set[str]) -> bool:
    return isinstance(status, str) and status in scenario_terminal_statuses


def _result_sort_key(
    path: Path,
    payload: dict[str, Any],
    *,
    parse_utc_timestamp: Callable[[Any], float | None],
) -> tuple[float, str]:
    return (
        max(
            _parse_sort_timestamp(payload.get("completed_at_utc"), parse_utc_timestamp=parse_utc_timestamp),
            _parse_sort_timestamp(payload.get("updated_at_utc"), parse_utc_timestamp=parse_utc_timestamp),
            _parse_sort_timestamp(payload.get("started_at_utc"), parse_utc_timestamp=parse_utc_timestamp),
            path.stat().st_mtime,
        ),
        path.name,
    )


def list_persisted_scenario_result_summaries(
    project_root: Path,
    *,
    scenario_results_dir: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
    parse_utc_timestamp: Callable[[Any], float | None],
    attach_persisted_scenario_result_evidence: Callable[[dict[str, Any], Path, Path], dict[str, Any]],
    build_scenario_result_summary: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    scenario_terminal_statuses: set[str],
    scenario_name: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    root = scenario_results_dir(project_root)
    matched: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        payload = read_persisted_scenario_result_payload(path, read_json=read_json)
        if payload is None or not _scenario_matches(payload, scenario_name):
            continue
        matched.append((path.resolve(), payload))

    matched.sort(
        key=lambda item: _result_sort_key(item[0], item[1], parse_utc_timestamp=parse_utc_timestamp),
        reverse=True,
    )

    bounded_limit = max(1, int(limit or 20))
    results = [
        build_persisted_scenario_result_summary(
            project_root,
            path,
            payload,
            attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
            build_scenario_result_summary=build_scenario_result_summary,
            scenario_terminal_statuses=scenario_terminal_statuses,
        )
        for path, payload in matched[:bounded_limit]
    ]
    return {
        "action": "unity_scenario_results_list",
        "project_root": str(project_root),
        "scenario_name_filter": str(scenario_name or ""),
        "results_root": str(root.resolve()),
        "lookup_found": bool(results),
        "total_results": len(matched),
        "returned_results": len(results),
        "results": results,
    }


def latest_persisted_scenario_result_summary(
    project_root: Path,
    *,
    scenario_results_dir: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
    parse_utc_timestamp: Callable[[Any], float | None],
    attach_persisted_scenario_result_evidence: Callable[[dict[str, Any], Path, Path], dict[str, Any]],
    build_scenario_result_summary: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    scenario_terminal_statuses: set[str],
    scenario_name: str = "",
) -> dict[str, Any]:
    listing = list_persisted_scenario_result_summaries(
        project_root,
        scenario_results_dir=scenario_results_dir,
        read_json=read_json,
        parse_utc_timestamp=parse_utc_timestamp,
        attach_persisted_scenario_result_evidence=attach_persisted_scenario_result_evidence,
        build_scenario_result_summary=build_scenario_result_summary,
        scenario_terminal_statuses=scenario_terminal_statuses,
        scenario_name=scenario_name,
        limit=1,
    )
    results = list(listing.get("results") or [])
    if not results:
        return {
            "action": "unity_scenario_result_latest",
            "project_root": str(project_root),
            "scenario_name_filter": str(scenario_name or ""),
            "results_root": str(listing.get("results_root") or scenario_results_dir(project_root).resolve()),
            "lookup_found": False,
            "total_results": int(listing.get("total_results") or 0),
            "run_id": "",
            "status": "",
            "started_at_utc": "",
            "completed_at_utc": "",
            "duration_seconds": 0.0,
            "result_path": "",
            "artifact_manifest": {
                "operation": "unity.scenario.result.persisted",
                "request_id": "",
                "artifact_count": 0,
                "existing_artifact_count": 0,
                "groups": {
                    "request_journal": [],
                    "logs": [],
                    "captures": [],
                    "scenario_results": [],
                    "compile_outputs": [],
                    "test_outputs": [],
                },
            },
            "structured_timing": {
                "operation": "unity.scenario.result.persisted",
                "request_id": "",
                "request_submitted_at_utc": "",
                "request_started_at_utc": "",
                "request_completed_at_utc": "",
                "settled_at_utc": "",
                "duration_seconds": 0.0,
                "settle_duration_seconds": None,
                "host_round_trip_seconds": None,
                "host_wait_duration_seconds": None,
            },
        }

    summary = dict(results[0])
    summary["action"] = "unity_scenario_result_latest"
    summary["scenario_name_filter"] = str(scenario_name or "")
    summary["lookup_found"] = True
    summary["results_root"] = str(listing.get("results_root") or "")
    summary["total_results"] = int(listing.get("total_results") or 0)
    return summary


def reconcile_persisted_scenario_result(
    project_root: Path,
    *,
    scenario_results_dir: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
    parse_utc_timestamp: Callable[[Any], float | None],
    scenario_terminal_statuses: set[str],
    run_id: str = "",
    scenario_name: str = "",
) -> dict[str, Any]:
    root = scenario_results_dir(project_root)
    all_results: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        payload = read_persisted_scenario_result_payload(path, read_json=read_json)
        if payload is None:
            continue
        all_results.append((path.resolve(), payload))

    def sorted_matches(matches: list[tuple[Path, dict[str, Any]]]) -> list[tuple[Path, dict[str, Any]]]:
        return sorted(
            matches,
            key=lambda item: _result_sort_key(item[0], item[1], parse_utc_timestamp=parse_utc_timestamp),
            reverse=True,
        )

    lookup_strategy = "none"
    matches: list[tuple[Path, dict[str, Any]]] = []
    if run_id:
        lookup_strategy = "run_id"
        matches = sorted_matches([item for item in all_results if _run_id_matches(item[1], run_id)])
    if not matches and scenario_name:
        lookup_strategy = "scenario_name"
        matches = sorted_matches([item for item in all_results if _scenario_matches(item[1], scenario_name)])

    terminal_matches = [
        item
        for item in matches
        if _is_terminal_status(str(item[1].get("status") or ""), scenario_terminal_statuses)
    ]
    selected = terminal_matches[0] if terminal_matches else (matches[0] if matches else None)
    selected_path = selected[0] if selected else None
    selected_payload = dict(selected[1]) if selected else {}
    selected_status = str(selected_payload.get("status") or "")
    selected_terminal = _is_terminal_status(selected_status, scenario_terminal_statuses)

    if selected_path is not None:
        selected_payload.setdefault("project_root", str(project_root))
        selected_payload["result_path"] = str(selected_payload.get("result_path") or selected_path)

    return {
        "lookup_found": selected is not None,
        "lookup_strategy": lookup_strategy if selected is not None else "none",
        "terminal_result_found": selected_terminal,
        "status": selected_status,
        "result_path": str(selected_path or ""),
        "payload": selected_payload,
        "matched_result_count": len(matches),
        "terminal_result_count": len(terminal_matches),
        "results_root": str(root.resolve()),
    }
