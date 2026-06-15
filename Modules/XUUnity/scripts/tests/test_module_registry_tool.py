from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "module_registry_tool.py"


class ModuleRegistryToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.host = self.root / "Host"
        self.air_root = self.host / "AIRoot"
        self.aimodules = self.host / "AIModules"
        self.private_root = self.root / "Private" / "XCNT-P"
        self.home = self.root / "Home"
        self.air_root.mkdir(parents=True)
        self.aimodules.mkdir(parents=True)
        self.home.mkdir(parents=True)
        self._write_private_module()
        self._link_private_module()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _write_private_module(self, *, protocol_scopes: list[str] | None = None) -> None:
        pack_root = self.private_root / "packs" / "game_qa_paid_skill"
        for rel in [
            "role/game_qa_brain.md",
            "skills/game_qa/routing.md",
            "skills/game_qa/mcp_playmode_smoke.md",
            "reviews/ui_runtime_validation_closeout_gate.md",
            "utilities/game_qa_paid_skill_usage.md",
        ]:
            path = pack_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {rel}\n", encoding="utf-8")
        self._write_json(
            self.private_root / "module.json",
            {
                "schemaVersion": "xuunity.module.v1",
                "id": "xcntp",
                "displayName": "XCNT-P",
                "kind": "personal_private_overlay",
                "visibility": "personal_private",
                "version": "0.1.0",
                "protocolScopes": protocol_scopes or ["xuunity"],
                "license": {"feature": "xcntp", "defaultState": "locked"},
                "packs": ["packs/game_qa_paid_skill/pack.json"],
                "exportPolicy": {
                    "mayCommitToHostRepo": False,
                    "mayWriteResolvedRegistryToProject": False,
                    "mayQuotePrivateContentInReports": False,
                },
            },
        )
        self._write_json(
            pack_root / "pack.json",
            {
                "schemaVersion": "xuunity.pack.v1",
                "id": "xcntp.game_qa_paid_skill",
                "displayName": "Game QA Paid Skill",
                "licenseFeature": "xcntp.game_qa_paid_skill",
                "dependsOn": ["xuunity.core"],
                "entrypoints": {
                    "roles": ["role/game_qa_brain.md"],
                    "skills": ["skills/game_qa/routing.md", "skills/game_qa/mcp_playmode_smoke.md"],
                    "reviews": ["reviews/ui_runtime_validation_closeout_gate.md"],
                    "utilities": ["utilities/game_qa_paid_skill_usage.md"],
                    "knowledge": [],
                },
                "routing": {"triggers": ["game qa", "playmode smoke", "validate ui after a fix"]},
                "exportPolicy": {
                    "mayQuotePrivateContentInReports": False,
                    "reportReferenceMode": "pack_id_only",
                },
            },
        )

    def _link_private_module(self) -> None:
        link = self.aimodules / "XCNT-P"
        try:
            link.symlink_to(self.private_root, target_is_directory=True)
        except OSError as exc:  # pragma: no cover - platform capability guard
            self.skipTest(f"symlinks unavailable: {exc}")

    def _unlink_private_module(self) -> None:
        link = self.aimodules / "XCNT-P"
        if link.exists() or link.is_symlink():
            link.unlink()

    def _write_entitlements(self, features: list[str]) -> Path:
        path = self.home / "entitlements.json"
        self._write_json(
            path,
            {
                "schemaVersion": "xuunity.entitlements.v1",
                "mode": "local_personal",
                "features": features,
            },
        )
        return path

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "XUUNITY_HOME": str(self.home)}
        result = subprocess.run(
            [sys.executable, str(TOOL), *args, "--project-root", str(self.host), "--xuunity-home", str(self.home)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_rollsync_loads_entitled_pack_from_aimodules_symlink(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run("rollsync")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["loaded_pack_count"], 1)
        self.assertEqual(payload["loadedPacks"][0]["id"], "xcntp.game_qa_paid_skill")
        self.assertIn("AIModules/XCNT-P", payload["loadedPacks"][0]["root"])

    def test_route_smoke_matches_game_qa_without_public_path_leak(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run(
            "route-smoke",
            "--task-text",
            "validate ui after a fix with PlayMode smoke",
            "--expect-pack",
            "xcntp.game_qa_paid_skill",
        )
        payload = json.loads(result.stdout)
        match = payload["matchedLoadedPacks"][0]

        self.assertEqual(payload["status"], "passed")
        self.assertEqual(match["id"], "xcntp.game_qa_paid_skill")
        self.assertFalse(match["publicPathLeakDetected"])
        self.assertIn("AIModules/XCNT-P", match["root"])
        all_paths = "\n".join(path for group in match["entrypoints"].values() for path in group)
        self.assertNotIn("Modules/XUUnity/skills/game_qa", all_paths)

    def test_session_plan_loads_enabled_pack_with_redacted_report_reference(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run(
            "session-plan",
            "--task-text",
            "validate ui after a fix with PlayMode smoke",
        )
        payload = json.loads(result.stdout)
        contract = payload["sessionContract"]

        self.assertEqual(payload["status"], "private_pack_loaded")
        self.assertEqual(contract["matched_private_packs"], ["xcntp.game_qa_paid_skill"])
        self.assertEqual(contract["private_pack_report_references"], ["Private pack used: xcntp.game_qa_paid_skill"])
        self.assertFalse(contract["continue_without_private_pack"])
        self.assertFalse(payload["publicPathLeakDetected"])
        self.assertIn("entrypoints", payload["matchedLoadedPacks"][0])
        report_reference = contract["private_pack_report_references"][0]
        self.assertNotIn("/", report_reference)
        self.assertNotIn("role/", report_reference)
        self.assertNotIn("skills/game_qa", report_reference)

    def test_session_plan_locked_pack_continues_with_public_core(self) -> None:
        self._write_entitlements(["xcntp"])

        result = self._run(
            "session-plan",
            "--task-text",
            "validate ui after a fix with PlayMode smoke",
        )
        payload = json.loads(result.stdout)
        contract = payload["sessionContract"]

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "private_pack_unavailable")
        self.assertEqual(contract["matched_private_packs"], [])
        self.assertTrue(contract["continue_without_private_pack"])
        self.assertEqual(payload["fallback"], "continue_with_public_core")
        self.assertEqual(payload["matchedLockedPacks"][0]["id"], "xcntp.game_qa_paid_skill")

    def test_session_plan_absent_private_module_continues_with_public_core(self) -> None:
        self._unlink_private_module()
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run(
            "session-plan",
            "--task-text",
            "validate ui after a fix with PlayMode smoke",
        )
        payload = json.loads(result.stdout)
        contract = payload["sessionContract"]

        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["status"], "public_core_only")
        self.assertEqual(payload["matchedLoadedPacks"], [])
        self.assertEqual(contract["matched_private_packs"], [])
        self.assertTrue(contract["continue_without_private_pack"])

    def test_missing_entitlement_locks_pack(self) -> None:
        self._write_entitlements(["xcntp"])

        result = self._run("rollsync", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(payload["status"], "locked")
        self.assertEqual(payload["lockedPacks"][0]["id"], "xcntp.game_qa_paid_skill")

    def test_out_of_scope_module_is_ignored(self) -> None:
        self._write_private_module(protocol_scopes=["other_protocol"])
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run("rollsync")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["status"], "not_configured")
        self.assertEqual(payload["loaded_pack_count"], 0)
        self.assertEqual(payload["scanned_module_count"], 1)

    def test_project_output_path_is_rejected(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])
        output = self.host / "resolved_modules.json"

        result = self._run("rollsync", "--output", str(output), check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(payload["status"], "invalid")
        self.assertFalse(output.exists())
        self.assertIn("user cache", " ".join(payload["next_actions"]))


if __name__ == "__main__":
    unittest.main()
