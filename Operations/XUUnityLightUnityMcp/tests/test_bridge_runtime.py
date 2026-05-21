import json
import os
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_build_bridge_stabilization_summary_treats_file_ipc_flow_as_usable(self) -> None:
        summary = server_bridge_runtime.build_bridge_stabilization_summary(
            {
                "transport": "file_ipc",
                "transport_listener_state": "",
                "health_status": "healthy",
                "pending_request_count": 0,
            }
        )

        self.assertTrue(summary["stabilized"])
        self.assertEqual("inactive", summary["transport_listener_state"])
        self.assertFalse(summary["listener_required"])
        self.assertEqual("usable", summary["request_flow_state"])
        self.assertTrue(summary["transport_ready_for_requests"])
        self.assertNotIn("transport_listener_not_ready", summary["blocking_reasons"])

    def test_resolve_bridge_transport_defaults_config_missing_transport_to_tcp_loopback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            write_json(
                server_bridge_runtime.bridge_config_path(project_root),
                {
                    "enabled": True,
                    "heartbeat_interval_ms": 2000,
                    "pump_interval_ms": 500,
                },
            )

            transport = server_bridge_runtime.resolve_bridge_transport(project_root)

        self.assertEqual("tcp_loopback", transport.name)

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
            self.assertEqual("unity_completed_confirmed", summary["result_trust_class"])
            self.assertEqual("settled_after_lifecycle_reset", summary["reclassified_status"])
            self.assertEqual("none", summary["recommended_next_action"])
            self.assertEqual(
                "confirmed_success_after_lifecycle_churn",
                summary["operator_verdict"]["status"],
            )
            self.assertFalse(summary["operator_verdict"]["should_retry"])
            self.assertEqual("continue", summary["operator_verdict"]["next_action"])
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
            self.assertEqual("wrapper_failed_unity_unproven", summary["result_trust_class"])
            self.assertEqual("verify_effect_or_retry", summary["recommended_next_action"])
            self.assertEqual("unity_completion_unproven", summary["operator_verdict"]["status"])
            self.assertTrue(summary["operator_verdict"]["should_retry"])
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

    def test_build_request_final_status_uses_persisted_playmode_result_when_response_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            result_dir = project_root / "Library" / "XUUnityLightMcp" / "state" / "test_results"
            request_id = "req-playmode-failed"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-15T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-15T10:00:01Z",
                    "started_at_utc": "2026-05-15T10:00:01Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                journal_dir / "03_request_completed.json",
                {
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-15T10:00:05Z",
                    "completed_at_utc": "2026-05-15T10:00:05Z",
                    "operation_status": "ok",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                result_dir / f"{request_id}.json",
                {
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "run_phase": "completed",
                    "started_at_utc": "2026-05-15T10:00:01Z",
                    "completed_at_utc": "2026-05-15T10:00:05Z",
                    "total": 2,
                    "passed": 1,
                    "failed": 1,
                    "skipped": 0,
                    "failures": [{"name": "Game.Tests.Fails", "message": "expected true"}],
                    "last_started_test": "Game.Tests.Fails",
                    "last_finished_test": "Game.Tests.Fails",
                    "last_progress_at_utc": "2026-05-15T10:00:04Z",
                },
            )

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.tests.run_playmode",
                poll_timeout_ms=0,
            )

            self.assertTrue(summary["result_payload_available"])
            self.assertEqual("persisted_test_result", summary["result_payload_source"])
            self.assertEqual("failed", summary["test_verdict"])
            self.assertEqual("unity_failed_confirmed", summary["result_trust_class"])
            self.assertEqual(2, summary["total"])
            self.assertEqual("Game.Tests.Fails", summary["first_failures"][0]["name"])
            self.assertTrue(summary["artifact_manifest"]["groups"]["test_outputs"][0]["exists"])

    def test_build_request_final_status_reports_unproven_playmode_when_payload_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            request_id = "req-playmode-missing"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-15T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-15T10:00:01Z",
                    "started_at_utc": "2026-05-15T10:00:01Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                journal_dir / "03_request_completed.json",
                {
                    "event_type": "request_completed",
                    "event_at_utc": "2026-05-15T10:00:05Z",
                    "completed_at_utc": "2026-05-15T10:00:05Z",
                    "operation_status": "ok",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )

            summary = server_bridge_runtime.build_request_final_status(
                project_root,
                request_id,
                "unity.tests.run_playmode",
                poll_timeout_ms=0,
            )

            self.assertFalse(summary["result_payload_available"])
            self.assertEqual("journal_only", summary["result_payload_source"])
            self.assertEqual("response_missing_after_completed_request", summary["result_payload_reason"])
            self.assertEqual("unity_unproven", summary["test_verdict"])
            self.assertEqual("wrapper_failed_unity_unproven", summary["result_trust_class"])

    def test_build_request_final_status_classifies_started_playmode_runtime_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            result_dir = project_root / "Library" / "XUUnityLightMcp" / "state" / "test_results"
            request_id = "req-playmode-timeout"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-15T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-15T10:00:01Z",
                    "started_at_utc": "2026-05-15T10:00:01Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                result_dir / f"{request_id}.json",
                {
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "run_phase": "running",
                    "started_at_utc": "2026-05-15T10:00:01Z",
                    "last_progress_at_utc": "2026-05-15T10:00:02Z",
                    "last_started_test": "Game.Tests.LongRunning",
                    "request_timeout_ms": 1000,
                    "runtime_timeout_ms": 1000,
                },
            )

            with mock.patch.object(server_bridge_runtime.time, "time", return_value=1778840000.0):
                summary = server_bridge_runtime.build_request_final_status(
                    project_root,
                    request_id,
                    "unity.tests.run_playmode",
                    current_state={"playmode_state": "playing"},
                    poll_timeout_ms=0,
                )

            self.assertEqual("runtime_timeout", summary["test_verdict"])
            self.assertEqual("runtime_timeout_after_test_start", summary["timeout_classification"])
            self.assertEqual("Game.Tests.LongRunning", summary["last_started_test"])
            self.assertTrue(summary["editor_cleanup_recommended"])
            self.assertIn("request-playmode-set", summary["cleanup_command"])
            self.assertIn("--action exit", summary["cleanup_command"])

    def test_build_request_final_status_does_not_call_pre_start_timeout_runtime_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            result_dir = project_root / "Library" / "XUUnityLightMcp" / "state" / "test_results"
            request_id = "req-playmode-before-start-timeout"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-15T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                },
            )
            write_json(
                result_dir / f"{request_id}.json",
                {
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "run_phase": "submitted",
                    "started_at_utc": "2026-05-15T10:00:00Z",
                    "request_timeout_ms": 1000,
                    "runtime_timeout_ms": 1000,
                },
            )

            with mock.patch.object(server_bridge_runtime.time, "time", return_value=1778840000.0):
                summary = server_bridge_runtime.build_request_final_status(
                    project_root,
                    request_id,
                    "unity.tests.run_playmode",
                    poll_timeout_ms=0,
                )

            self.assertEqual("unity_unproven", summary["test_verdict"])
            self.assertEqual("timeout_before_test_start", summary["timeout_classification"])
            self.assertFalse(summary["runtime_timeout_observed"])

    def test_build_request_final_status_returns_immediately_for_stable_request_abandoned_reclassification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            request_id = "req-abandoned"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-11T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 3,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-11T10:00:01Z",
                    "started_at_utc": "2026-05-11T10:00:01Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 3,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "03_request_abandoned.json",
                {
                    "event_id": "03",
                    "event_type": "request_abandoned",
                    "event_at_utc": "2026-05-11T10:00:08Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "reason": "domain_reload_before_request_completion",
                    "retryable": True,
                    "reclassified_status": "retryable_after_lifecycle_reset",
                    "bridge_generation": 4,
                    "bridge_session_id": "session-new",
                },
            )

            current_state = {
                "bridge_generation": 4,
                "bridge_session_id": "session-new",
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

            with mock.patch.object(server_bridge_runtime.time, "sleep", side_effect=AssertionError("unexpected sleep")):
                summary = server_bridge_runtime.build_request_final_status(
                    project_root,
                    request_id,
                    "unity.tests.run_playmode",
                    current_state=current_state,
                    poll_timeout_ms=5000,
                )

            self.assertTrue(summary["reclassified"])
            self.assertEqual("request_abandoned", summary["reclassified_event_type"])
            self.assertEqual("retryable_after_lifecycle_reset", summary["operation_outcome"])
            self.assertEqual("wrapper_failed_unity_unproven", summary["result_trust_class"])
            self.assertEqual("retry_request", summary["recommended_next_action"])
            self.assertEqual(1, summary["safe_retry_budget_total"])
            self.assertEqual(1, summary["safe_retry_budget_remaining"])
            self.assertFalse(summary["safe_retry_budget_exhausted"])
            self.assertTrue(summary["bridge_stabilization"]["safe_to_retry"])

    def test_recovered_response_waits_past_reclassification_until_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            request_id = "req-playmode-reset"
            response_path = (
                project_root
                / "Library"
                / "XUUnityLightMcp"
                / "outbox"
                / f"{request_id}.json"
            )
            write_json(
                response_path,
                {
                    "request_id": request_id,
                    "status": "ok",
                    "completed_at_utc": "2026-05-12T00:09:46Z",
                    "payload_type": "unity.tests.run_playmode",
                    "payload_json": json.dumps(
                        {
                            "status": "passed",
                            "total": 1,
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                        }
                    ),
                },
            )

            base_events = [
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-12T00:09:34Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 151,
                    "bridge_session_id": "session-old",
                },
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-12T00:09:35Z",
                    "started_at_utc": "2026-05-12T00:09:35Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 151,
                    "bridge_session_id": "session-old",
                },
                {
                    "event_id": "03",
                    "event_type": "request_reclassified",
                    "event_at_utc": "2026-05-12T00:09:45Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "reason": "bridge_generation_changed_before_response",
                    "retryable": True,
                    "reclassified_status": "retryable_after_lifecycle_reset",
                    "bridge_generation": 152,
                    "bridge_session_id": "session-new",
                },
            ]
            completed_event = {
                "event_id": "04",
                "event_type": "request_completed",
                "event_at_utc": "2026-05-12T00:09:46Z",
                "completed_at_utc": "2026-05-12T00:09:46Z",
                "operation_status": "ok",
                "request_id": request_id,
                "operation": "unity.tests.run_playmode",
                "bridge_generation": 152,
                "bridge_session_id": "session-new",
            }
            current_state = {
                "bridge_generation": 152,
                "bridge_session_id": "session-new",
                "transport": "tcp_loopback",
                "transport_listener_state": "listening",
                "health_status": "healthy",
                "pending_request_count": 0,
            }
            calls = {"count": 0}

            def fake_events(project_root_value: Path, request_id_value: str) -> list[dict[str, object]]:
                calls["count"] += 1
                if calls["count"] == 1:
                    return list(base_events)
                return [*base_events, completed_event]

            with (
                mock.patch.object(server_bridge_runtime, "read_request_journal_events", side_effect=fake_events),
                mock.patch.object(server_bridge_runtime.time, "sleep", return_value=None),
            ):
                response, final_status = server_bridge_runtime.try_recover_completed_response_after_reset(
                    project_root,
                    request_id=request_id,
                    operation="unity.tests.run_playmode",
                    current_state=current_state,
                    poll_timeout_ms=5000,
                )

            self.assertIsNotNone(response)
            self.assertEqual("ok", response["status"])
            self.assertEqual("completed_ok", final_status["operation_outcome"])
            self.assertEqual("unity_completed_confirmed", final_status["result_trust_class"])
            self.assertGreaterEqual(calls["count"], 2)
            self.assertFalse(response_path.exists())

    def test_build_lifecycle_reset_tool_error_carries_result_trust_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            journal_dir = project_root / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            request_id = "req-reset"

            write_json(
                journal_dir / "01_request_submitted.json",
                {
                    "event_id": "01",
                    "event_type": "request_submitted",
                    "event_at_utc": "2026-05-11T10:00:00Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 2,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "02_request_started.json",
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-11T10:00:01Z",
                    "started_at_utc": "2026-05-11T10:00:01Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "bridge_generation": 2,
                    "bridge_session_id": "session-old",
                },
            )
            write_json(
                journal_dir / "03_request_abandoned.json",
                {
                    "event_id": "03",
                    "event_type": "request_abandoned",
                    "event_at_utc": "2026-05-11T10:00:04Z",
                    "request_id": request_id,
                    "operation": "unity.tests.run_playmode",
                    "reason": "domain_reload_before_request_completion",
                    "retryable": True,
                    "reclassified_status": "retryable_after_lifecycle_reset",
                    "bridge_generation": 3,
                    "bridge_session_id": "session-new",
                },
            )

            error = server_bridge_runtime.build_lifecycle_reset_tool_error(
                project_root,
                request_id=request_id,
                operation="unity.tests.run_playmode",
                transport="tcp_loopback",
                initial_bridge_generation=2,
                initial_bridge_session_id="session-old",
                current_state={
                    "bridge_generation": 3,
                    "bridge_session_id": "session-new",
                    "transport": "tcp_loopback",
                    "transport_listener_state": "listening",
                    "health_status": "healthy",
                    "pending_request_count": 0,
                },
            )

            self.assertEqual("request_lifecycle_reset", error.code)
            self.assertEqual("wrapper_failed_unity_unproven", error.details["result_trust_class"])
            self.assertEqual("wrapper_failed_unity_unproven", error.details["request_final_status"]["result_trust_class"])
            self.assertEqual(1, error.details["safe_retry_budget_total"])


if __name__ == "__main__":
    unittest.main()
