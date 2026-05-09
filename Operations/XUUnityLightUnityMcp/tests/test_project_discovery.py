import sys
import unittest
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from server_discovery import discover_project_context_state


class ProjectDiscoveryTests(unittest.TestCase):
    def test_discovery_prefers_live_bridge_state(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: {
                "editor_pid": 101,
                "transport": "tcp_loopback",
                "transport_listener_state": "listening",
            },
            try_read_host_editor_session_state=lambda _: {"editor_pid": 202},
            find_running_unity_editors_for_project=lambda _: [{"pid": 101}, {"pid": 202}],
            pid_is_alive=lambda pid: pid in {101, 202},
            bridge_enabled=lambda _: True,
        )

        self.assertEqual("bridge_live", result["discovery_classification"])
        self.assertEqual("bridge_state", result["authoritative_state_source"])
        self.assertEqual(101, result["last_seen_pid"])
        self.assertEqual("tcp_loopback", result["active_transport"])
        self.assertEqual("bridge_state_authoritative", result["reconciliation_case"])
        self.assertEqual("healthy", result["reconciliation_status"])

    def test_discovery_falls_back_to_live_host_session_when_bridge_state_is_stale(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: {"editor_pid": 101, "transport": "file_ipc"},
            try_read_host_editor_session_state=lambda _: {"editor_pid": 202},
            find_running_unity_editors_for_project=lambda _: [{"pid": 202}],
            pid_is_alive=lambda pid: pid == 202,
            bridge_enabled=lambda _: True,
        )

        self.assertEqual("host_session_live", result["discovery_classification"])
        self.assertEqual("host_editor_session", result["authoritative_state_source"])
        self.assertFalse(result["bridge_state_live"])
        self.assertTrue(result["host_session_live"])
        self.assertEqual(202, result["last_seen_pid"])
        self.assertEqual("stale_bridge_state", result["reconciliation_case"])
        self.assertEqual("ensure_ready_or_recover_bridge", result["reconciliation_recommended_next_action"])

    def test_discovery_uses_process_table_when_state_files_are_missing(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: None,
            try_read_host_editor_session_state=lambda _: None,
            find_running_unity_editors_for_project=lambda _: [{"pid": 303}],
            pid_is_alive=lambda pid: pid == 303,
            bridge_enabled=lambda _: True,
        )

        self.assertEqual("editor_process_only", result["discovery_classification"])
        self.assertEqual("process_table", result["authoritative_state_source"])
        self.assertEqual([303], result["detected_editor_pids"])
        self.assertEqual("live_process_only", result["reconciliation_case"])

    def test_discovery_classifies_stale_state_without_live_process(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: {"editor_pid": 404},
            try_read_host_editor_session_state=lambda _: {},
            find_running_unity_editors_for_project=lambda _: [],
            pid_is_alive=lambda pid: False,
            bridge_enabled=lambda _: True,
        )

        self.assertEqual("stale_state", result["discovery_classification"])
        self.assertEqual("state_files", result["authoritative_state_source"])
        self.assertFalse(result["bridge_state_live"])
        self.assertEqual("stale_bridge_state", result["reconciliation_case"])

    def test_discovery_classifies_disabled_bridge_without_live_editor(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: None,
            try_read_host_editor_session_state=lambda _: None,
            find_running_unity_editors_for_project=lambda _: [],
            pid_is_alive=lambda pid: False,
            bridge_enabled=lambda _: False,
        )

        self.assertEqual("bridge_disabled", result["discovery_classification"])
        self.assertEqual("bridge_config", result["authoritative_state_source"])
        self.assertEqual("bridge_disabled", result["reconciliation_case"])
        self.assertEqual("enable_bridge_and_retry", result["reconciliation_recommended_next_action"])

    def test_discovery_bridge_disabled_overrides_stale_state_when_editor_is_not_live(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: {"editor_pid": 404},
            try_read_host_editor_session_state=lambda _: {"editor_pid": 505},
            find_running_unity_editors_for_project=lambda _: [],
            pid_is_alive=lambda pid: False,
            bridge_enabled=lambda _: False,
        )

        self.assertEqual("bridge_disabled", result["discovery_classification"])
        self.assertEqual("bridge_disabled", result["reconciliation_case"])

    def test_discovery_builds_transport_state_and_state_groups(self) -> None:
        project_root = Path("/tmp/ProjectA")
        result = discover_project_context_state(
            project_root,
            try_read_bridge_state=lambda _: {
                "editor_pid": 101,
                "transport": "tcp_loopback",
                "transport_requested": "file_ipc",
                "transport_listener_state": "listening",
                "transport_host": "127.0.0.1",
                "transport_port": 41234,
                "bridge_generation": 7,
                "bridge_session_id": "session-a",
                "playmode_state": "edit",
            },
            try_read_host_editor_session_state=lambda _: {"editor_pid": 202, "opened_by_host": True},
            find_running_unity_editors_for_project=lambda _: [{"pid": 101}],
            pid_is_alive=lambda pid: pid in {101, 202},
            bridge_enabled=lambda _: True,
            build_project_health=lambda **_: {
                "host_health_classification": "fresh",
                "host_health_reason": "heartbeat_fresh",
                "host_health_recommended_next_action": "none",
                "host_health_termination_policy": "observe_only",
                "anr_classification": "none",
            },
        )

        self.assertEqual("per_project_context", result["transport_state"]["selection_scope"])
        self.assertEqual("tcp_loopback", result["transport_state"]["active_transport"])
        self.assertEqual("file_ipc", result["transport_state"]["requested_transport"])
        self.assertEqual("127.0.0.1:41234", result["transport_state"]["address"])
        self.assertEqual(7, result["state_groups"]["bridge_identity"]["bridge_generation"])
        self.assertEqual("session-a", result["state_groups"]["bridge_identity"]["bridge_session_id"])
        self.assertEqual([101], result["state_groups"]["process_identity"]["detected_editor_pids"])
        self.assertTrue(result["state_groups"]["process_identity"]["opened_by_host"])
        self.assertEqual("fresh", result["state_groups"]["health"]["host_health_classification"])
        self.assertEqual("edit", result["state_groups"]["editor_state"]["playmode_state"])


if __name__ == "__main__":
    unittest.main()
