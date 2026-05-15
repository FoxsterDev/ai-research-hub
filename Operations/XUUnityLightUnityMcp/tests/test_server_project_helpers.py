import json
import time
import threading
import types
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_DIR))

import server
import server_editor_host
from server_project_context import ensure_project_root as ensure_project_root_base
from server_registry import BridgeRegistry
from server_core import ToolInvocationError


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_unity_project(root: Path) -> Path:
    (root / "Assets").mkdir(parents=True, exist_ok=True)
    project_settings = root / "ProjectSettings"
    project_settings.mkdir(parents=True, exist_ok=True)
    (project_settings / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 6000.0.58f2\n", encoding="utf-8"
    )
    return root


class ServerProjectHelperTests(unittest.TestCase):
    def test_ensure_project_root_accepts_valid_unity_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            resolved = server.ensure_project_root(str(project_root))
            self.assertEqual(project_root.resolve(), resolved)

    def test_ensure_project_root_rejects_invalid_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_root = Path(tmp_dir) / "NotAProject"
            invalid_root.mkdir(parents=True, exist_ok=True)

            with self.assertRaises(ToolInvocationError) as ctx:
                server.ensure_project_root(str(invalid_root))

            self.assertEqual("project_not_found", ctx.exception.code)

    def test_open_unity_editor_reuses_recent_host_launch_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            unity_app = Path("/Applications/Unity.app")
            log_path = project_root / "Library" / "XUUnityLightMcp" / "logs" / "unity_editor.log"
            session = server_editor_host.build_host_editor_session_state(
                project_root,
                unity_app,
                log_path,
                background_open=True,
                editor_pid=0,
            )
            session["launch_in_progress"] = True
            server_editor_host.write_host_editor_session_state(project_root, session)

            with (
                mock.patch.object(server_editor_host, "try_read_live_editor_state", return_value=None),
                mock.patch.object(server_editor_host, "find_running_unity_editors_for_project", return_value=[]),
                mock.patch.object(server_editor_host.subprocess, "run") as run_mock,
                mock.patch.object(server_editor_host.subprocess, "Popen") as popen_mock,
            ):
                result = server_editor_host.open_unity_editor(project_root, log_path, unity_app, True)

            self.assertTrue(result["reused_existing_editor"])
            self.assertEqual("host_launch_in_progress", result["reused_via"])
            self.assertTrue(result["launch_in_progress"])
            run_mock.assert_not_called()
            popen_mock.assert_not_called()

    def test_find_latest_request_event_is_sorted_and_project_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            project_a = base / "ProjectA"
            project_b = base / "ProjectB"
            journal_a = project_a / "Library" / "XUUnityLightMcp" / "journal" / "requests"
            journal_b = project_b / "Library" / "XUUnityLightMcp" / "journal" / "requests"

            write_json(
                journal_a / "01.json",
                {
                    "event_id": "01",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T15:00:00Z",
                    "request_id": "a-1",
                    "operation": "unity.status",
                },
            )
            write_json(journal_a / "invalid.json", {"request_id": ""})
            (journal_a / "broken.json").write_text("{not-json", encoding="utf-8")
            write_json(
                journal_a / "02.json",
                {
                    "event_id": "02",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T16:00:00Z",
                    "request_id": "a-2",
                    "operation": "unity.status",
                },
            )
            write_json(
                journal_b / "01.json",
                {
                    "event_id": "01",
                    "event_type": "request_started",
                    "event_at_utc": "2026-05-09T17:00:00Z",
                    "request_id": "b-1",
                    "operation": "unity.status",
                },
            )

            latest_a = server.find_latest_request_event(project_a, ["unity.status"])
            latest_b = server.find_latest_request_event(project_b, ["unity.status"])

            self.assertIsNotNone(latest_a)
            self.assertEqual("a-2", latest_a["request_id"])
            self.assertEqual("02", latest_a["event_id"])
            self.assertIsNotNone(latest_b)
            self.assertEqual("b-1", latest_b["request_id"])

    def test_inspect_package_dependency_alignment_for_repo_local_file_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            package_dir = (
                repo_root
                / "AIRoot"
                / "Operations"
                / "XUUnityLightUnityMcp"
                / "templates"
                / "unity-package"
            )
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "package.json").write_text('{"name":"com.xuunity.light-mcp"}\n', encoding="utf-8")

            project_root = make_unity_project(repo_root / "MyProject")
            manifest_path = project_root / "Packages" / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "dependencies": {
                            "com.xuunity.light-mcp": "file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package"
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = server.inspect_package_dependency_alignment(project_root)

            self.assertEqual("file", result["dependency_mode"])
            self.assertEqual("aligned", result["alignment"])
            self.assertTrue(result["repo_local_package_source_present"])
            self.assertEqual(str(package_dir.resolve()), result["resolved_dependency_path"])

    def test_inspect_package_dependency_alignment_for_missing_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            manifest_path = project_root / "Packages" / "manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps({"dependencies": {}}, indent=2) + "\n", encoding="utf-8")

            result = server.inspect_package_dependency_alignment(project_root)

            self.assertEqual("dependency_missing", result["alignment"])
            self.assertIn("not declared", result["warning"])

    def test_bridge_registry_reuses_context_for_normalized_same_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            registry = BridgeRegistry(ensure_project_root=ensure_project_root_base)

            first = registry.get_or_discover(str(project_root))
            second = registry.get_or_discover(str(project_root / "."))

            self.assertIs(first, second)
            self.assertEqual(1, len(registry.list_active_contexts()))
            self.assertEqual(str(project_root.resolve()), first.instance_key)

    def test_bridge_registry_keeps_project_context_state_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            project_a = make_unity_project(base / "ProjectA")
            project_b = make_unity_project(base / "ProjectB")

            def refresh_context_state(project_root: Path) -> dict:
                marker = project_root.name
                return {
                    "last_bridge_state": {"project": marker, "editor_pid": 100 if marker == "ProjectA" else 200},
                    "last_host_editor_session_state": {"editor_pid": 1000 if marker == "ProjectA" else 2000},
                    "active_transport": "tcp_loopback",
                    "transport_metadata": {"transport_listener_state": "listening", "project": marker},
                    "last_seen_pid": 100 if marker == "ProjectA" else 200,
                    "last_seen_generation": 1 if marker == "ProjectA" else 2,
                    "last_seen_session_id": f"session-{marker}",
                    "last_refresh_utc": f"{marker}-refresh",
                    "last_refresh_unix": 10.0 if marker == "ProjectA" else 20.0,
                    "health_classification": f"healthy-{marker}",
                }

            registry = BridgeRegistry(
                ensure_project_root=ensure_project_root_base,
                refresh_context_state=refresh_context_state,
            )

            context_a = registry.get_or_discover(str(project_a))
            context_b = registry.get_or_discover(str(project_b))

            self.assertNotEqual(context_a.instance_key, context_b.instance_key)
            self.assertEqual("ProjectA", context_a.last_bridge_state["project"])
            self.assertEqual("ProjectB", context_b.last_bridge_state["project"])
            self.assertEqual("session-ProjectA", context_a.last_seen_session_id)
            self.assertEqual("session-ProjectB", context_b.last_seen_session_id)
            self.assertEqual(2, len(registry.list_active_contexts()))

    def test_bridge_registry_prunes_offline_idle_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            registry = BridgeRegistry(
                ensure_project_root=ensure_project_root_base,
                refresh_context_state=lambda _: {
                    "last_bridge_state": {},
                    "last_host_editor_session_state": {},
                    "discovery_details": {
                        "bridge_state_live": False,
                        "host_session_live": False,
                        "detected_editor_count": 0,
                    },
                },
                offline_context_max_idle_seconds=1.0,
                general_context_max_idle_seconds=9999.0,
            )

            context = registry.get_or_discover(str(project_root))
            context.last_access_unix = time.time() - 100.0

            pruned = registry.prune_stale_contexts()

            self.assertEqual(1, len(pruned))
            self.assertEqual("offline_idle_expired", pruned[0]["reason"])
            self.assertEqual([], registry.list_active_contexts())

    def test_bridge_registry_keeps_live_context_when_only_offline_idle_expires(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            registry = BridgeRegistry(
                ensure_project_root=ensure_project_root_base,
                refresh_context_state=lambda _: {
                    "last_bridge_state": {"editor_pid": 321},
                    "last_host_editor_session_state": {},
                    "last_seen_pid": 321,
                    "discovery_details": {
                        "bridge_state_live": True,
                        "host_session_live": False,
                        "detected_editor_count": 1,
                    },
                },
                offline_context_max_idle_seconds=1.0,
                general_context_max_idle_seconds=9999.0,
            )

            context = registry.get_or_discover(str(project_root))
            context.last_access_unix = time.time() - 100.0

            pruned = registry.prune_stale_contexts()

            self.assertEqual([], pruned)
            remaining = registry.list_active_contexts()
            self.assertEqual(1, len(remaining))
            self.assertEqual(str(project_root.resolve()), remaining[0].instance_key)

    def test_status_and_scenario_summaries_preserve_operation_evidence_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            structured_timing = {
                "operation": "unity.status",
                "request_id": "req-1",
                "request_submitted_at_utc": "2026-05-09T15:40:57Z",
                "request_started_at_utc": "2026-05-09T15:40:58Z",
                "request_completed_at_utc": "2026-05-09T15:40:59Z",
                "settled_at_utc": "",
                "duration_seconds": 1.0,
                "settle_duration_seconds": None,
                "host_round_trip_seconds": 1.2,
                "host_wait_duration_seconds": None,
            }
            artifact_manifest = {
                "operation": "unity.status",
                "request_id": "req-1",
                "artifact_count": 1,
                "existing_artifact_count": 1,
                "groups": {
                    "request_journal": [],
                    "logs": [],
                    "captures": [],
                    "scenario_results": [],
                    "compile_outputs": [],
                    "test_outputs": [],
                },
            }
            host_prerequisites = {
                "lane": "same_host_editor",
                "ready": True,
                "blocking_codes": [],
                "warning_codes": [],
                "checks": {
                    "bridge_enabled": {"ready": True, "status": "ready", "code": "none"},
                },
            }

            with (
                mock.patch.object(
                    server,
                    "current_project_context_discovery_details",
                    return_value={"host_prerequisites": host_prerequisites},
                ),
                mock.patch.object(
                    server,
                    "current_project_context_bridge_state",
                    return_value={
                        "bridge_generation": 3,
                        "bridge_session_id": "session-a",
                        "transport": "file_ipc",
                        "transport_listener_state": "",
                        "pending_request_count": 0,
                        "health_status": "healthy",
                    },
                ),
                mock.patch.object(
                    server,
                    "refresh_project_context",
                    return_value=mock.Mock(last_bridge_state={}),
                ),
                mock.patch.object(server, "pid_is_alive", return_value=True),
                mock.patch.object(server, "heartbeat_age_seconds", return_value=0.5),
                mock.patch.object(server, "derive_busy_reason", return_value="idle"),
                mock.patch.object(server, "summarize_state_for_error", return_value="ok"),
            ):
                status_summary = server.build_status_summary_from_context(
                    project_root,
                    {
                        "editor_running": True,
                        "mcp_reachable": True,
                        "health_status": "healthy",
                        "playmode_state": "edit",
                        "structured_timing": structured_timing,
                        "artifact_manifest": artifact_manifest,
                    },
                )
                scenario_summary = server.build_scenario_result_summary_from_context(
                    project_root,
                    {
                        "project_root": str(project_root),
                        "run_id": "run-1",
                        "scenario_name": "SampleScenario",
                        "status": "passed",
                        "terminal": True,
                        "succeeded": True,
                        "terminal_status": "passed",
                        "started_at_utc": "2026-05-09T15:40:58Z",
                        "completed_at_utc": "2026-05-09T15:40:59Z",
                        "duration_seconds": 1.0,
                        "steps": [],
                        "structured_timing": structured_timing,
                        "artifact_manifest": artifact_manifest,
                    },
                )

            self.assertEqual(structured_timing, status_summary["structured_timing"])
            self.assertEqual(artifact_manifest, status_summary["artifact_manifest"])
            self.assertEqual(host_prerequisites, status_summary["host_prerequisites"])
            self.assertEqual(structured_timing, scenario_summary["structured_timing"])
            self.assertEqual(artifact_manifest, scenario_summary["artifact_manifest"])
            self.assertEqual(host_prerequisites, scenario_summary["host_prerequisites"])

    def test_bridge_operation_requires_request_lock_matches_mutation_policy(self) -> None:
        self.assertTrue(server.bridge_operation_requires_request_lock("unity.project.refresh"))
        self.assertTrue(server.bridge_operation_requires_request_lock("unity.compile.matrix"))
        self.assertTrue(server.bridge_operation_requires_request_lock("unity.editor.quit"))
        self.assertFalse(server.bridge_operation_requires_request_lock("unity.status"))
        self.assertFalse(server.bridge_operation_requires_request_lock("unity.health.probe"))

    def test_run_in_project_request_lock_uses_lock_for_mutating_operation_only(self) -> None:
        events: list[str] = []

        class RecordingLock:
            def __enter__(self):
                events.append("enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("exit")
                return False

        context = types.SimpleNamespace(request_lock=RecordingLock())

        def callback() -> str:
            events.append("callback")
            return "ok"

        result = server.run_in_project_request_lock(context, "unity.project.refresh", callback)
        self.assertEqual("ok", result)
        self.assertEqual(["enter", "callback", "exit"], events)

        events.clear()
        result = server.run_in_project_request_lock(context, "unity.status", callback)
        self.assertEqual("ok", result)
        self.assertEqual(["callback"], events)

    def test_current_project_context_bridge_state_prefers_best_effort_and_falls_back_to_context(self) -> None:
        context = types.SimpleNamespace(
            last_bridge_state={"bridge_generation": 7, "transport": "file_ipc"},
            last_host_editor_session_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)
        project_root = Path("/tmp/FakeProject")

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
        ):
            fallback_state = server.current_project_context_bridge_state(project_root)
        self.assertEqual(7, fallback_state["bridge_generation"])

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value={"bridge_generation": 11, "transport": "tcp_loopback"}),
        ):
            best_effort_state = server.current_project_context_bridge_state(project_root)
        self.assertEqual(11, best_effort_state["bridge_generation"])
        self.assertEqual("tcp_loopback", best_effort_state["transport"])

    def test_current_project_context_host_session_state_uses_context_snapshot(self) -> None:
        context = types.SimpleNamespace(
            last_bridge_state={},
            last_host_editor_session_state={"editor_pid": 1234, "opened_by_host": True},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with mock.patch.object(server, "_BRIDGE_REGISTRY", registry):
            host_session = server.current_project_context_host_session_state(Path("/tmp/FakeProject"))

        self.assertEqual(1234, host_session["editor_pid"])
        self.assertTrue(host_session["opened_by_host"])

    def test_build_project_discovery_report_includes_context_cache_transport_state_and_state_groups(self) -> None:
        context = types.SimpleNamespace(
            instance_key="/tmp/FakeProject",
            last_seen_pid=4321,
            last_seen_generation=9,
            last_seen_session_id="session-z",
            active_transport="tcp_loopback",
            health_classification="fresh",
            transport_metadata={"transport_listener_state": "listening"},
            transport_state={"selection_scope": "per_project_context", "active_transport": "tcp_loopback"},
            state_groups={"bridge_identity": {"bridge_generation": 9}},
            created_unix=10.0,
            last_access_unix=20.0,
            last_refresh_unix=30.0,
            last_refresh_utc="2026-05-09T12:00:00Z",
            idle_seconds=lambda: 1.25,
            has_live_runtime_evidence=lambda: True,
            discovery_details={
                "host_health_classification": "fresh",
                "host_health_reason": "heartbeat_fresh",
                "host_health_recommended_next_action": "none",
                "host_health_termination_policy": "observe_only",
                "host_health_heartbeat_age_seconds": 0.5,
                "host_health_busy_reason": "idle",
                "host_health_progress_evidence": [],
                "anr_classification": "none",
                "discovery_classification": "bridge_live",
                "discovery_reason": "live_bridge_state_with_live_pid",
                "authoritative_state_source": "bridge_state",
                "reconciliation_case": "bridge_state_authoritative",
                "reconciliation_status": "healthy",
                "reconciliation_reason": "live_bridge_state_with_live_pid",
                "reconciliation_recommended_next_action": "none",
                "detected_editor_count": 1,
                "detected_editor_pids": [4321],
                "bridge_state_live": True,
                "host_session_live": False,
                "bridge_enabled": True,
                "host_prerequisites": {
                    "lane": "same_host_editor",
                    "ready": True,
                    "blocking_codes": [],
                    "warning_codes": [],
                    "checks": {},
                },
                "transport_state": {"selection_scope": "per_project_context", "active_transport": "tcp_loopback"},
                "state_groups": {"bridge_identity": {"bridge_generation": 9}},
            },
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with mock.patch.object(server, "_BRIDGE_REGISTRY", registry):
            report = server.build_project_discovery_report(Path("/tmp/FakeProject"))

        self.assertEqual("tcp_loopback", report["transport_state"]["active_transport"])
        self.assertEqual(9, report["state_groups"]["bridge_identity"]["bridge_generation"])
        self.assertEqual(10.0, report["context_cache"]["created_unix"])
        self.assertEqual(1.25, report["context_cache"]["idle_seconds"])
        self.assertTrue(report["context_cache"]["live_runtime_evidence"])
        self.assertTrue(report["host_prerequisites"]["ready"])

    def test_build_request_final_status_from_context_includes_discovery_and_reconciliation(self) -> None:
        context = types.SimpleNamespace(
            last_bridge_state={"bridge_generation": 7, "bridge_session_id": "session-a"},
            last_host_editor_session_state={},
            discovery_details={
                "discovery_classification": "editor_process_only",
                "discovery_reason": "project_matched_in_process_table",
                "authoritative_state_source": "process_table",
                "reconciliation_case": "live_process_only",
                "reconciliation_status": "degraded",
                "reconciliation_reason": "process_table_match_without_live_state_authority",
                "reconciliation_recommended_next_action": "recover_editor_session",
                "detected_editor_count": 1,
                "detected_editor_pids": [777],
            },
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
            mock.patch.object(
                server,
                "build_request_final_status",
                return_value={
                    "request_id": "req-1",
                    "request_completed": False,
                    "recommended_next_action": "retry_request",
                },
            ),
        ):
            summary = server.build_request_final_status_from_context(Path("/tmp/FakeProject"), "req-1", "unity.status", 0)

        self.assertEqual("editor_process_only", summary["discovery_classification"])
        self.assertEqual("live_process_only", summary["reconciliation_case"])
        self.assertEqual("recover_editor_session", summary["recommended_next_action"])

    def test_build_request_final_status_prefers_host_health_next_action_for_anr(self) -> None:
        context = types.SimpleNamespace(
            last_bridge_state={"bridge_generation": 7, "bridge_session_id": "session-a"},
            last_host_editor_session_state={},
            discovery_details={
                "host_health_classification": "anr_suspected",
                "host_health_reason": "heartbeat_stale_without_progress_evidence",
                "host_health_recommended_next_action": "inspect_editor_log_and_observe",
                "host_health_termination_policy": "observe_only",
                "host_health_heartbeat_age_seconds": 22.0,
                "host_health_busy_reason": "idle",
                "host_health_progress_evidence": [],
                "anr_classification": "anr_suspected",
                "discovery_classification": "bridge_live",
                "discovery_reason": "live_bridge_state_with_live_pid",
                "authoritative_state_source": "bridge_state",
                "reconciliation_case": "bridge_state_authoritative",
                "reconciliation_status": "healthy",
                "reconciliation_reason": "live_bridge_state_with_live_pid",
                "reconciliation_recommended_next_action": "none",
                "detected_editor_count": 1,
                "detected_editor_pids": [777],
            },
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
            mock.patch.object(
                server,
                "build_request_final_status",
                return_value={
                    "request_id": "req-2",
                    "request_completed": False,
                    "recommended_next_action": "wait_for_bridge_stabilization",
                },
            ),
        ):
            summary = server.build_request_final_status_from_context(Path("/tmp/FakeProject"), "req-2", "unity.status", 0)

        self.assertEqual("anr_suspected", summary["host_health_classification"])
        self.assertEqual("inspect_editor_log_and_observe", summary["recommended_next_action"])

    def test_build_scenario_result_summary_from_context_includes_discovery_and_reconciliation(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "host_health_classification": "stale",
                "host_health_reason": "live_editor_without_live_bridge_state",
                "host_health_recommended_next_action": "ensure_ready_or_recover_bridge",
                "host_health_termination_policy": "observe_only",
                "host_health_heartbeat_age_seconds": None,
                "host_health_busy_reason": "bridge_state_missing",
                "host_health_progress_evidence": [],
                "anr_classification": "none",
                "discovery_classification": "host_session_live",
                "discovery_reason": "host_editor_session_with_live_pid",
                "authoritative_state_source": "host_editor_session",
                "reconciliation_case": "stale_bridge_state",
                "reconciliation_status": "degraded",
                "reconciliation_reason": "live_host_session_overrides_stale_bridge_state",
                "reconciliation_recommended_next_action": "recover_editor_session",
                "detected_editor_count": 1,
                "detected_editor_pids": [202],
            },
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with mock.patch.object(server, "_BRIDGE_REGISTRY", registry):
            summary = server.build_scenario_result_summary_from_context(
                Path("/tmp/FakeProject"),
                {
                    "run_id": "run-1",
                    "scenario_name": "SampleScenario",
                    "status": "running",
                    "terminal": False,
                },
            )

        self.assertEqual("host_session_live", summary["discovery_classification"])
        self.assertEqual("stale_bridge_state", summary["reconciliation_case"])
        self.assertEqual("stale", summary["host_health_classification"])
        self.assertEqual("ensure_ready_or_recover_bridge", summary["recommended_next_action"])

    def test_call_unity_scenario_results_list_tool_reads_persisted_results_with_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            results_root = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results"
            capture_path = project_root / "Library" / "XUUnityLightMcp" / "captures" / "capture.png"
            capture_path.parent.mkdir(parents=True, exist_ok=True)
            capture_path.write_bytes(b"png")

            write_json(
                results_root / "older.json",
                {
                    "project_root": str(project_root),
                    "run_id": "run-older",
                    "scenario_name": "SampleScenario",
                    "status": "passed",
                    "started_at_utc": "2026-05-09T15:40:00Z",
                    "completed_at_utc": "2026-05-09T15:40:05Z",
                    "duration_seconds": 5.0,
                    "result_path": str((results_root / "older.json").resolve()),
                    "steps": [],
                },
            )
            write_json(
                results_root / "latest.json",
                {
                    "project_root": str(project_root),
                    "run_id": "run-latest",
                    "scenario_name": "SampleScenario",
                    "status": "passed",
                    "started_at_utc": "2026-05-09T15:42:00Z",
                    "completed_at_utc": "2026-05-09T15:42:08Z",
                    "duration_seconds": 8.0,
                    "result_path": str((results_root / "latest.json").resolve()),
                    "steps": [
                        {
                            "stepId": "capture",
                            "payload_json": json.dumps(
                                {"capture_source": "game_view", "file_path": str(capture_path.resolve())},
                                ensure_ascii=True,
                            ),
                        }
                    ],
                },
            )
            write_json(
                results_root / "other.json",
                {
                    "project_root": str(project_root),
                    "run_id": "run-other",
                    "scenario_name": "OtherScenario",
                    "status": "failed",
                    "started_at_utc": "2026-05-09T15:43:00Z",
                    "completed_at_utc": "2026-05-09T15:43:03Z",
                    "duration_seconds": 3.0,
                    "result_path": str((results_root / "other.json").resolve()),
                    "steps": [],
                },
            )

            result = server.call_unity_scenario_results_list_tool(
                {
                    "projectRoot": str(project_root),
                    "scenarioName": "SampleScenario",
                    "limit": 10,
                }
            )

            structured = result["structuredContent"]
            self.assertFalse(result["isError"])
            self.assertEqual("unity_scenario_results_list", structured["action"])
            self.assertEqual(2, structured["total_results"])
            self.assertEqual(2, structured["returned_results"])
            self.assertEqual("run-latest", structured["results"][0]["run_id"])
            self.assertIn("structured_timing", structured["results"][0])
            self.assertIn("artifact_manifest", structured["results"][0])
            self.assertEqual(
                str(capture_path.resolve()),
                structured["results"][0]["artifact_manifest"]["groups"]["captures"][0]["path"],
            )

    def test_call_unity_scenario_result_latest_tool_returns_latest_filtered_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            results_root = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results"
            write_json(
                results_root / "first.json",
                {
                    "project_root": str(project_root),
                    "run_id": "run-1",
                    "scenario_name": "SampleScenario",
                    "status": "passed",
                    "started_at_utc": "2026-05-09T15:40:00Z",
                    "completed_at_utc": "2026-05-09T15:40:05Z",
                    "duration_seconds": 5.0,
                    "result_path": str((results_root / "first.json").resolve()),
                    "steps": [],
                },
            )
            write_json(
                results_root / "second.json",
                {
                    "project_root": str(project_root),
                    "run_id": "run-2",
                    "scenario_name": "SampleScenario",
                    "status": "failed",
                    "started_at_utc": "2026-05-09T15:41:00Z",
                    "completed_at_utc": "2026-05-09T15:41:07Z",
                    "duration_seconds": 7.0,
                    "result_path": str((results_root / "second.json").resolve()),
                    "steps": [],
                },
            )

            result = server.call_unity_scenario_result_latest_tool(
                {
                    "projectRoot": str(project_root),
                    "scenarioName": "SampleScenario",
                }
            )

            structured = result["structuredContent"]
            self.assertFalse(result["isError"])
            self.assertEqual("unity_scenario_result_latest", structured["action"])
            self.assertTrue(structured["lookup_found"])
            self.assertEqual("run-2", structured["run_id"])
            self.assertEqual("failed", structured["status"])
            self.assertIn("artifact_manifest", structured)
            self.assertIn("structured_timing", structured)

    def test_enrich_error_details_with_discovery_adds_recovery_command(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "discovery_classification": "bridge_disabled",
                "discovery_reason": "bridge_disabled_in_project_config",
                "authoritative_state_source": "bridge_config",
                "reconciliation_case": "bridge_disabled",
                "reconciliation_status": "offline",
                "reconciliation_reason": "bridge_disabled_in_project_config",
                "reconciliation_recommended_next_action": "enable_bridge_and_retry",
                "detected_editor_count": 0,
                "detected_editor_pids": [],
                "host_prerequisites": {
                    "lane": "same_host_editor",
                    "ready": False,
                    "blocking_codes": ["bridge_disabled"],
                    "warning_codes": [],
                    "checks": {},
                },
            }
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with mock.patch.object(server, "_BRIDGE_REGISTRY", registry):
            details = server.enrich_error_details_with_discovery(
                Path("/tmp/FakeProject"),
                {"recommended_next_action": "inspect_request_journal"},
            )

        self.assertEqual("bridge_disabled", details["discovery_classification"])
        self.assertEqual("enable_bridge_and_retry", details["recommended_next_action"])
        self.assertIn("init_xuunity_light_unity_mcp.sh", details["recommended_recovery_command"])
        self.assertEqual(["bridge_disabled"], details["host_prerequisites"]["blocking_codes"])

    def test_recover_project_bridge_for_reconciliation_raises_guided_bridge_disabled_error(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "reconciliation_case": "bridge_disabled",
                "reconciliation_status": "offline",
                "reconciliation_recommended_next_action": "enable_bridge_and_retry",
                "discovery_classification": "bridge_disabled",
                "discovery_reason": "bridge_disabled_in_project_config",
                "authoritative_state_source": "bridge_config",
                "detected_editor_count": 0,
                "detected_editor_pids": [],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
        ):
            with self.assertRaises(ToolInvocationError) as ctx:
                server.recover_project_bridge_for_reconciliation(
                    Path("/tmp/FakeProject"),
                    timeout_ms=5000,
                    heartbeat_max_age_seconds=5,
                    startup_policy="fail_fast_on_interactive_compile_block",
                    allow_open_editor=True,
                )

        self.assertEqual("bridge_disabled", ctx.exception.code)
        self.assertEqual("enable_bridge_and_retry", ctx.exception.details["recommended_next_action"])
        self.assertIn("init_xuunity_light_unity_mcp.sh", ctx.exception.details["recommended_recovery_command"])

    def test_recover_project_bridge_for_reconciliation_activates_live_process_only_editor(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "reconciliation_case": "live_process_only",
                "reconciliation_status": "degraded",
                "reconciliation_recommended_next_action": "ensure_ready_or_recover_bridge",
                "detected_editor_count": 1,
                "detected_editor_pids": [777],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
            mock.patch.object(server, "activate_unity_editor", return_value={"activated": True}) as activate_mock,
            mock.patch.object(server, "wait_for_ready", return_value={"editor_pid": 777, "health_status": "healthy"}) as wait_mock,
            mock.patch.object(server, "refresh_project_context", return_value=context),
        ):
            recovery = server.recover_project_bridge_for_reconciliation(
                Path("/tmp/FakeProject"),
                timeout_ms=5000,
                heartbeat_max_age_seconds=5,
                startup_policy="fail_fast_on_interactive_compile_block",
                allow_open_editor=False,
            )

        self.assertEqual("activated_existing_editor", recovery["action"])
        activate_mock.assert_called_once()
        wait_mock.assert_called_once()

    def test_execute_host_health_recovery_policy_observe_only_does_not_terminate(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "host_health_classification": "anr_suspected",
                "host_health_termination_policy": "observe_only",
                "host_health_recommended_next_action": "inspect_editor_log_and_observe",
                "bridge_pid": 777,
                "detected_editor_pids": [777],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "terminate_editor_pid") as terminate_mock,
        ):
            recovery = server.execute_host_health_recovery_policy(
                Path("/tmp/FakeProject"),
                timeout_ms=5000,
                startup_policy="fail_fast_on_interactive_compile_block",
                allow_open_editor=True,
            )

        self.assertEqual("observe_only", recovery["action"])
        terminate_mock.assert_not_called()

    def test_execute_host_health_recovery_policy_defers_termination_without_open_permission(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "host_health_classification": "anr",
                "host_health_termination_policy": "graceful_terminate",
                "host_health_recommended_next_action": "inspect_editor_log_and_consider_graceful_restart",
                "bridge_pid": 777,
                "detected_editor_pids": [777],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "terminate_editor_pid") as terminate_mock,
        ):
            recovery = server.execute_host_health_recovery_policy(
                Path("/tmp/FakeProject"),
                timeout_ms=5000,
                startup_policy="fail_fast_on_interactive_compile_block",
                allow_open_editor=False,
            )

        self.assertEqual("termination_deferred_no_open", recovery["action"])
        terminate_mock.assert_not_called()

    def test_execute_host_health_recovery_policy_terminates_and_reopens_for_anr(self) -> None:
        context = types.SimpleNamespace(
            discovery_details={
                "host_health_classification": "anr",
                "host_health_termination_policy": "graceful_terminate",
                "host_health_recommended_next_action": "inspect_editor_log_and_consider_graceful_restart",
                "bridge_pid": 777,
                "detected_editor_pids": [777],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "terminate_editor_pid", return_value=True) as terminate_mock,
            mock.patch.object(server, "detect_unity_app_path_for_project", return_value=Path("/Applications/Unity.app")),
            mock.patch.object(server, "open_unity_editor", return_value={"editor_pid": 888, "reused_existing_editor": False}) as open_mock,
            mock.patch.object(server, "wait_for_ready", return_value={"editor_pid": 888, "health_status": "healthy"}) as wait_mock,
            mock.patch.object(server, "update_host_editor_session_pid") as update_mock,
            mock.patch.object(server, "refresh_project_context", return_value=context),
        ):
            recovery = server.execute_host_health_recovery_policy(
                Path("/tmp/FakeProject"),
                timeout_ms=5000,
                startup_policy="fail_fast_on_interactive_compile_block",
                allow_open_editor=True,
            )

        self.assertEqual("terminated_and_reopened", recovery["action"])
        terminate_mock.assert_called_once_with(777, 5000)
        open_mock.assert_called_once()
        wait_mock.assert_called_once()
        update_mock.assert_called_once_with(Path("/tmp/FakeProject"), 888)

    def test_wait_for_scenario_result_attempts_recovery_on_editor_not_running(self) -> None:
        success_response = {
            "status": "ok",
            "payload_type": "unity.scenario.result",
            "payload_json": json.dumps(
                {
                    "run_id": "run-1",
                    "scenario_name": "SampleScenario",
                    "status": "passed",
                    "project_root": "/tmp/FakeProject",
                },
                ensure_ascii=True,
            ),
        }
        context = types.SimpleNamespace(
            discovery_details={
                "discovery_classification": "editor_process_only",
                "discovery_reason": "project_matched_in_process_table",
                "authoritative_state_source": "process_table",
                "reconciliation_case": "live_process_only",
                "reconciliation_status": "degraded",
                "reconciliation_reason": "process_table_match_without_live_state_authority",
                "reconciliation_recommended_next_action": "ensure_ready_or_recover_bridge",
                "detected_editor_count": 1,
                "detected_editor_pids": [777],
            },
            last_bridge_state={},
        )
        registry = types.SimpleNamespace(refresh_context=lambda _: context)

        with (
            mock.patch.object(server, "_BRIDGE_REGISTRY", registry),
            mock.patch.object(server, "try_read_live_editor_state", return_value=None),
            mock.patch.object(
                server,
                "invoke_bridge",
                side_effect=[
                    ToolInvocationError("editor_not_running", "editor offline"),
                    success_response,
                ],
            ) as invoke_mock,
            mock.patch.object(server, "recover_project_bridge_for_reconciliation", return_value={"action": "activated_existing_editor"}) as recovery_mock,
            mock.patch.object(server, "read_best_effort_bridge_state", return_value=None),
            mock.patch.object(server, "time", wraps=server.time) as time_module_mock,
        ):
            time_module_mock.sleep = mock.Mock()
            payload = server.wait_for_scenario_result(
                Path("/tmp/FakeProject"),
                "run-1",
                "SampleScenario",
                timeout_ms=5000,
                poll_interval_ms=10,
            )

        self.assertEqual("passed", payload["status"])
        self.assertEqual(1, payload["recovery_attempt_count"])
        self.assertEqual("live_process_only", payload["reconciliation_case"])
        self.assertEqual(2, invoke_mock.call_count)
        recovery_mock.assert_called_once()

    def test_wait_for_scenario_result_recovers_terminal_persisted_result_after_poll_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            results_root = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results"
            result_path = results_root / "run-1.json"
            write_json(
                result_path,
                {
                    "project_root": str(project_root),
                    "run_id": "run-1",
                    "scenario_name": "SampleScenario",
                    "status": "passed",
                    "started_at_utc": "2026-05-15T12:00:00Z",
                    "completed_at_utc": "2026-05-15T12:00:02Z",
                    "duration_seconds": 2.0,
                    "steps": [],
                },
            )

            with (
                mock.patch.object(server, "current_project_context_discovery_details", return_value={}),
                mock.patch.object(server, "invoke_bridge") as invoke_mock,
            ):
                payload = server.wait_for_scenario_result(
                    project_root,
                    "run-1",
                    "SampleScenario",
                    timeout_ms=0,
                    poll_interval_ms=10,
                )

            invoke_mock.assert_not_called()
            self.assertEqual("passed", payload["status"])
            self.assertTrue(payload["scenario_result_reconciled_from_persisted"])
            self.assertEqual("terminal_persisted_result_after_poll_timeout", payload["scenario_result_reconciliation_reason"])
            self.assertEqual("run_id", payload["scenario_result_lookup_strategy"])
            self.assertEqual(str(result_path.resolve()), payload["result_path"])
            self.assertEqual("none", payload["recommended_next_action"])

    def test_wait_for_scenario_result_timeout_reports_latest_persisted_recovery_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            results_root = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results"
            result_path = results_root / "run-1.json"
            write_json(
                result_path,
                {
                    "project_root": str(project_root),
                    "run_id": "run-1",
                    "scenario_name": "SampleScenario",
                    "status": "running",
                    "started_at_utc": "2026-05-15T12:00:00Z",
                    "updated_at_utc": "2026-05-15T12:00:01Z",
                    "steps": [],
                },
            )

            with (
                mock.patch.object(server, "current_project_context_discovery_details", return_value={}),
                mock.patch.object(server, "enrich_tool_invocation_error_with_discovery", side_effect=lambda _, exc: exc),
                mock.patch.object(server, "invoke_bridge") as invoke_mock,
            ):
                with self.assertRaises(ToolInvocationError) as raised:
                    server.wait_for_scenario_result(
                        project_root,
                        "run-1",
                        "SampleScenario",
                        timeout_ms=0,
                        poll_interval_ms=10,
                    )

            invoke_mock.assert_not_called()
            self.assertEqual("scenario_wait_timeout", raised.exception.code)
            details = raised.exception.details
            self.assertTrue(details["persisted_scenario_result_lookup_found"])
            self.assertFalse(details["persisted_scenario_result_terminal_found"])
            self.assertEqual("running", details["latest_persisted_scenario_status"])
            self.assertEqual(str(result_path.resolve()), details["latest_persisted_scenario_result_path"])
            self.assertIn("request-scenario-result-summary", details["scenario_recovery_command"])
            self.assertIn("--run-id run-1", details["scenario_recovery_command"])

    def test_wait_for_scenario_result_reconciles_by_scenario_name_when_run_id_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = make_unity_project(Path(tmp_dir) / "MyProject")
            results_root = project_root / "Library" / "XUUnityLightMcp" / "scenarios" / "results"
            write_json(
                results_root / "other.json",
                {
                    "project_root": str(project_root),
                    "run_id": "other-run",
                    "scenario_name": "OtherScenario",
                    "status": "passed",
                    "started_at_utc": "2026-05-15T12:00:00Z",
                    "completed_at_utc": "2026-05-15T12:00:01Z",
                    "steps": [],
                },
            )
            write_json(
                results_root / "sample.json",
                {
                    "project_root": str(project_root),
                    "run_id": "sample-run",
                    "scenario_name": "SampleScenario",
                    "status": "failed",
                    "started_at_utc": "2026-05-15T12:01:00Z",
                    "completed_at_utc": "2026-05-15T12:01:03Z",
                    "steps": [],
                },
            )

            with (
                mock.patch.object(server, "current_project_context_discovery_details", return_value={}),
                mock.patch.object(server, "invoke_bridge") as invoke_mock,
            ):
                payload = server.wait_for_scenario_result(
                    project_root,
                    "",
                    "SampleScenario",
                    timeout_ms=0,
                    poll_interval_ms=10,
                )

            invoke_mock.assert_not_called()
            self.assertEqual("failed", payload["status"])
            self.assertTrue(payload["scenario_result_reconciled_from_persisted"])
            self.assertEqual("scenario_name", payload["scenario_result_lookup_strategy"])
            self.assertEqual("sample-run", payload["run_id"])
            self.assertEqual("inspect_persisted_scenario_failure", payload["recommended_next_action"])

    def test_status_summary_reports_active_test_progress_age_and_elapsed_runtime(self) -> None:
        summary = server.build_status_summary(
            Path("/tmp/FakeProject"),
            {
                "editor_pid": 123,
                "editor_running": True,
                "mcp_reachable": True,
                "active_test_request_id": "req-test",
                "active_test_operation": "unity.tests.run_playmode",
                "active_test_run_phase": "running",
                "active_test_started_at_utc": "2026-05-15T12:00:00Z",
                "active_test_last_started_test": "Package.PlayMode.Sample",
                "active_test_last_progress_at_utc": "2026-05-15T12:00:10Z",
                "active_test_runtime_timeout_ms": 240000,
            },
            read_best_effort_bridge_state=lambda _: {},
            try_read_bridge_state=lambda _: {},
            pid_is_alive=lambda _: True,
            heartbeat_age_seconds=lambda _: 1.0,
            derive_busy_reason=lambda _: "tests_running",
            summarize_state_for_error=lambda _: "tests_running",
        )

        self.assertEqual("req-test", summary["active_test_request_id"])
        self.assertEqual("running", summary["active_test_run_phase"])
        self.assertEqual("2026-05-15T12:00:00Z", summary["active_test_started_at_utc"])
        self.assertIsNotNone(summary["active_test_elapsed_runtime_seconds"])
        self.assertIsNotNone(summary["active_test_last_progress_age_seconds"])
        self.assertEqual(240000, summary["active_test_runtime_timeout_ms"])

    def test_run_in_project_request_lock_serializes_same_project_mutations(self) -> None:
        context = types.SimpleNamespace(request_lock=threading.Lock())
        entry_order: list[str] = []
        finished: list[str] = []
        first_entered = threading.Event()
        release_first = threading.Event()
        second_entered = threading.Event()

        def first_callback() -> str:
            entry_order.append("first")
            first_entered.set()
            release_first.wait(timeout=2.0)
            finished.append("first")
            return "first"

        def second_callback() -> str:
            entry_order.append("second")
            second_entered.set()
            finished.append("second")
            return "second"

        first_thread = threading.Thread(
            target=lambda: server.run_in_project_request_lock(context, "unity.project.refresh", first_callback)
        )
        second_thread = threading.Thread(
            target=lambda: server.run_in_project_request_lock(context, "unity.project.refresh", second_callback)
        )

        first_thread.start()
        self.assertTrue(first_entered.wait(timeout=2.0))
        second_thread.start()

        self.assertFalse(second_entered.wait(timeout=0.2))
        release_first.set()
        first_thread.join(timeout=2.0)
        second_thread.join(timeout=2.0)

        self.assertEqual(["first", "second"], entry_order)
        self.assertEqual(["first", "second"], finished)

    def test_run_in_project_request_lock_allows_cross_project_independence(self) -> None:
        context_a = types.SimpleNamespace(request_lock=threading.Lock())
        context_b = types.SimpleNamespace(request_lock=threading.Lock())
        first_entered = threading.Event()
        second_entered = threading.Event()
        release_both = threading.Event()
        entry_order: list[str] = []

        def callback_a() -> str:
            entry_order.append("a")
            first_entered.set()
            release_both.wait(timeout=2.0)
            return "a"

        def callback_b() -> str:
            entry_order.append("b")
            second_entered.set()
            release_both.wait(timeout=2.0)
            return "b"

        thread_a = threading.Thread(
            target=lambda: server.run_in_project_request_lock(context_a, "unity.project.refresh", callback_a)
        )
        thread_b = threading.Thread(
            target=lambda: server.run_in_project_request_lock(context_b, "unity.project.refresh", callback_b)
        )

        thread_a.start()
        self.assertTrue(first_entered.wait(timeout=2.0))
        thread_b.start()
        self.assertTrue(second_entered.wait(timeout=2.0))

        release_both.set()
        thread_a.join(timeout=2.0)
        thread_b.join(timeout=2.0)

        self.assertCountEqual(["a", "b"], entry_order)

    def test_find_running_unity_editors_for_project_ignores_unity_hub_launcher(self) -> None:
        project_root = Path("/Users/test/ProjectA")
        commands = [
            (
                101,
                "/Applications/Unity Hub.app/Contents/MacOS/Unity Hub -- --silent -- -projectPath "
                f"{project_root} -logFile /tmp/editor.log",
            ),
            (
                202,
                "/Applications/Unity/Hub/Editor/6000.0.58f2/Unity.app/Contents/MacOS/Unity "
                f"-projectPath {project_root} -logFile /tmp/editor.log",
            ),
        ]

        with (
            mock.patch.object(server_editor_host, "list_process_commands", return_value=commands),
            mock.patch.object(server_editor_host, "pid_is_alive", return_value=True),
        ):
            matches = server_editor_host.find_running_unity_editors_for_project(project_root)

        self.assertEqual(1, len(matches))
        self.assertEqual(202, matches[0]["pid"])
        self.assertEqual("6000.0.58f2", matches[0]["unity_version"])

    def test_find_running_unity_editors_for_project_requires_exact_project_path_argument(self) -> None:
        project_root = Path("/Users/test/ProjectA")
        commands = [
            (
                202,
                "/Applications/Unity/Hub/Editor/6000.0.58f2/Unity.app/Contents/MacOS/Unity "
                '-projectPath "/Users/test/ProjectA-Shadow" -logFile /tmp/editor.log',
            ),
        ]

        with (
            mock.patch.object(server_editor_host, "list_process_commands", return_value=commands),
            mock.patch.object(server_editor_host, "pid_is_alive", return_value=True),
        ):
            matches = server_editor_host.find_running_unity_editors_for_project(project_root)

        self.assertEqual([], matches)

    def test_extract_unity_project_path_from_command_supports_quoted_paths(self) -> None:
        command = (
            '/Applications/Unity/Hub/Editor/6000.0.58f2/Unity.app/Contents/MacOS/Unity '
            '-projectPath "/Users/test/My Project" -logFile /tmp/editor.log'
        )

        result = server_editor_host.extract_unity_project_path_from_command(command)

        self.assertEqual("/Users/test/My Project", result)


if __name__ == "__main__":
    unittest.main()
