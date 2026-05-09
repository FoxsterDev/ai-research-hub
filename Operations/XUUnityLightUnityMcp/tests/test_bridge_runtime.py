import json
import sys
import tempfile
import unittest
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

import server_bridge_runtime


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class BridgeRuntimeTests(unittest.TestCase):
    def test_build_bridge_stabilization_summary_healthy(self) -> None:
        summary = server_bridge_runtime.build_bridge_stabilization_summary(
            {
                "bridge_generation": 7,
                "bridge_session_id": "session-a",
                "transport": "tcp_loopback",
                "transport_listener_state": "listening",
                "health_status": "healthy",
                "pending_request_count": 0,
                "domain_reload_in_progress": False,
                "asset_import_in_progress": False,
                "package_operation_in_progress": False,
                "compile_settle_pending": False,
                "refresh_settle_pending": False,
                "playmode_transition_pending": False,
            }
        )

        self.assertTrue(summary["stabilized"])
        self.assertTrue(summary["safe_to_retry"])
        self.assertEqual([], summary["blocking_reasons"])
        self.assertEqual(7, summary["bridge_generation"])
        self.assertEqual("session-a", summary["bridge_session_id"])

    def test_build_bridge_stabilization_summary_detects_blockers(self) -> None:
        summary = server_bridge_runtime.build_bridge_stabilization_summary(
            {
                "transport": "tcp_loopback",
                "transport_listener_state": "closed",
                "health_status": "unstable",
                "pending_request_count": 2,
                "domain_reload_in_progress": True,
            },
            editor_running=False,
            mcp_reachable=False,
        )

        self.assertFalse(summary["stabilized"])
        self.assertIn("editor_not_running", summary["blocking_reasons"])
        self.assertIn("mcp_not_reachable", summary["blocking_reasons"])
        self.assertIn("health_not_healthy", summary["blocking_reasons"])
        self.assertIn("domain_reload_in_progress", summary["blocking_reasons"])
        self.assertIn("pending_request_in_flight", summary["blocking_reasons"])
        self.assertIn("transport_listener_not_ready", summary["blocking_reasons"])

    def test_build_request_final_status_completed_ok_with_reclassification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            state_path = project_root / "Library" / "XUUnityLightMcp" / "state" / "bridge_state.json"
            request_id = "req-ok"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "bridge_generation": 4,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T15:40:58Z",
                    "started_at_utc": "2026-05-09T15:40:58Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "bridge_generation": 4,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "03_request_completed.json",
                {
                    "event_id": "03",
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-09T15:41:00Z",
                    "completed_at_utc": "2026-05-09T15:41:00Z",
                    "operation_status": "ok",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "bridge_generation": 4,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "04_request_reclassified.json",
                {
                    "event_id": "04",
                    "event_type": "request_reclassified",
                    "event_at_utc": "2026-05-09T15:41:11Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "reason": "bridge_generation_changed_during_post_request_settle",
                    "retryable": False,
                    "reclassified_status": "settled_after_lifecycle_reset",
                    "previous_bridge_generation": 4,
                    "previous_bridge_session_id": "session-old",
                    "bridge_generation": 6,
                    "bridge_session_id": "session-new",
                },
            )
            write_json(
                state_path,
                {
                    "bridge_generation": 6,
                    "bridge_session_id": "session-new",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
            )

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.project.refresh",
                poll_timeout_ms=0,
            )

            self.assertTrue(summary["request_submitted"])
            self.assertTrue(summary["request_started"])
            self.assertTrue(summary["request_completed"])
            self.assertTrue(summary["reclassified"])
            self.assertEqual("completed_ok", summary["operation_outcome"])
            self.assertEqual("settled_after_lifecycle_reset", summary["reclassified_status"])
            self.assertEqual("none", summary["recommended_next_action"])
            self.assertTrue(summary["request_observed_in_unity_journal"])
            self.assertTrue(summary["bridge_changed_since_submission"])
            self.assertFalse(summary["recovery_gap_detected"])
            self.assertEqual(4, summary["journal_event_count"])

    def test_build_request_final_status_detects_submitted_lost_after_lifecycle_churn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            state_path = project_root / "Library" / "XUUnityLightMcp" / "state" / "bridge_state.json"
            request_id = "req-gap"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "bridge_generation": 4,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                state_path,
                {
                    "bridge_generation": 9,
                    "bridge_session_id": "session-new",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
            )

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.project.refresh",
                poll_timeout_ms=0,
            )

            self.assertTrue(summary["request_submitted"])
            self.assertFalse(summary["request_started"])
            self.assertFalse(summary["request_completed"])
            self.assertEqual("submitted_lost_after_lifecycle_churn", summary["operation_outcome"])
            self.assertEqual("verify_effect_or_retry", summary["recommended_next_action"])
            self.assertFalse(summary["request_observed_in_unity_journal"])
            self.assertTrue(summary["bridge_changed_since_submission"])
            self.assertTrue(summary["recovery_gap_detected"])


if __name__ == "__main__":
    unittest.main()
