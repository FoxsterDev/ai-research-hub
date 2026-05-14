from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable


TRANSIENT_SCENARIO_POLL_ERROR_CODES = frozenset(
    {
        "transport_not_ready",
        "transport_response_missing",
        "request_lifecycle_reset",
        "response_missing_after_lifecycle_reset",
    }
)


def is_terminal_scenario_status(status: Any, scenario_terminal_statuses: set[str]) -> bool:
    return isinstance(status, str) and status in scenario_terminal_statuses


def wait_for_scenario_result_data(
    project_root: Path,
    run_id: str,
    scenario_name: str,
    timeout_ms: int,
    poll_interval_ms: int,
    *,
    scenario_recovery_error_codes: set[str] | frozenset[str],
    scenario_terminal_statuses: set[str],
    default_heartbeat_max_age_seconds: int,
    try_read_live_editor_state: Callable[[Path], dict[str, Any] | None],
    activate_unity_editor: Callable[[Path], Any],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    recover_project_bridge_for_reconciliation: Callable[..., dict[str, Any]],
    current_project_context_bridge_state: Callable[[Path], dict[str, Any]],
    enrich_tool_invocation_error_with_discovery: Callable[[Path, Any], Exception],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
    normalize_scenario_payload: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    apply_discovery_to_scenario_payload: Callable[[dict[str, Any], Path], dict[str, Any]],
    tool_invocation_error_type: type,
) -> dict[str, Any]:
    started_at = time.time()
    deadline = started_at + (timeout_ms / 1000.0)
    effective_poll_interval = max(0.1, poll_interval_ms / 1000.0)
    last_payload: dict[str, Any] | None = None
    recovery_attempt_count = 0

    while time.time() < deadline:
        live_state = try_read_live_editor_state(project_root)
        if isinstance(live_state, dict) and bool(live_state.get("playmode_transition_pending")):
            target_state = str(live_state.get("playmode_transition_target_state") or "")
            current_state = str(live_state.get("playmode_state") or "")
            if target_state in {"playing", "paused"} and current_state != target_state:
                try:
                    activate_unity_editor(project_root)
                except Exception:
                    pass

        remaining_ms = max(1000, min(5000, int((deadline - time.time()) * 1000)))
        bridge_args: dict[str, Any] = {}
        if run_id:
            bridge_args["runId"] = run_id
        if scenario_name:
            bridge_args["scenarioName"] = scenario_name

        try:
            response = invoke_bridge(str(project_root), "unity.scenario.result", bridge_args, remaining_ms)
        except Exception as exc:
            exc_code = str(getattr(exc, "code", "") or "")
            if exc_code in scenario_recovery_error_codes and time.time() + effective_poll_interval < deadline:
                recovery_attempt_count += 1
                try:
                    recover_project_bridge_for_reconciliation(
                        project_root,
                        timeout_ms=min(remaining_ms, 10000),
                        heartbeat_max_age_seconds=default_heartbeat_max_age_seconds,
                        startup_policy=str(
                            (current_project_context_bridge_state(project_root) or {}).get("startup_policy")
                            or "fail_fast_on_interactive_compile_block"
                        ),
                        allow_open_editor=True,
                    )
                except Exception as recovery_exc:
                    raise enrich_tool_invocation_error_with_discovery(project_root, recovery_exc)
                time.sleep(effective_poll_interval)
                continue
            if exc_code in TRANSIENT_SCENARIO_POLL_ERROR_CODES and time.time() + effective_poll_interval < deadline:
                time.sleep(effective_poll_interval)
                continue
            raise enrich_tool_invocation_error_with_discovery(project_root, exc)

        tool_result = bridge_response_to_tool_result(response)
        if tool_result.get("isError"):
            structured = tool_result.get("structuredContent") or {}
            error = structured.get("error") or {}
            raise tool_invocation_error_type(
                str(error.get("code") or "scenario_result_failed"),
                str(error.get("message") or "Scenario result polling failed."),
            )

        payload = tool_result.get("structuredContent") or {}
        if isinstance(payload, dict):
            payload = normalize_scenario_payload(payload, scenario_terminal_statuses)
        last_payload = payload

        if is_terminal_scenario_status(payload.get("status"), scenario_terminal_statuses):
            payload["waited_for_terminal_state"] = True
            payload["wait_duration_seconds"] = round(time.time() - started_at, 3)
            payload["recovery_attempt_count"] = recovery_attempt_count
            return apply_discovery_to_scenario_payload(payload, project_root)

        time.sleep(effective_poll_interval)

    scenario_label = scenario_name or run_id or "unknown"
    suffix = ""
    if last_payload:
        suffix = f" Last observed status: {last_payload.get('status') or 'unknown'}."
    raise enrich_tool_invocation_error_with_discovery(
        project_root,
        tool_invocation_error_type(
            "scenario_wait_timeout",
            f"Timed out waiting for scenario '{scenario_label}' to reach a terminal state.{suffix}",
            {
                "run_id": run_id,
                "scenario_name": scenario_name,
                "last_observed_status": str((last_payload or {}).get("status") or ""),
                "recovery_attempt_count": recovery_attempt_count,
            },
        ),
    )
