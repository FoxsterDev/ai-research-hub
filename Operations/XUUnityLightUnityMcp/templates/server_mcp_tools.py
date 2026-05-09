import json
from pathlib import Path
from typing import Any, Callable

from server_mcp_protocol import JsonRpcError


def tool_error_result(
    exc: Exception,
    *,
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
) -> dict[str, Any]:
    payload = build_tool_error_payload(exc)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=True),
            }
        ],
        "structuredContent": payload,
        "isError": True,
    }


def call_unity_compile_build_config_matrix_tool(
    arguments: dict[str, Any],
    *,
    tool_invocation_error_type: type[Exception],
    ensure_project_root: Callable[[str], Path],
    resolve_operation_timeout_ms: Callable[[Path, str, Any, int], int],
    build_compile_matrix_args_from_build_config: Callable[..., dict[str, Any]],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
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
            tool_error_type=tool_invocation_error_type,
        )
        response = invoke_bridge(
            str(project_root),
            "unity.compile.matrix",
            compile_plan["matrixArgs"],
            timeout_ms,
        )
    except tool_invocation_error_type as exc:
        return tool_error_result(exc, build_tool_error_payload=build_tool_error_payload)

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
                "text": json.dumps(structured, ensure_ascii=True),
            }
        ]
    return tool_result


def call_unity_scenario_run_and_wait_tool(
    arguments: dict[str, Any],
    *,
    tool_invocation_error_type: type[Exception],
    ensure_project_root: Callable[[str], Path],
    resolve_operation_timeout_ms: Callable[[Path, str, Any, int], int],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
    wait_for_scenario_result: Callable[..., dict[str, Any]],
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
    scenario_failure_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
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
    except tool_invocation_error_type as exc:
        return tool_error_result(exc, build_tool_error_payload=build_tool_error_payload)

    result_payload["run_start"] = run_payload
    if not bool(result_payload.get("succeeded")):
        return scenario_failure_tool_result(result_payload)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result_payload, ensure_ascii=True),
            }
        ],
        "structuredContent": result_payload,
        "isError": False,
    }


def call_unity_status_summary_tool(
    arguments: dict[str, Any],
    *,
    tool_invocation_error_type: type[Exception],
    ensure_project_root: Callable[[str], Path],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
    build_status_summary: Callable[..., dict[str, Any]],
    read_best_effort_bridge_state: Callable[[Path], dict[str, Any] | None],
    try_read_bridge_state: Callable[[Path], dict[str, Any] | None],
    pid_is_alive: Callable[[int], bool],
    heartbeat_age_seconds: Callable[[dict[str, Any]], float | None],
    derive_busy_reason: Callable[[dict[str, Any]], str],
    summarize_state_for_error: Callable[[dict[str, Any] | None], str],
) -> dict[str, Any]:
    project_root_value = arguments.get("projectRoot")
    if not isinstance(project_root_value, str) or not project_root_value.strip():
        raise JsonRpcError(-32602, "projectRoot is required.")

    timeout_ms = arguments.get("timeoutMs", 5000)
    if not isinstance(timeout_ms, int):
        raise JsonRpcError(-32602, "timeoutMs must be an integer.")

    project_root = ensure_project_root(project_root_value)
    try:
        response = invoke_bridge(str(project_root), "unity.status", {}, timeout_ms)
    except tool_invocation_error_type as exc:
        return tool_error_result(exc, build_tool_error_payload=build_tool_error_payload)

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
                "text": json.dumps(summary, ensure_ascii=True),
            }
        ],
        "structuredContent": summary,
        "isError": False,
    }


def call_unity_request_final_status_tool(
    arguments: dict[str, Any],
    *,
    ensure_project_root: Callable[[str], Path],
    build_request_final_status_summary: Callable[[Path, str, str, int], dict[str, Any]],
) -> dict[str, Any]:
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
    summary = build_request_final_status_summary(
        project_root,
        request_id.strip(),
        operation.strip() if isinstance(operation, str) else "",
        timeout_ms,
    )
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(summary, ensure_ascii=True),
            }
        ],
        "structuredContent": summary,
        "isError": False,
    }


def call_unity_scenario_result_summary_tool(
    arguments: dict[str, Any],
    *,
    tool_invocation_error_type: type[Exception],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
    build_scenario_result_summary: Callable[[dict[str, Any], set[str]], dict[str, Any]],
    scenario_terminal_statuses: set[str],
) -> dict[str, Any]:
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
    except tool_invocation_error_type as exc:
        return tool_error_result(exc, build_tool_error_payload=build_tool_error_payload)

    tool_result = bridge_response_to_tool_result(response)
    if tool_result.get("isError"):
        return tool_result

    payload = tool_result.get("structuredContent") or {}
    if not isinstance(payload, dict):
        payload = {}
    summary = build_scenario_result_summary(payload, scenario_terminal_statuses)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(summary, ensure_ascii=True),
            }
        ],
        "structuredContent": summary,
        "isError": False,
    }


def call_unity_maintenance_prune_tool(
    arguments: dict[str, Any],
    *,
    ensure_project_root: Callable[[str], Path],
    prune_project_artifacts: Callable[..., dict[str, Any]],
    bridge_root: Callable[[Path], Path],
    request_journal_dir: Callable[[Path], Path],
    scenario_results_dir: Callable[[Path], Path],
    active_scenario_run_path: Callable[[Path], Path],
    captures_dir: Callable[[Path], Path],
    logs_dir: Callable[[Path], Path],
    default_editor_log_path: Callable[[Path], Path],
    read_json: Callable[[Path], Any],
) -> dict[str, Any]:
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
                "text": json.dumps(result, ensure_ascii=True),
            }
        ],
        "structuredContent": result,
        "isError": False,
    }


def call_tool(
    name: str,
    arguments: dict[str, Any] | None,
    *,
    tools: dict[str, dict[str, Any]],
    special_tool_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
    tool_invocation_error_type: type[Exception],
    ensure_project_root: Callable[[str], Path],
    resolve_operation_timeout_ms: Callable[[Path, str, Any, int], int],
    invoke_bridge: Callable[[str, str, dict[str, Any], int], dict[str, Any]],
    build_tool_error_payload: Callable[[Exception], dict[str, Any]],
    bridge_response_to_tool_result: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if name not in tools:
        raise JsonRpcError(-32601, f"Unknown tool: {name}")

    args = arguments or {}
    special_handler = special_tool_handlers.get(name)
    if special_handler is not None:
        return special_handler(args)

    tool = tools[name]
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
    except tool_invocation_error_type as exc:
        return tool_error_result(exc, build_tool_error_payload=build_tool_error_payload)

    return bridge_response_to_tool_result(response)
