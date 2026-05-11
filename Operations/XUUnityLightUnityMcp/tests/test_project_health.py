import sys
import tempfile
import time
import unittest
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

from server_bridge_runtime import derive_busy_reason, heartbeat_age_seconds
from server_editor_host import classify_editor_log
from server_health import build_editor_log_diagnosis, classify_project_health


def heartbeat_utc(seconds_ago: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))


class ProjectHealthTests(unittest.TestCase):
    def test_classify_project_health_marks_fresh_when_heartbeat_is_recent(self) -> None:
        result = classify_project_health(
            bridge_state={
                "editor_pid": 101,
                "heartbeat_utc": heartbeat_utc(2),
                "health_status": "healthy",
            },
            discovery={
                "bridge_state_live": True,
                "host_session_live": True,
                "bridge_enabled": True,
                "detected_editor_count": 1,
                "bridge_pid_alive": True,
                "host_session_pid_alive": True,
                "reconciliation_recommended_next_action": "none",
            },
            editor_log_diagnosis={},
            heartbeat_age_seconds=heartbeat_age_seconds,
            derive_busy_reason=derive_busy_reason,
        )

        self.assertEqual("fresh", result["host_health_classification"])
        self.assertEqual("none", result["anr_classification"])
        self.assertEqual("observe_only", result["host_health_termination_policy"])

    def test_classify_project_health_marks_anr_suspected_without_progress_evidence(self) -> None:
        result = classify_project_health(
            bridge_state={
                "editor_pid": 101,
                "heartbeat_utc": heartbeat_utc(20),
                "health_status": "healthy",
            },
            discovery={
                "bridge_state_live": True,
                "host_session_live": True,
                "bridge_enabled": True,
                "detected_editor_count": 1,
                "bridge_pid_alive": True,
                "host_session_pid_alive": True,
                "reconciliation_recommended_next_action": "ensure_ready_or_recover_bridge",
            },
            editor_log_diagnosis={},
            heartbeat_age_seconds=heartbeat_age_seconds,
            derive_busy_reason=derive_busy_reason,
        )

        self.assertEqual("anr_suspected", result["host_health_classification"])
        self.assertEqual("anr_suspected", result["anr_classification"])
        self.assertEqual("inspect_editor_log_and_observe", result["host_health_recommended_next_action"])

    def test_classify_project_health_keeps_prolonged_lifecycle_churn_out_of_anr(self) -> None:
        result = classify_project_health(
            bridge_state={
                "editor_pid": 101,
                "heartbeat_utc": heartbeat_utc(35),
                "health_status": "healthy",
                "active_operation": "unity.project.refresh",
                "pending_request_count": 1,
                "refresh_settle_pending": True,
            },
            discovery={
                "bridge_state_live": True,
                "host_session_live": True,
                "bridge_enabled": True,
                "detected_editor_count": 1,
                "bridge_pid_alive": True,
                "host_session_pid_alive": True,
                "reconciliation_recommended_next_action": "ensure_ready_or_recover_bridge",
            },
            editor_log_diagnosis={
                "code": "lifecycle_activity_observed",
                "severity": "info",
                "summary": "Lifecycle activity observed.",
            },
            heartbeat_age_seconds=heartbeat_age_seconds,
            derive_busy_reason=derive_busy_reason,
        )

        self.assertEqual("stale", result["host_health_classification"])
        self.assertEqual("none", result["anr_classification"])
        self.assertIn("active_operation", result["host_health_progress_evidence"])

    def test_build_editor_log_diagnosis_detects_compile_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "compile_blocker.log"
            log_path.write_text(
                "Assets/Foo.cs(12,3): error CS1002: ; expected\n"
                "AssetDatabase: script compilation time: 1.234s\n",
                encoding="utf-8",
            )

            diagnosis = build_editor_log_diagnosis(
                log_path,
                startup_policy="fail_fast_on_interactive_compile_block",
                classify_editor_log=classify_editor_log,
            )

        self.assertEqual("interactive_compile_block_detected", diagnosis["code"])
        self.assertEqual("error", diagnosis["severity"])
        self.assertEqual("tail_fallback", diagnosis["scope"]["source"])
        self.assertTrue(diagnosis["scope"]["fallback_used"])

    def test_build_editor_log_diagnosis_detects_lifecycle_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "lifecycle_activity.log"
            log_path.write_text(
                "Begin MonoManager ReloadAssembly\n"
                "RefreshInfo: InitialScriptRefreshV2(NoUpdateAssetOptions)\n",
                encoding="utf-8",
            )

            diagnosis = build_editor_log_diagnosis(
                log_path,
                startup_policy="fail_fast_on_interactive_compile_block",
                classify_editor_log=classify_editor_log,
            )

        self.assertEqual("lifecycle_activity_observed", diagnosis["code"])
        self.assertEqual("info", diagnosis["severity"])

    def test_build_editor_log_diagnosis_uses_session_scope_when_offset_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "scoped_compile_blocker.log"
            prefix = "old stale line\n"
            scoped = "Assets/Foo.cs(12,3): error CS1002: ; expected\n"
            log_path.write_text(prefix + scoped, encoding="utf-8")

            diagnosis = build_editor_log_diagnosis(
                log_path,
                startup_policy="fail_fast_on_interactive_compile_block",
                classify_editor_log=classify_editor_log,
                session_start_offset_bytes=len(prefix),
                session_start_mtime=log_path.stat().st_mtime,
            )

        self.assertEqual("interactive_compile_block_detected", diagnosis["code"])
        self.assertEqual("host_opened_editor_session", diagnosis["scope"]["source"])
        self.assertFalse(diagnosis["scope"]["fallback_used"])
        self.assertEqual(len(prefix), diagnosis["scope"]["start_offset_bytes"])

    def test_build_editor_log_diagnosis_does_not_fallback_to_stale_tail_when_scoped_region_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "empty_scoped_region.log"
            stale_tail = "Assets/Foo.cs(12,3): error CS1002: ; expected\n"
            log_path.write_text(stale_tail, encoding="utf-8")

            diagnosis = build_editor_log_diagnosis(
                log_path,
                startup_policy="fail_fast_on_interactive_compile_block",
                classify_editor_log=classify_editor_log,
                session_start_offset_bytes=len(stale_tail),
                session_start_mtime=log_path.stat().st_mtime,
            )

        self.assertEqual({}, diagnosis)


if __name__ == "__main__":
    unittest.main()
