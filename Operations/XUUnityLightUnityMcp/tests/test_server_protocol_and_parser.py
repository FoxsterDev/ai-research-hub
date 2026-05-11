import argparse
import sys
import unittest
from pathlib import Path
from unittest import mock

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

import server


def get_subparser_choices(parser: argparse.ArgumentParser) -> set[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices.keys())
    return set()


class ServerProtocolAndParserTests(unittest.TestCase):
    def test_parser_contains_critical_subcommands(self) -> None:
        parser = server.build_parser()
        choices = get_subparser_choices(parser)

        self.assertTrue(
            {
                "bridge-state",
                "request-status",
                "request-status-summary",
                "request-final-status",
                "request-cancel",
                "request-stale-cleanup",
                "request-scenario-results-list",
                "request-scenario-result-latest",
                "request-project-refresh",
                "project-discovery-report",
                "registry-context-report",
                "registry-prune-contexts",
                "request-compile",
                "request-editmode-tests",
                "ensure-ready",
                "recover-editor-session",
                "batch-compile",
                "maintenance-prune",
            }.issubset(choices)
        )

    def test_tools_list_includes_required_tool_surfaces(self) -> None:
        response = server.handle_json_rpc_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            {"initialized": True, "protocolVersion": server.PROTOCOL_VERSION},
        )

        tool_names = {
            tool["name"]
            for tool in response["result"]["tools"]
        }
        self.assertIn("unity_status_summary", tool_names)
        self.assertIn("unity_request_final_status", tool_names)
        self.assertIn("unity_compile_build_config_matrix", tool_names)
        self.assertIn("unity_scenario_run_and_wait", tool_names)
        self.assertIn("unity_scenario_results_list", tool_names)
        self.assertIn("unity_scenario_result_latest", tool_names)

    def test_tools_call_status_summary_happy_path(self) -> None:
        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(
                server,
                "invoke_bridge",
                return_value={
                    "status": "ok",
                    "payload_type": "unity.status",
                    "payload_json": (
                        '{"editor_running": true, "mcp_reachable": true, '
                        '"health_status": "healthy", "playmode_state": "edit"}'
                    ),
                },
            ),
            mock.patch.object(
                server,
                "current_project_context_bridge_state",
                return_value={
                    "bridge_generation": 7,
                    "bridge_session_id": "session-a",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "pending_request_count": 0,
                    "health_status": "healthy",
                },
            ),
            mock.patch.object(
                server,
                "refresh_project_context",
                return_value=mock.Mock(
                    last_bridge_state={},
                    discovery_details={
                        "host_health_classification": "fresh",
                        "host_health_reason": "heartbeat_fresh",
                        "host_health_recommended_next_action": "none",
                        "host_health_termination_policy": "observe_only",
                        "host_health_heartbeat_age_seconds": 1.25,
                        "host_health_busy_reason": "idle",
                        "host_health_progress_evidence": [],
                        "anr_classification": "none",
                        "discovery_classification": "bridge_live",
                        "reconciliation_case": "bridge_state_authoritative",
                        "reconciliation_status": "healthy",
                        "detected_editor_count": 1,
                        "detected_editor_pids": [1234],
                        "transport_state": {"selection_scope": "per_project_context", "active_transport": "tcp_loopback"},
                        "state_groups": {"bridge_identity": {"bridge_generation": 7}},
                    },
                ),
            ),
            mock.patch.object(server, "pid_is_alive", return_value=True),
            mock.patch.object(server, "heartbeat_age_seconds", return_value=1.25),
            mock.patch.object(server, "derive_busy_reason", return_value="idle"),
            mock.patch.object(server, "summarize_state_for_error", return_value="ok"),
        ):
            response = server.handle_json_rpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "unity_status_summary",
                        "arguments": {"projectRoot": "/tmp/FakeProject", "timeoutMs": 5000},
                    },
                },
                {"initialized": True, "protocolVersion": server.PROTOCOL_VERSION},
            )

        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual("unity_status_summary", result["structuredContent"]["action"])
        self.assertEqual(7, result["structuredContent"]["bridge_generation"])
        self.assertEqual("session-a", result["structuredContent"]["bridge_session_id"])
        self.assertEqual("healthy", result["structuredContent"]["health_status"])
        self.assertEqual("idle", result["structuredContent"]["busy_reason"])
        self.assertEqual("fresh", result["structuredContent"]["host_health_classification"])
        self.assertEqual("bridge_live", result["structuredContent"]["discovery_classification"])
        self.assertEqual("bridge_state_authoritative", result["structuredContent"]["reconciliation_case"])
        self.assertEqual("tcp_loopback", result["structuredContent"]["transport_state"]["active_transport"])
        self.assertEqual(7, result["structuredContent"]["state_groups"]["bridge_identity"]["bridge_generation"])

    def test_tools_call_status_summary_falls_back_to_discovery_when_editor_is_offline(self) -> None:
        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(
                server,
                "invoke_bridge",
                side_effect=server.ToolInvocationError(
                    "editor_not_running",
                    "Unity editor is not running for this project.",
                ),
            ),
            mock.patch.object(server, "current_project_context_bridge_state", return_value={"transport": "tcp_loopback"}),
            mock.patch.object(
                server,
                "refresh_project_context",
                return_value=mock.Mock(
                    last_bridge_state={"transport": "tcp_loopback"},
                    discovery_details={
                        "discovery_classification": "stale_state",
                        "discovery_reason": "state_files_present_without_live_project_process",
                        "authoritative_state_source": "state_files",
                        "reconciliation_case": "stale_bridge_state",
                        "reconciliation_status": "offline",
                        "reconciliation_reason": "bridge_state_present_but_editor_pid_not_alive",
                        "reconciliation_recommended_next_action": "recover_editor_session",
                        "detected_editor_count": 0,
                        "detected_editor_pids": [],
                        "bridge_state_live": False,
                        "host_session_live": False,
                        "active_transport": "tcp_loopback",
                    },
                ),
            ),
            mock.patch.object(server, "pid_is_alive", return_value=False),
            mock.patch.object(server, "heartbeat_age_seconds", return_value=None),
            mock.patch.object(server, "derive_busy_reason", return_value="idle"),
            mock.patch.object(server, "summarize_state_for_error", return_value="offline"),
        ):
            response = server.handle_json_rpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "unity_status_summary",
                        "arguments": {"projectRoot": "/tmp/FakeProject", "timeoutMs": 5000},
                    },
                },
                {"initialized": True, "protocolVersion": server.PROTOCOL_VERSION},
            )

        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual("stale_bridge_state", result["structuredContent"]["reconciliation_case"])
        self.assertEqual("offline", result["structuredContent"]["reconciliation_status"])
        self.assertEqual("recover_editor_session", result["structuredContent"]["reconciliation_recommended_next_action"])

    def test_tools_call_scenario_result_summary_falls_back_to_discovery_when_editor_is_offline(self) -> None:
        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(
                server,
                "invoke_bridge",
                side_effect=server.ToolInvocationError(
                    "editor_not_running",
                    "Unity editor is not running for this project.",
                ),
            ),
            mock.patch.object(
                server,
                "refresh_project_context",
                return_value=mock.Mock(
                    last_bridge_state={"transport": "tcp_loopback"},
                    discovery_details={
                        "discovery_classification": "stale_state",
                        "discovery_reason": "state_files_present_without_live_project_process",
                        "authoritative_state_source": "state_files",
                        "reconciliation_case": "stale_bridge_state",
                        "reconciliation_status": "offline",
                        "reconciliation_reason": "bridge_state_present_but_editor_pid_not_alive",
                        "reconciliation_recommended_next_action": "recover_editor_session",
                        "detected_editor_count": 0,
                        "detected_editor_pids": [],
                    },
                ),
            ),
        ):
            response = server.handle_json_rpc_message(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "unity_scenario_result_summary",
                        "arguments": {
                            "projectRoot": "/tmp/FakeProject",
                            "scenarioName": "SampleScenario",
                            "timeoutMs": 5000,
                        },
                    },
                },
                {"initialized": True, "protocolVersion": server.PROTOCOL_VERSION},
            )

        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual("offline", result["structuredContent"]["status"])
        self.assertEqual("stale_bridge_state", result["structuredContent"]["reconciliation_case"])
        self.assertEqual("recover_editor_session", result["structuredContent"]["recommended_next_action"])
        self.assertEqual("editor_not_running", result["structuredContent"]["offline_error_code"])

    def test_recover_editor_session_reports_batch_lane_conflict_without_claiming_compile_red(self) -> None:
        args = argparse.Namespace(
            project_root="/tmp/FakeProject",
            timeout_ms=180000,
            close_timeout_ms=45000,
            open_editor=False,
            force_compile_probe=True,
            heartbeat_max_age_seconds=10,
            startup_policy="fail_fast_on_interactive_compile_block",
        )
        discovery_initial = {
            "reconciliation_case": "stale_bridge_state",
            "detected_editor_pids": [],
            "editor_log_diagnosis": {},
        }
        discovery_after_clear = {
            "reconciliation_case": "host_launchable_not_active",
            "detected_editor_pids": [],
            "editor_log_diagnosis": {},
        }
        emitted_payloads: list[dict[str, object]] = []

        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(server, "refresh_project_context"),
            mock.patch.object(
                server,
                "build_project_discovery_report",
                side_effect=[
                    discovery_initial,
                    discovery_initial,
                    discovery_after_clear,
                    discovery_after_clear,
                ],
            ),
            mock.patch.object(server, "current_project_context_host_session_state", return_value={}),
            mock.patch.object(server, "clear_stale_bridge_state", return_value=True),
            mock.patch.object(
                server,
                "run_batch_build_config_compile_matrix_probe",
                return_value={
                    "succeeded": False,
                    "batch_probe": {
                        "error": {
                            "code": "editor_running_batch_conflict",
                            "message": "Editor is already running.",
                        }
                    },
                    "top_actionable_error": "Editor is already running.",
                },
            ),
            mock.patch.object(server, "print_json", side_effect=lambda payload: emitted_payloads.append(dict(payload))),
        ):
            with self.assertRaises(SystemExit) as ctx:
                server.cmd_recover_editor_session(args)

        self.assertEqual(1, ctx.exception.code)
        self.assertEqual(1, len(emitted_payloads))
        payload = emitted_payloads[0]
        self.assertEqual("compile_probe_blocked_by_live_editor", payload["recovery_classification"])
        self.assertEqual("close_editor_or_use_interactive_lane", payload["recovery_recommended_next_action"])
        self.assertNotIn("reopen_block_reason", payload)
        self.assertFalse(bool(payload.get("reopen_blocked")))

    def test_initialize_returns_protocol_version(self) -> None:
        response = server.handle_json_rpc_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
            {"initialized": False, "protocolVersion": None},
        )

        self.assertEqual(server.PROTOCOL_VERSION, response["result"]["protocolVersion"])
        self.assertEqual("xuunity-light-unity-mcp", response["result"]["serverInfo"]["name"])


if __name__ == "__main__":
    unittest.main()
