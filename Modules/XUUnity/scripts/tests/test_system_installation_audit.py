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

    def test_broken_markdown_link_is_reported(self) -> None:
        readme = self.air_root / "Modules" / "XUUnity" / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\n[missing](missing.md)\n",
            encoding="utf-8",
        )
        self.assertIn("broken_markdown_link", self._kinds(self._audit()))

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
        private_value = "/Users/privateaccount/private-repo"
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
            file_path.read_text(encoding="utf-8") + "\n/Users/alice/repo\n",
            encoding="utf-8",
        )
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_public_host_path_in_json_is_reported(self) -> None:
        config = self.air_root / "Modules" / "XUUnity" / "fixture-config.json"
        config.write_text(
            json.dumps({"root": "/home/alice/project"}),
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
            target.read_text(encoding="utf-8") + "\n/Users/alice/repo\n",
            encoding="utf-8",
        )
        self._init_host_repo()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_ignored_untracked_file_is_local_scratch_not_public_leak(self) -> None:
        self._init_host_repo()
        (self.host / ".gitignore").write_text("*-setup-plan.json\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        scratch = self.air_root / "Modules" / "XUUnity" / "local-setup-plan.json"
        scratch.write_text(json.dumps({"root": "/Users/alice/project"}), encoding="utf-8")
        kinds = self._kinds(self._audit())
        self.assertIn("local_scratch_path_leak", kinds)
        self.assertNotIn("public_path_leak", kinds)

    def test_untracked_but_unignored_file_stays_a_public_leak(self) -> None:
        self._init_host_repo()
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")
        pending = self.air_root / "Modules" / "XUUnity" / "pending.json"
        pending.write_text(json.dumps({"root": "/Users/alice/project"}), encoding="utf-8")
        self.assertIn("public_path_leak", self._kinds(self._audit()))

    def test_design_registry_drift_is_reported(self) -> None:
        registry = self.air_root / "Design" / "README.md"
        registry.write_text("# Fixture Design Registry\n", encoding="utf-8")
        self.assertIn("design_file_unregistered", self._kinds(self._audit()))

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
