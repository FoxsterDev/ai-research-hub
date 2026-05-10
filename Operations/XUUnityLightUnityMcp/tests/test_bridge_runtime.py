import json
import os
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

    def test_cancel_request_best_effort_cancels_file_ipc_request_before_unity_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            inbox_dir = project_root / "Library" / "XUUnityLightMcp" / "inbox"
            request_id = "req-cancel-early"
            request_path = inbox_dir / f"{request_id}.json"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.compile.matrix",
                    "transport": "file_ipc",
                },
            )
            write_json(
                request_path,
                {
                    "request_id": request_id,
                    "operation": "unity.compile.matrix",
                },
            )

            result = server_bridge_runtime.cancel_request_best_effort(
                project_root,
                request_id,
                operation="unity.compile.matrix",
                current_state={
                    "transport": "file_ipc",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
            )

            self.assertEqual("request_cancelled", result["cancellation_event_type"])
            self.assertEqual("cancelled_before_unity_start", result["cancellation_status"])
            self.assertTrue(result["request_file_deleted"])
            self.assertFalse(request_path.exists())

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.compile.matrix",
                current_state={
                    "transport": "file_ipc",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                poll_timeout_ms=0,
            )

            self.assertTrue(summary["request_cancelled"])
            self.assertEqual("cancelled_before_unity_start", summary["operation_outcome"])
            self.assertEqual("retry_request", summary["recommended_next_action"])

    def test_cancel_request_best_effort_marks_in_flight_cancellation_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            request_id = "req-cancel-running"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "transport": "tcp_loopback",
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
                },
            )

            result = server_bridge_runtime.cancel_request_best_effort(
                project_root,
                request_id,
                operation="unity.project.refresh",
                current_state={
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 1,
                },
            )

            self.assertEqual("request_cancel_requested", result["cancellation_event_type"])
            self.assertEqual("cancellation_requested_in_flight", result["cancellation_status"])
            self.assertEqual("wait_for_bridge_stabilization", result["recommended_next_action"])

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.project.refresh",
                current_state={
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                poll_timeout_ms=0,
            )

            self.assertTrue(summary["cancellation_requested"])
            self.assertEqual("cancellation_requested_in_flight", summary["operation_outcome"])
            self.assertEqual("verify_effect_or_retry", summary["recommended_next_action"])

    def test_inspect_and_cleanup_stale_request_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            inbox_dir = project_root / "Library" / "XUUnityLightMcp" / "inbox"
            outbox_dir = project_root / "Library" / "XUUnityLightMcp" / "outbox"
            request_id = "req-stale-cleanup"
            inbox_path = inbox_dir / f"{request_id}.json"
            outbox_path = outbox_dir / f"{request_id}.json"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.status",
                    "transport": "file_ipc",
                },
            )
            write_json(
                journal_dir / "02_request_completed.json",
                {
                    "event_id": "02",
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-09T15:40:58Z",
                    "completed_at_utc": "2026-05-09T15:40:58Z",
                    "request_id": request_id,
                    "operation": "unity.status",
                    "operation_status": "ok",
                },
            )
            write_json(inbox_path, {"request_id": request_id})
            write_json(outbox_path, {"request_id": request_id, "status": "ok"})
            stale_unix = 1_700_000_000
            os.utime(inbox_path, (stale_unix, stale_unix))
            os.utime(outbox_path, (stale_unix, stale_unix))

            inspection = server_bridge_runtime.inspect_stale_request_artifacts(
                project_root,
                current_state={
                    "transport": "file_ipc",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                stale_age_seconds=1,
                max_entries=10,
            )

            self.assertTrue(inspection["has_stale_request_artifacts"])
            self.assertEqual(2, inspection["candidate_count"])
            self.assertEqual(1, inspection["classifications"]["stale_inbox_after_terminal_event"])
            self.assertEqual(1, inspection["classifications"]["stale_outbox_after_terminal_event"])

            cleanup = server_bridge_runtime.cleanup_stale_request_artifacts(
                project_root,
                current_state={
                    "transport": "file_ipc",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                stale_age_seconds=1,
                dry_run=False,
                max_entries=10,
            )

            self.assertEqual("request_stale_cleanup", cleanup["action"])
            self.assertEqual(2, cleanup["removed_count"])
            self.assertFalse(inbox_path.exists())
            self.assertFalse(outbox_path.exists())

    def test_cleanup_stale_request_artifacts_dry_run_reports_would_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            outbox_dir = project_root / "Library" / "XUUnityLightMcp" / "outbox"
            request_id = "req-stale-dry-run"
            outbox_path = outbox_dir / f"{request_id}.json"

            write_json(
                journal_dir / "01_request_completed.json",
                {
                    "event_id": "01",
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-09T15:40:58Z",
                    "completed_at_utc": "2026-05-09T15:40:58Z",
                    "request_id": request_id,
                    "operation": "unity.status",
                    "operation_status": "ok",
                },
            )
            write_json(outbox_path, {"request_id": request_id, "status": "ok"})
            stale_unix = 1_700_000_000
            os.utime(outbox_path, (stale_unix, stale_unix))

            cleanup = server_bridge_runtime.cleanup_stale_request_artifacts(
                project_root,
                current_state={
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                stale_age_seconds=1,
                dry_run=True,
                max_entries=10,
            )

            self.assertTrue(outbox_path.exists())
            self.assertEqual(0, cleanup["removed_count"])
            self.assertEqual(1, cleanup["would_remove_count"])
            self.assertEqual([str(outbox_path.resolve())], cleanup["would_remove_paths"])

    def test_inspect_stale_request_artifacts_detects_unclaimed_old_inbox_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            inbox_dir = project_root / "Library" / "XUUnityLightMcp" / "inbox"
            request_id = "req-stale-unclaimed"
            inbox_path = inbox_dir / f"{request_id}.json"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.project.refresh",
                    "transport": "file_ipc",
                },
            )
            write_json(inbox_path, {"request_id": request_id})
            stale_unix = 1_700_000_000
            os.utime(inbox_path, (stale_unix, stale_unix))

            inspection = server_bridge_runtime.inspect_stale_request_artifacts(
                project_root,
                current_state={
                    "transport": "file_ipc",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
                stale_age_seconds=1,
                max_entries=10,
            )

            self.assertTrue(inspection["has_stale_request_artifacts"])
            self.assertEqual(
                "stale_inbox_without_unity_ownership",
                inspection["candidates"][0]["classification"],
            )

    def test_build_request_final_status_uses_injected_state_reader_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            request_id = "req-reader"

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

            calls: list[str] = []

            def read_current_state(_: Path) -> dict:
                calls.append("read")
                return {
                    "bridge_generation": 9,
                    "bridge_session_id": "session-new",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                }

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.project.refresh",
                read_current_state=read_current_state,
                poll_timeout_ms=0,
            )

            self.assertEqual(["read"], calls)
            self.assertEqual("submitted_lost_after_lifecycle_churn", summary["operation_outcome"])

    def test_build_request_final_status_includes_artifact_manifest_and_structured_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            response_dir = project_root / "Library" / "XUUnityLightMcp" / "outbox"
            logs_dir = project_root / "Library" / "XUUnityLightMcp" / "logs"
            request_id = "req-evidence"
            scenario_result_path = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results" / "sample.json"
            capture_path = project_root / "Library" / "XUUnityLightMcp" / "captures" / "sample.png"
            editor_log_path = logs_dir / "unity_editor.log"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-09T15:40:57Z",
                    "request_id": request_id,
                    "operation": "unity.scenario.result",
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
                    "operation": "unity.scenario.result",
                },
            )
            write_json(
                journal_dir / "03_request_completed.json",
                {
                    "event_id": "03",
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-09T15:41:02Z",
                    "completed_at_utc": "2026-05-09T15:41:02Z",
                    "operation_status": "ok",
                    "request_id": request_id,
                    "operation": "unity.scenario.result",
                },
            )

            scenario_result_path.parent.mkdir(parents=True, exist_ok=True)
            capture_path.parent.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)
            scenario_result_path.write_text("{}\n", encoding="utf-8")
            capture_path.write_bytes(b"png")
            editor_log_path.write_text("editor log\n", encoding="utf-8")

            response_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                response_dir / f"{request_id}.json",
                {
                    "request_id": request_id,
                    "status": "ok",
                    "completed_at_utc": "2026-05-09T15:41:02Z",
                    "payload_type": "unity.scenario.result",
                    "payload_json": json.dumps(
                        {
                            "project_root": str(project_root),
                            "run_id": "run-1",
                            "scenario_name": "SampleScenario",
                            "status": "passed",
                            "duration_seconds": 4.0,
                            "result_path": str(scenario_result_path),
                            "steps": [
                                {
                                    "stepId": "capture",
                                    "payload_json": json.dumps(
                                        {
                                            "capture_source": "game_view",
                                            "file_path": str(capture_path),
                                        }
                                    ),
                                }
                            ],
                        },
                        separators=(",", ":"),
                    ),
                },
            )

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.scenario.result",
                poll_timeout_ms=0,
            )

            self.assertEqual("completed_ok", summary["operation_outcome"])
            self.assertEqual(4.0, summary["structured_timing"]["duration_seconds"])
            self.assertEqual("2026-05-09T15:40:58Z", summary["structured_timing"]["request_started_at_utc"])
            self.assertEqual("2026-05-09T15:41:02Z", summary["structured_timing"]["request_completed_at_utc"])
            self.assertEqual(3, len(summary["artifact_manifest"]["groups"]["request_journal"]))
            self.assertEqual(str(editor_log_path.resolve()), summary["artifact_manifest"]["groups"]["logs"][0]["path"])
            self.assertEqual(str(scenario_result_path.resolve()), summary["artifact_manifest"]["groups"]["scenario_results"][0]["path"])
            self.assertEqual("capture", summary["artifact_manifest"]["groups"]["captures"][0]["step_id"])
            self.assertTrue(summary["artifact_manifest"]["groups"]["captures"][0]["exists"])


if __name__ == "__main__":
    unittest.main()
