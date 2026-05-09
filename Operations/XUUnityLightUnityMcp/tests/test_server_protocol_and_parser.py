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
                "request-project-refresh",
                "request-compile",
                "request-editmode-tests",
                "ensure-ready",
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
                "read_best_effort_bridge_state",
                return_value={
                    "bridge_generation": 7,
                    "bridge_session_id": "session-a",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "pending_request_count": 0,
                    "health_status": "healthy",
                },
            ),
            mock.patch.object(server, "try_read_bridge_state", return_value=None),
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
