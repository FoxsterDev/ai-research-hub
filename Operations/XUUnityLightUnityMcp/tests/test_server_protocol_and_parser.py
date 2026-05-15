import argparse
import contextlib
import io
import sys
import tempfile
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
                "request-edm4u-resolve",
                "request-sdk-dependency-verify",
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
        self.assertIn("unity_edm4u_resolve", tool_names)
        self.assertIn("unity_sdk_dependency_verify", tool_names)
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
        self.assertEqual("close_same_project_editor_or_use_interactive_lane", payload["recovery_recommended_next_action"])
        self.assertEqual(
            "xuunity_light_unity_mcp.sh request-editor-quit --project-root /tmp/FakeProject --timeout-ms 30000",
            payload["recommended_recovery_command"],
        )
        self.assertNotIn("reopen_block_reason", payload)
        self.assertFalse(bool(payload.get("reopen_blocked")))

    def test_recover_editor_session_open_editor_uses_completed_process_helper(self) -> None:
        args = argparse.Namespace(
            project_root="/tmp/FakeProject",
            timeout_ms=180000,
            close_timeout_ms=45000,
            open_editor=True,
            force_compile_probe=False,
            heartbeat_max_age_seconds=10,
            startup_policy="fail_fast_on_interactive_compile_block",
        )
        discovery = {
            "reconciliation_case": "host_launchable_not_active",
            "detected_editor_pids": [],
            "editor_log_diagnosis": {},
        }
        emitted_payloads: list[dict[str, object]] = []
        completed = mock.Mock(returncode=0, stderr="")

        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(server, "refresh_project_context"),
            mock.patch.object(server, "build_project_discovery_report", return_value=discovery),
            mock.patch.object(server, "current_project_context_host_session_state", return_value={}),
            mock.patch.object(
                server,
                "run_self_json_command_with_completed",
                return_value=({"project_root": "/tmp/FakeProject"}, completed),
            ) as run_mock,
            mock.patch.object(server, "print_json", side_effect=lambda payload: emitted_payloads.append(dict(payload))),
        ):
            server.cmd_recover_editor_session(args)

        run_mock.assert_called_once()
        self.assertEqual(1, len(emitted_payloads))
        payload = emitted_payloads[0]
        self.assertEqual("recovered", payload["recovery_classification"])
        self.assertEqual({"project_root": "/tmp/FakeProject"}, payload["ensure_ready"])

    def test_ensure_ready_without_open_editor_fails_fast_when_project_is_offline(self) -> None:
        args = argparse.Namespace(
            project_root="/tmp/FakeProject",
            open_editor=False,
            unity_app=None,
            editor_log_path=None,
            background_open=False,
            timeout_ms=120000,
            heartbeat_max_age_seconds=10,
            startup_policy="fail_fast_on_interactive_compile_block",
        )
        discovery = {
            "reconciliation_case": "host_launchable_not_active",
            "reconciliation_status": "offline",
            "reconciliation_recommended_next_action": "open_editor_or_ensure_ready",
            "detected_editor_count": 0,
            "detected_editor_pids": [],
        }

        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(server, "resolve_editor_log_path", return_value=Path("/tmp/editor.log")),
            mock.patch.object(server, "build_project_discovery_report", return_value=discovery),
            mock.patch.object(server, "current_project_context_bridge_state", return_value={}),
            mock.patch.object(server, "enrich_tool_invocation_error_with_discovery", side_effect=lambda _, exc: exc),
            mock.patch.object(server, "wait_for_ready") as wait_mock,
        ):
            with self.assertRaises(server.ToolInvocationError) as ctx:
                server.cmd_ensure_ready(args)

        self.assertEqual("editor_not_running", ctx.exception.code)
        self.assertEqual(
            "ensure_ready_without_open_editor_offline",
            ctx.exception.details["fail_fast_reason"],
        )
        self.assertEqual("open_editor_or_ensure_ready", ctx.exception.details["recommended_next_action"])
        self.assertEqual(
            "xuunity_light_unity_mcp.sh ensure-ready --project-root /tmp/FakeProject --open-editor",
            ctx.exception.details["recommended_recovery_command"],
        )
        wait_mock.assert_not_called()

    def test_batch_editor_conflict_includes_concrete_recovery_command(self) -> None:
        project_root = Path("/tmp/FakeProject")

        with mock.patch.object(server, "list_live_project_editor_pids", return_value=[1234]):
            with self.assertRaises(server.ToolInvocationError) as ctx:
                server.ensure_batch_project_closed(project_root, "batch compile")

        exc = ctx.exception
        self.assertEqual("editor_running_batch_conflict", exc.code)
        self.assertEqual([1234], exc.details["live_editor_pids"])
        self.assertEqual(
            "close_same_project_editor_or_use_interactive_lane",
            exc.details["recommended_next_action"],
        )
        self.assertEqual(
            "xuunity_light_unity_mcp.sh request-editor-quit --project-root /tmp/FakeProject --timeout-ms 30000",
            exc.details["recommended_recovery_command"],
        )
        self.assertTrue(exc.details["closeout_verification_required"])

        summary = server.build_batch_prepare_failure_summary(
            action="batch_compile",
            result_path=Path("/tmp/result.json"),
            log_path=Path("/tmp/editor.log"),
            exc=exc,
            truncate_text=server.truncate_text,
        )

        self.assertEqual("batch_prepare_blocked", summary["transport_outcome"])
        self.assertEqual("not_started", summary["unity_outcome"])
        self.assertEqual(exc.details["recommended_next_action"], summary["recommended_next_action"])
        self.assertEqual(exc.details["recommended_recovery_command"], summary["recommended_recovery_command"])
        self.assertTrue(summary["closeout_verification_required"])
        self.assertIn("verify editor process exit", summary["next_step"])

    def test_batch_commands_accept_timeout_ms(self) -> None:
        parser = server.build_parser()

        matrix_args = parser.parse_args(
            [
                "batch-build-config-compile-matrix",
                "--project-root",
                "/tmp/FakeProject",
                "--timeout-ms",
                "900000",
            ]
        )
        self.assertEqual(900000, matrix_args.timeout_ms)

        editmode_args = parser.parse_args(
            [
                "batch-editmode-tests",
                "--project-root",
                "/tmp/FakeProject",
                "--timeout-ms",
                "900000",
                "--dry-run",
            ]
        )
        self.assertEqual(900000, editmode_args.timeout_ms)

    def test_test_framework_regression_defaults_are_public_safe(self) -> None:
        parser = server.build_parser()
        args = parser.parse_args(
            [
                "batch-test-framework-version-regression",
                "--project-root",
                "/tmp/FakeProject",
            ]
        )

        self.assertEqual("active", args.compile_target)
        self.assertEqual([], args.focus_assembly_name)
        self.assertEqual([], args.focus_test_name)
        self.assertFalse(args.no_generated_focus_test)

    def test_generated_test_framework_focus_fixture_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "Assets").mkdir()

            fixture = server.deploy_test_framework_regression_focus_fixture(
                project_root,
                server.TEST_FRAMEWORK_REGRESSION_GENERATED_FOCUS_RELATIVE_DIR,
            )

            fixture_path = Path(fixture["fixture_path"])
            self.assertTrue(fixture_path.is_file())
            self.assertIn(
                server.TEST_FRAMEWORK_REGRESSION_GENERATED_FOCUS_TEST_NAME,
                fixture["test_name"],
            )

            cleanup = server.cleanup_test_framework_regression_focus_fixture(fixture)

            self.assertTrue(cleanup["removed_file"])
            self.assertFalse(fixture_path.exists())

    def test_error_summary_includes_closeout_verified_false(self) -> None:
        payload = {
            "error": {"code": "restore_editor_state_incomplete", "message": "closeout incomplete"},
            "closeout_classification": "quit_ack_without_exit",
            "closeout_verified": False,
            "recommended_next_action": "manual_editor_close",
            "recommended_recovery_command": "xuunity_light_unity_mcp.sh recover-editor-session --project-root /tmp/FakeProject",
        }

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            server.emit_tool_error_summary(payload)

        output = stderr.getvalue()
        self.assertIn("closeout_classification=quit_ack_without_exit", output)
        self.assertIn("closeout_verified=false", output)
        self.assertIn("recovery_command xuunity_light_unity_mcp.sh recover-editor-session", output)

    def test_request_playmode_tests_exits_playmode_and_retries_once(self) -> None:
        args = argparse.Namespace(
            project_root="/tmp/FakeProject",
            timeout_ms=None,
            test_names=None,
            group_names=None,
            category_names=None,
            assembly_names=None,
        )
        emitted_payloads: list[dict[str, object]] = []
        invoke_calls: list[tuple[str, dict[str, object], int]] = []

        def fake_invoke_bridge(
            project_root_value: str,
            operation: str,
            operation_args: dict[str, object],
            timeout_ms: int,
        ) -> dict[str, object]:
            invoke_calls.append((operation, dict(operation_args), timeout_ms))
            if operation == "unity.tests.run_playmode" and len([call for call in invoke_calls if call[0] == operation]) == 1:
                return {
                    "status": "ok",
                    "payload_json": (
                        '{"status":"error","error":{"code":"playmode_state_invalid",'
                        '"message":"Cannot run PlayMode tests unless Unity is in edit mode. Current state: playing."}}'
                    ),
                }
            if operation == "unity.playmode.set":
                return {
                    "status": "ok",
                    "payload_json": '{"status":"ok","state":"edit"}',
                }
            return {
                "status": "ok",
                "payload_json": '{"status":"ok","total":47,"passed":47}',
            }

        def fake_timeout(project_root: Path, operation: str, fallback_timeout_ms: int) -> int:
            if operation == "unity.tests.run_playmode":
                return 300000
            if operation == "unity.playmode.set":
                return 180000
            raise AssertionError(f"Unexpected operation: {operation}")

        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(server, "invoke_bridge", side_effect=fake_invoke_bridge),
            mock.patch.object(server, "resolve_operation_default_timeout_ms", side_effect=fake_timeout),
            mock.patch.object(server, "print_json", side_effect=lambda payload: emitted_payloads.append(dict(payload))),
        ):
            server.cmd_request_playmode_tests(args)

        self.assertEqual(1, len(emitted_payloads))
        self.assertEqual("ok", emitted_payloads[0]["status"])
        self.assertEqual(
            [
                ("unity.tests.run_playmode", {"testNames": None, "groupNames": None, "categoryNames": None, "assemblyNames": None}, 300000),
                ("unity.playmode.set", {"action": "exit"}, 180000),
                ("unity.tests.run_playmode", {"testNames": None, "groupNames": None, "categoryNames": None, "assemblyNames": None}, 300000),
            ],
            invoke_calls,
        )

    def test_request_playmode_tests_retries_when_bridge_returns_top_level_playmode_error(self) -> None:
        args = argparse.Namespace(
            project_root="/tmp/FakeProject",
            timeout_ms=None,
            test_names=None,
            group_names=None,
            category_names=None,
            assembly_names=None,
        )
        emitted_payloads: list[dict[str, object]] = []
        invoke_calls: list[tuple[str, dict[str, object], int]] = []

        def fake_invoke_bridge(
            project_root_value: str,
            operation: str,
            operation_args: dict[str, object],
            timeout_ms: int,
        ) -> dict[str, object]:
            invoke_calls.append((operation, dict(operation_args), timeout_ms))
            if operation == "unity.tests.run_playmode" and len([call for call in invoke_calls if call[0] == operation]) == 1:
                return {
                    "request_id": "play-1",
                    "status": "error",
                    "completed_at_utc": "2026-05-11T22:40:59Z",
                    "payload_type": "",
                    "payload_json": "",
                    "error": {
                        "code": "playmode_state_invalid",
                        "message": "Cannot run PlayMode tests unless Unity is in edit mode. Current state: playing.",
                    },
                }
            if operation == "unity.playmode.set":
                return {
                    "status": "ok",
                    "payload_json": '{"status":"ok","state":"edit"}',
                }
            return {
                "status": "ok",
                "payload_json": '{"status":"passed","total":47,"passed":47}',
            }

        def fake_timeout(project_root: Path, operation: str, fallback_timeout_ms: int) -> int:
            if operation == "unity.tests.run_playmode":
                return 300000
            if operation == "unity.playmode.set":
                return 180000
            raise AssertionError(f"Unexpected operation: {operation}")

        with (
            mock.patch.object(server, "ensure_project_root", return_value=Path("/tmp/FakeProject")),
            mock.patch.object(server, "invoke_bridge", side_effect=fake_invoke_bridge),
            mock.patch.object(server, "resolve_operation_default_timeout_ms", side_effect=fake_timeout),
            mock.patch.object(server, "print_json", side_effect=lambda payload: emitted_payloads.append(dict(payload))),
        ):
            server.cmd_request_playmode_tests(args)

        self.assertEqual(1, len(emitted_payloads))
        self.assertEqual("ok", emitted_payloads[0]["status"])
        self.assertEqual(3, len(invoke_calls))
        self.assertEqual("unity.tests.run_playmode", invoke_calls[0][0])
        self.assertEqual("unity.playmode.set", invoke_calls[1][0])
        self.assertEqual("unity.tests.run_playmode", invoke_calls[2][0])

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
