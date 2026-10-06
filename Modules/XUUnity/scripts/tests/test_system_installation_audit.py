from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
AUDIT = SCRIPTS_DIR / "system_installation_audit.py"
FIXTURE = (
    Path(__file__).resolve().parent
    / "system_installation_fixtures"
    / "healthy"
)
sys.path.insert(0, str(SCRIPTS_DIR))
import system_installation_audit  # noqa: E402


class SystemInstallationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.host = Path(self.tmp.name) / "Host"
        shutil.copytree(FIXTURE, self.host)
        self.air_root = self.host / "AIRoot"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _audit(self) -> dict[str, object]:
        return system_installation_audit.audit_installation(
            self.host,
            self.air_root,
            forbidden_tokens=("FixturePrivateIdentifier",),
            run_composed=False,
        )

    def _kinds(self, payload: dict[str, object]) -> set[str]:
        return {
            str(finding["kind"])
            for finding in payload["findings"]  # type: ignore[index]
        }

    def test_healthy_fixture_is_clean(self) -> None:
        payload = self._audit()
        self.assertEqual(payload["status"], "clean")
        self.assertEqual(payload["findings"], [])
        self.assertTrue(str(payload["publicModuleFingerprint"]).startswith("sha256:"))

    def test_repeat_run_is_deterministic(self) -> None:
        self.assertEqual(self._audit(), self._audit())

    def test_finding_ids_do_not_depend_on_other_findings(self) -> None:
        first = system_installation_audit.finalize_findings([
            {"kind": "z", "severity": "low", "path": "z", "message": "z"},
        ])[0]["id"]
        second = system_installation_audit.finalize_findings([
            {"kind": "a", "severity": "high", "path": "a", "message": "a"},
            {"kind": "z", "severity": "low", "path": "z", "message": "z"},
        ])[1]["id"]
        self.assertEqual(first, second)

    def test_unregistered_skill_family_is_reported(self) -> None:
        path = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "skills"
            / "orphan"
            / "README.md"
        )
        path.parent.mkdir()
        path.write_text("# Orphan family\n", encoding="utf-8")
        self.assertIn("skill_family_unregistered", self._kinds(self._audit()))

    def test_unreachable_owner_file_is_reported(self) -> None:
        path = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "knowledge"
            / "orphan.md"
        )
        path.write_text("# Orphan knowledge\n", encoding="utf-8")
        self.assertIn("unreachable_file", self._kinds(self._audit()))

    def test_module_index_omission_is_reported(self) -> None:
        path = self.air_root / "Modules" / "XUUnity" / "knowledge" / "new_owner.md"
        path.write_text("# New owner\n", encoding="utf-8")
        start = self.air_root / "Modules" / "XUUnity" / "tasks" / "start_session.md"
        start.write_text(start.read_text() + "\nRoute `knowledge/new_owner.md`.\n")
        self.assertIn("module_index_entry_missing", self._kinds(self._audit()))

    def test_broken_markdown_link_is_reported(self) -> None:
        readme = self.air_root / "Modules" / "XUUnity" / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\n[missing](missing.md)\n",
            encoding="utf-8",
        )
        self.assertIn("broken_markdown_link", self._kinds(self._audit()))

    def test_git_ignored_vendor_tree_does_not_affect_corpus(self) -> None:
        self._init_host_repo()
        (self.host / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        before = self._audit()["inventory"]["markdown"]
        vendor = self.air_root / "node_modules" / "vendor" / "README.md"
        vendor.parent.mkdir(parents=True)
        vendor.write_text("[missing](CONTRIBUTING.md)\n", encoding="utf-8")

        payload = self._audit()

        self.assertNotIn("broken_markdown_link", self._kinds(payload))
        self.assertEqual(before, payload["inventory"]["markdown"])

    def test_html_is_covered_by_private_identifier_scan(self) -> None:
        page = self.air_root / "docs" / "index.html"
        page.parent.mkdir()
        page.write_text("PrivateProject", encoding="utf-8")
        payload = system_installation_audit.audit_installation(
            self.host,
            self.air_root,
            forbidden_tokens=("PrivateProject",),
            run_composed=False,
        )
        self.assertIn("public_path_leak", self._kinds(payload))

    def test_test_fixture_is_covered_by_private_identifier_scan(self) -> None:
        fixture = self.air_root / "Modules" / "XUUnity" / "tests" / "private.json"
        fixture.parent.mkdir()
        fixture.write_text('{"name":"PrivateProject"}', encoding="utf-8")
        payload = system_installation_audit.audit_installation(
            self.host,
            self.air_root,
            forbidden_tokens=("PrivateProject",),
            run_composed=False,
        )
        self.assertIn("public_path_leak", self._kinds(payload))

    def test_duplicate_protected_heading_is_reported(self) -> None:
        entrypoint = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "tasks"
            / "start_session.md"
        )
        entrypoint.write_text(
            entrypoint.read_text(encoding="utf-8")
            + "\n## Skill Routing Hints\n",
            encoding="utf-8",
        )
        self.assertIn("duplicate_protected_heading", self._kinds(self._audit()))

    def test_conflicting_command_owners_are_reported(self) -> None:
        entrypoint = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "tasks"
            / "start_session.md"
        )
        entrypoint.write_text(
            entrypoint.read_text(encoding="utf-8")
            + "\n- `xuunity fixture ...` -> `utilities/one.md`\n"
            + "- `xuunity fixture ...` -> `utilities/two.md`\n",
            encoding="utf-8",
        )
        self.assertIn("conflicting_command_route", self._kinds(self._audit()))

    def test_generic_route_before_specific_route_is_reported(self) -> None:
        entrypoint = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "tasks"
            / "start_session.md"
        )
        entrypoint.write_text(
            entrypoint.read_text(encoding="utf-8")
            + "\n- `xuunity fixture ...` -> `utilities/one.md`\n"
            + "- `xuunity fixture exact ...` -> `utilities/one.md`\n",
            encoding="utf-8",
        )
        self.assertIn(
            "generic_route_precedes_specific",
            self._kinds(self._audit()),
        )

    def test_public_host_path_is_reported_without_echoing_it(self) -> None:
        private_value = "/" + "Users/privateaccount/private-repo"
        file_path = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "knowledge"
            / "decision_rules.md"
        )
        file_path.write_text(
            file_path.read_text(encoding="utf-8") + f"\n{private_value}\n",
            encoding="utf-8",
        )
        payload = self._audit()
        self.assertIn("public_path_leak", self._kinds(payload))
        self.assertNotIn(private_value, json.dumps(payload))

    def test_concrete_username_with_generic_tail_is_still_reported(self) -> None:
        file_path = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "knowledge"
            / "decision_rules.md"
        )
        file_path.write_text(
            file_path.read_text(encoding="utf-8") + "\n/" + "Users/alice/repo\n",
            encoding="utf-8",
        )
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_public_host_path_in_json_is_reported(self) -> None:
        config = self.air_root / "Modules" / "XUUnity" / "fixture-config.json"
        config.write_text(
            json.dumps({"root": "/" + "home/alice/project"}),
            encoding="utf-8",
        )
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def _git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.host), *arguments],
            capture_output=True,
            text=True,
            check=True,
        )

    def _init_host_repo(self) -> None:
        self._git("init", "-q")
        self._git("config", "user.email", "fixture@example.com")
        self._git("config", "user.name", "Fixture")

    def test_tracked_file_with_host_path_stays_a_public_leak(self) -> None:
        target = self.air_root / "Modules" / "XUUnity" / "knowledge" / "decision_rules.md"
        target.write_text(
            target.read_text(encoding="utf-8") + "\n/" + "Users/alice/repo\n",
            encoding="utf-8",
        )
        self._init_host_repo()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_ignored_untracked_file_is_outside_the_public_corpus(self) -> None:
        self._init_host_repo()
        (self.host / ".gitignore").write_text("*-setup-plan.json\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        scratch = self.air_root / "Modules" / "XUUnity" / "local-setup-plan.json"
        scratch.write_text(json.dumps({"root": "/" + "Users/alice/project"}), encoding="utf-8")
        kinds = self._kinds(self._audit())
        self.assertNotIn("local_scratch_path_leak", kinds)
        self.assertNotIn("public_path_leak", kinds)

    def test_untracked_but_unignored_file_stays_a_public_leak(self) -> None:
        self._init_host_repo()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        pending = self.air_root / "Modules" / "XUUnity" / "pending.json"
        pending.write_text(json.dumps({"root": "/" + "Users/alice/project"}), encoding="utf-8")
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_design_registry_drift_is_reported(self) -> None:
        registry = self.air_root / "Design" / "README.md"
        registry.write_text("# Fixture Design Registry\n", encoding="utf-8")
        self.assertIn("design_file_unregistered", self._kinds(self._audit()))

    def _write_router(self, size: int) -> None:
        (self.host / "AGENTS.md").write_bytes(b"x" * size)

    def _router_findings(self, payload: dict[str, object]) -> list[dict[str, str]]:
        return [
            finding
            for finding in payload["findings"]  # type: ignore[union-attr]
            if finding["path"] == "AGENTS.md"
        ]

    def test_router_with_headroom_beyond_margin_is_clean(self) -> None:
        window = system_installation_audit.ROUTER_READ_WINDOW_BYTES
        margin = system_installation_audit.ROUTER_HEADROOM_MARGIN_BYTES
        self._write_router(window - margin - 1)
        payload = self._audit()
        self.assertEqual(payload["status"], "clean")
        self.assertEqual(self._router_findings(payload), [])

    def test_router_within_headroom_margin_is_reported(self) -> None:
        window = system_installation_audit.ROUTER_READ_WINDOW_BYTES
        margin = system_installation_audit.ROUTER_HEADROOM_MARGIN_BYTES
        size = window - margin
        self._write_router(size)
        [finding] = self._router_findings(self._audit())
        self.assertEqual(finding["kind"], "router_read_window_headroom_low")
        self.assertEqual(finding["severity"], "medium")
        self.assertIn(f"{size} bytes", finding["message"])
        self.assertIn(f"{window}-byte", finding["message"])
        self.assertIn(f"headroom {margin} bytes", finding["message"])

    def test_router_larger_than_read_window_is_reported(self) -> None:
        window = system_installation_audit.ROUTER_READ_WINDOW_BYTES
        size = window + 10
        self._write_router(size)
        [finding] = self._router_findings(self._audit())
        self.assertEqual(finding["kind"], "router_exceeds_read_window")
        self.assertEqual(finding["severity"], "high")
        self.assertIn(f"{size} bytes", finding["message"])
        self.assertIn(f"{window}-byte", finding["message"])
        self.assertIn("headroom -10 bytes", finding["message"])

    def _audit_composed(self) -> dict[str, object]:
        return system_installation_audit.audit_installation(
            self.host,
            self.air_root,
            forbidden_tokens=("FixturePrivateIdentifier",),
            run_composed=True,
        )

    def _composed(self, payload: dict[str, object], check_id: str) -> dict[str, object]:
        return next(
            check
            for check in payload["composedChecks"]  # type: ignore[union-attr]
            if check["id"] == check_id
        )

    def _install_task_registry(self) -> None:
        scripts = self.air_root / "Modules" / "XUUnity" / "scripts"
        scripts.mkdir(exist_ok=True)
        shutil.copy2(SCRIPTS_DIR / "task_registry_tool.py", scripts)
        shutil.copytree(
            SCRIPTS_DIR / "templates" / "task_registry",
            scripts / "templates" / "task_registry",
        )
        for command in ("bootstrap", "reconcile"):
            self._registry(command)

    def _registry(self, *arguments: str) -> str:
        return subprocess.run(
            [
                sys.executable,
                str(self.air_root / "Modules" / "XUUnity" / "scripts" / "task_registry_tool.py"),
                *arguments,
                "--repo-root",
                str(self.host),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_valid_task_registry_is_a_clean_pass(self) -> None:
        self._install_task_registry()
        payload = self._audit_composed()
        check = self._composed(payload, "task_registry")
        self.assertEqual(check["status"], "pass")
        self.assertIsNone(check["warningCount"])
        self.assertEqual(payload["status"], "clean")

    def test_task_registry_warnings_are_not_a_clean_pass(self) -> None:
        self._install_task_registry()
        index = self.host / "AIOutput" / "Registry" / "task_index.yaml"
        index.write_text(index.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
        payload = self._audit_composed()
        check = self._composed(payload, "task_registry")
        self.assertEqual(check["status"], "pass_with_warnings")
        self.assertEqual(check["exitCode"], 0)
        self.assertEqual(check["warningCount"], 1)
        self.assertIn("1 warning(s)", str(check["summary"]))
        [finding] = [
            finding
            for finding in payload["findings"]  # type: ignore[union-attr]
            if finding["kind"] == "composed_check_warnings"
        ]
        self.assertEqual(finding["severity"], "low")
        self.assertEqual(finding["path"], "task_registry")
        self.assertEqual(payload["status"], "findings")

    def test_corrected_legacy_registry_values_stay_a_clean_pass(self) -> None:
        self._install_task_registry()
        self._registry(
            "start", "--project-id", "fixture", "--repo-id", "fixture",
            "--origin-ref", "fixture", "--task-kind", "bug", "--severity", "low",
            "--summary", "Fixture task",
        )
        events = self.host / "AIOutput" / "Registry" / "task_events.jsonl"
        started = json.loads(events.read_text(encoding="utf-8").splitlines()[-1])
        legacy = {**started, "task_kind": "bug_fix"}
        correction = {
            **started,
            "event_type": "audit_saved",
            "actor": "system",
            "origin_type": "manual",
            "summary": "Append-only metadata correction: fixture",
        }
        with events.open("a", encoding="utf-8") as handle:
            for event in (legacy, correction):
                handle.write(json.dumps(event) + "\n")
        self._registry("reconcile")
        self.assertIn("retained legacy value", self._registry("validate"))

        payload = self._audit_composed()
        check = self._composed(payload, "task_registry")
        self.assertEqual(check["status"], "pass")
        self.assertIsNone(check["warningCount"])
        self.assertEqual(payload["status"], "clean")

    def test_warning_status_is_parsed_only_for_warning_reporting_checks(self) -> None:
        stub = self.air_root / "scripts" / "routing_audit.py"
        stub.parent.mkdir()
        stub.write_text(
            "print('STATUS: valid_with_warnings')\n"
            "print('WARNINGS:')\n"
            "print('  - stub warning')\n",
            encoding="utf-8",
        )
        payload = self._audit_composed()
        check = self._composed(payload, "routing_audit")
        self.assertEqual(check["status"], "pass")
        self.assertIsNone(check["warningCount"])
        self.assertNotIn("composed_check_warnings", self._kinds(payload))

    def test_warning_count_reads_only_the_warnings_block(self) -> None:
        count = system_installation_audit.count_validation_warnings(
            "STATUS: valid_with_warnings\n"
            "VIOLATIONS:\n"
            "  - not a warning\n"
            "WARNINGS:\n"
            "  - first\n"
            "  - event[1].task_kind: retained legacy value 'old'; corrected\n"
            "  - second\n"
            "OK: trailer\n"
            "  - not a warning\n"
        )
        self.assertEqual(count, 2)
        self.assertIsNone(
            system_installation_audit.count_validation_warnings("STATUS: valid\nOK: 0 event(s)\n")
        )
        self.assertIsNone(
            system_installation_audit.count_validation_warnings(
                "STATUS: valid_with_warnings\n"
                "WARNINGS:\n"
                "  - event[1].task_kind: retained legacy value 'old'; corrected\n"
            )
        )

    def test_cli_emits_json_and_findings_exit_code(self) -> None:
        path = (
            self.air_root
            / "Modules"
            / "XUUnity"
            / "knowledge"
            / "orphan.md"
        )
        path.write_text("# Orphan knowledge\n", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--host-root",
                str(self.host),
                "--skip-composed-checks",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "findings")

    def test_cli_output_atomically_persists_same_json(self) -> None:
        output = self.host / "AIOutput" / "installation-audit.json"
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--host-root",
                str(self.host),
                "--skip-composed-checks",
                "--forbidden-token",
                "FixturePrivateIdentifier",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(output.read_text()))
        self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_cli_loads_default_denylist_without_exposing_values(self) -> None:
        denylist = self.host / ".xuunity-public-safety-denylist"
        denylist.write_text("PrivateProject\n", encoding="utf-8")
        target = self.air_root / "Modules" / "XUUnity" / "README.md"
        target.write_text(target.read_text(encoding="utf-8") + "\nPrivateProject\n")
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--host-root",
                str(self.host),
                "--skip-composed-checks",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertTrue(payload["boundaryScan"]["armed"])
        self.assertEqual(1, payload["boundaryScan"]["tokenCount"])
        self.assertTrue(payload["boundaryScan"]["sourceId"].startswith("sha256:"))
        self.assertNotIn("PrivateProject", result.stdout)

    def test_cli_reports_unarmed_boundary_scan(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--host-root",
                str(self.host),
                "--skip-composed-checks",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["boundaryScan"]["armed"])
        self.assertIn("boundary_scan_unarmed", self._kinds(payload))

    def test_cli_output_failure_is_invalid_without_path_disclosure(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--host-root",
                str(self.host),
                "--skip-composed-checks",
                "--output",
                str(self.host),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(payload["status"], "invalid")
        self.assertIn("output_write_failed", self._kinds(payload))
        self.assertNotIn(str(self.host), result.stdout)


if __name__ == "__main__":
    unittest.main()
