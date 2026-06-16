from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[1] / "module_registry_tool.py"
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "paid_module_skill"


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
                "capabilities": [
                    "xuunity.game_qa.runtime_ui_validation",
                    "xuunity.game_qa.playmode_smoke_planning",
                ],
                "entrypoints": {
                    "roles": ["role/game_qa_brain.md"],
                    "skills": ["skills/game_qa/routing.md", "skills/game_qa/mcp_playmode_smoke.md"],
                    "reviews": ["reviews/ui_runtime_validation_closeout_gate.md"],
                    "utilities": ["utilities/game_qa_paid_skill_usage.md"],
                    "knowledge": [],
                },
                "routing": {
                    "triggers": ["game qa", "playmode smoke", "validate ui after a fix"],
                    "capabilities": ["xuunity.game_qa.runtime_ui_validation"],
                },
                "mcp": {
                    "providedCapabilities": ["xuunity.game_qa.playmode_smoke_planning"],
                },
                "exportPolicy": {
                    "mayQuotePrivateContentInReports": False,
                    "reportReferenceMode": "pack_id_only",
                },
            },
        )

    def _module_manifest_path(self) -> Path:
        return self.private_root / "module.json"

    def _pack_manifest_path(self) -> Path:
        return self.private_root / "packs" / "game_qa_paid_skill" / "pack.json"

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

    def _write_entitlements(
        self,
        features: list[str],
        *,
        mode: str = "personal_dev",
        trust_level: str = "local_flag",
        verified: bool = False,
        source: str = "local_file",
    ) -> Path:
        path = self.home / "entitlements.json"
        self._write_json(
            path,
            {
                "schemaVersion": "xuunity.entitlements.v1",
                "subject": "local-dev-seat",
                "mode": mode,
                "source": source,
                "provider": {
                    "type": "local_file",
                    "mode": mode,
                    "trustLevel": trust_level,
                    "verified": verified,
                    "checkedAtUtc": "2026-06-15T00:00:00Z",
                },
                "features": features,
            },
        )
        return path

    def _write_installer_manifest(self, payload: dict | None = None) -> Path:
        manifest = payload or {
            "schemaVersion": "xuunity.installer.v1",
            "moduleId": "xcntp",
            "displayName": "XCNT-P",
            "recommendedMount": "AIModules/XCNT-P",
            "requiredFeatures": ["xcntp", "xcntp.game_qa_paid_skill"],
            "postInstallChecks": ["xuunity_module_status", "xuunity_module_rollsync"],
        }
        path = self.root / "installer.json"
        self._write_json(path, manifest)
        return path

    def _assert_redacted_api_has_no_private_paths(self, text: str) -> None:
        private_fragments = [
            str(self.root),
            str(self.private_root),
            str(self.home),
            "AIModules",
            "packs/game_qa_paid_skill",
            "role/game_qa_brain.md",
            "skills/game_qa",
            "entrypoints",
            "resolved_root",
            "entitlements.json",
        ]
        for fragment in private_fragments:
            self.assertNotIn(fragment, text)

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
        self.assertEqual(payload["outputBoundary"], "private_runtime")
        self.assertEqual(payload["entitlementTrustLevel"], "local_flag")
        self.assertFalse(payload["entitlementVerified"])
        self.assertEqual(payload["loaded_pack_count"], 1)
        self.assertEqual(payload["loadedPacks"][0]["id"], "xcntp.game_qa_paid_skill")
        self.assertIn("AIModules/XCNT-P", payload["loadedPacks"][0]["root"])
        self.assertTrue(Path(payload["cache_path"]).is_file())
        registry = json.loads(Path(payload["cache_path"]).read_text(encoding="utf-8"))
        self.assertEqual(registry["outputBoundary"], "private_runtime")
        self.assertEqual(registry["entitlements"]["provider"]["mode"], "personal_dev")
        self.assertEqual(registry["entitlements"]["provider"]["trustLevel"], "local_flag")
        self.assertFalse(registry["entitlements"]["provider"]["verified"])
        self.assertEqual(registry["loadedPacks"][0]["entitlementTrustLevel"], "local_flag")

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

    def test_route_smoke_can_prove_pack_by_required_capability(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run(
            "route-smoke",
            "--task-text",
            "use the paid validation capability",
            "--require-capability",
            "xuunity.game_qa.runtime_ui_validation",
            "--expect-pack",
            "xcntp.game_qa_paid_skill",
        )
        payload = json.loads(result.stdout)
        match = payload["matchedLoadedPacks"][0]

        self.assertEqual(payload["status"], "passed")
        self.assertTrue(payload["requiredCapabilitiesFound"])
        self.assertEqual(match["id"], "xcntp.game_qa_paid_skill")
        self.assertIn("xuunity.game_qa.runtime_ui_validation", match["matchedCapabilities"])
        self.assertIn("xuunity.game_qa.playmode_smoke_planning", match["capabilities"])

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

    def test_session_plan_can_load_by_capability_without_hardcoded_trigger(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run(
            "session-plan",
            "--task-text",
            "perform premium runtime validation",
            "--require-capability",
            "xuunity.game_qa.runtime_ui_validation",
        )
        payload = json.loads(result.stdout)
        contract = payload["sessionContract"]

        self.assertEqual(payload["status"], "private_pack_loaded")
        self.assertEqual(contract["matched_private_packs"], ["xcntp.game_qa_paid_skill"])
        self.assertEqual(contract["matched_private_pack_capabilities"], ["xuunity.game_qa.runtime_ui_validation"])
        self.assertEqual(payload["matchedLoadedPacks"][0]["matchedTriggers"], [])

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

    def test_scan_reports_missing_module_json_without_crawling(self) -> None:
        loose_root = self.aimodules / "LoosePrivateModule"
        loose_root.mkdir()

        result = self._run("scan")
        payload = json.loads(result.stdout)
        loose_modules = [module for module in payload["scannedModules"] if module["root"].endswith("LoosePrivateModule")]

        self.assertEqual(len(loose_modules), 1)
        self.assertEqual(loose_modules[0]["resolution"], "unregistered_module_root")
        self.assertEqual(loose_modules[0]["pack_count"], 0)

    def test_invalid_module_schema_version_fails_validation(self) -> None:
        manifest = json.loads(self._module_manifest_path().read_text(encoding="utf-8"))
        manifest["schemaVersion"] = "xuunity.module.v999"
        self._write_json(self._module_manifest_path(), manifest)

        result = self._run("validate", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["invalidModules"][0]["id"], "xcntp")
        self.assertIn("unsupported module schemaVersion", payload["invalidModules"][0]["validation_errors"][0])

    def test_pack_path_escaping_root_fails_without_loading_pack(self) -> None:
        manifest = json.loads(self._module_manifest_path().read_text(encoding="utf-8"))
        manifest["packs"] = ["../evil/pack.json"]
        self._write_json(self._module_manifest_path(), manifest)
        self._write_json(
            self.private_root.parent / "evil" / "pack.json",
            {
                "schemaVersion": "xuunity.pack.v1",
                "id": "xcntp.evil",
                "displayName": "Evil",
                "licenseFeature": "xcntp.evil",
                "dependsOn": [],
                "entrypoints": {},
                "exportPolicy": {
                    "mayQuotePrivateContentInReports": False,
                    "reportReferenceMode": "pack_id_only",
                },
            },
        )

        result = self._run("validate", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["invalidModules"][0]["pack_count"], 0)
        self.assertEqual(payload["invalidPacks"], [])
        self.assertIn("module pack path must stay inside module root", payload["invalidModules"][0]["validation_errors"][0])

    def test_invalid_report_reference_mode_fails_pack_validation(self) -> None:
        manifest = json.loads(self._pack_manifest_path().read_text(encoding="utf-8"))
        manifest["exportPolicy"]["reportReferenceMode"] = "entrypoints"
        self._write_json(self._pack_manifest_path(), manifest)

        result = self._run("validate", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["invalidPacks"][0]["id"], "xcntp.game_qa_paid_skill")
        self.assertIn("reportReferenceMode", payload["invalidPacks"][0]["validation_errors"][0])

    def test_invalid_capability_tag_fails_pack_validation(self) -> None:
        manifest = json.loads(self._pack_manifest_path().read_text(encoding="utf-8"))
        manifest["capabilities"] = ["XUUnity.Bad Capability"]
        self._write_json(self._pack_manifest_path(), manifest)

        result = self._run("validate", check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["invalidPacks"][0]["id"], "xcntp.game_qa_paid_skill")
        self.assertIn("pack capabilities", "\n".join(payload["invalidPacks"][0]["validation_errors"]))

    def test_xuunity_module_status_redacts_private_paths_and_entrypoints(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run("xuunity_module_status")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["action"], "xuunity_module_status")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["outputBoundary"], "redacted_api")
        self.assertEqual(payload["counts"]["loadedPacks"], 1)
        self.assertEqual(payload["entitlements"]["trustLevel"], "local_flag")
        self.assertEqual(payload["entitlements"]["provider"]["trustLevel"], "local_flag")
        self.assertFalse(payload["entitlements"]["provider"]["verified"])
        self.assertEqual(payload["loadedPacks"][0]["entitlementTrustLevel"], "local_flag")
        self.assertIn("xuunity.game_qa.runtime_ui_validation", payload["loadedPacks"][0]["capabilities"])
        self.assertEqual(payload["loadedPacks"][0]["reportReference"], "Private pack used: xcntp.game_qa_paid_skill")
        self._assert_redacted_api_has_no_private_paths(result.stdout)

    def test_xuunity_module_rollsync_redacts_private_paths_and_entrypoints(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])

        result = self._run("xuunity_module_rollsync")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["action"], "xuunity_module_rollsync")
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["outputBoundary"], "redacted_api")
        self.assertEqual(payload["cache"], "user_cache")
        self.assertEqual(payload["entitlements"]["trustLevel"], "local_flag")
        self.assertEqual(payload["loadedPacks"][0]["entitlementTrustLevel"], "local_flag")
        self._assert_redacted_api_has_no_private_paths(result.stdout)

    def test_redacted_api_reports_commercial_provider_facts_without_gating_load(self) -> None:
        self._write_entitlements(
            ["xcntp", "xcntp.game_qa_paid_skill"],
            mode="signed_offline",
            trust_level="signed_offline",
            verified=False,
            source="signed_license",
        )

        result = self._run("xuunity_module_status")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["entitlements"]["trustLevel"], "signed_offline")
        self.assertFalse(payload["entitlements"]["verified"])
        self.assertEqual(payload["loadedPacks"][0]["entitlementTrustLevel"], "signed_offline")
        self._assert_redacted_api_has_no_private_paths(result.stdout)

    def test_redacted_api_redacts_path_like_entitlement_source(self) -> None:
        self._write_entitlements(
            ["xcntp", "xcntp.game_qa_paid_skill"],
            source=str(self.private_root / "customer-license.json"),
        )

        result = self._run("xuunity_module_status")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["entitlements"]["source"], "redacted_path")
        self._assert_redacted_api_has_no_private_paths(result.stdout)

    def test_redacted_rollsync_rejects_unsafe_output_without_path_leak(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])
        output = self.root / "outside-cache" / "resolved_modules.json"

        result = self._run("xuunity_module_rollsync", "--output", str(output), check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["outputBoundary"], "redacted_api")
        self.assertEqual(payload["cache"], "none")
        self.assertFalse(output.exists())
        self._assert_redacted_api_has_no_private_paths(result.stdout)

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

    def test_resolved_registry_output_outside_user_cache_is_rejected(self) -> None:
        self._write_entitlements(["xcntp", "xcntp.game_qa_paid_skill"])
        output = self.root / "outside-cache" / "resolved_modules.json"

        result = self._run("rollsync", "--output", str(output), check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 3)
        self.assertEqual(payload["status"], "invalid")
        self.assertFalse(output.exists())
        self.assertIn("user cache", " ".join(payload["next_actions"]))

    def test_validate_installer_accepts_public_safe_manifest_without_private_bodies(self) -> None:
        installer = self._write_installer_manifest()

        result = self._run("validate-installer", "--installer", str(installer))
        payload = json.loads(result.stdout)

        self.assertEqual(payload["action"], "xuunity.installer.validate")
        self.assertEqual(payload["status"], "valid")
        self.assertEqual(payload["outputBoundary"], "redacted_api")
        self.assertEqual(payload["moduleId"], "xcntp")
        self.assertEqual(payload["recommendedMount"], "AIModules/XCNT-P")
        self.assertEqual(payload["requiredFeatures"], ["xcntp", "xcntp.game_qa_paid_skill"])
        self.assertFalse(payload["privateBodiesRead"])
        self.assertNotIn(str(self.private_root), result.stdout)

    def test_validate_installer_rejects_unsafe_mount_without_path_leak(self) -> None:
        installer = self._write_installer_manifest(
            {
                "schemaVersion": "xuunity.installer.v1",
                "moduleId": "xcntp",
                "recommendedMount": str(self.private_root),
                "requiredFeatures": ["xcntp", "xcntp.game_qa_paid_skill"],
                "postInstallChecks": ["xuunity_module_status"],
            }
        )

        result = self._run("validate-installer", "--installer", str(installer), check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["recommendedMount"], "redacted_path")
        self.assertIn("recommendedMount", "\n".join(payload["errors"]))
        self.assertFalse(payload["privateBodiesRead"])
        self.assertNotIn(str(self.private_root), result.stdout)

    def test_validate_installer_unreadable_error_is_redacted(self) -> None:
        missing = self.root / "Private" / "missing-installer.json"

        result = self._run("validate-installer", "--installer", str(missing), check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["status"], "invalid")
        self.assertEqual(payload["outputBoundary"], "redacted_api")
        self.assertFalse(payload["privateBodiesRead"])
        self.assertNotIn(str(self.root), result.stdout)
        self.assertNotIn("missing-installer.json", result.stdout)

    def test_paid_module_skill_templates_generate_valid_pack(self) -> None:
        self._unlink_private_module()
        template_root = self.root / "TemplatePrivate" / "XCNT-P"
        pack_root = template_root / "packs" / "demo_paid_skill"
        replacements = {
            "{{MODULE_ID}}": "xcntp",
            "{{MODULE_DISPLAY_NAME}}": "XCNT-P",
            "{{MODULE_MOUNT_NAME}}": "XCNT-P",
            "{{MODULE_VERSION}}": "0.1.0",
            "{{PACK_ID}}": "xcntp.demo_paid_skill",
            "{{PACK_DISPLAY_NAME}}": "Demo Paid Skill",
            "{{PACK_SLUG}}": "demo_paid_skill",
            "{{LICENSE_FEATURE}}": "xcntp.demo_paid_skill",
            "{{CAPABILITY_ID}}": "xuunity.demo.paid_skill",
            "{{TRIGGER_TEXT}}": "demo paid validation",
            "{{ROLE_FILE}}": "demo_paid_brain.md",
            "{{SKILL_FOLDER}}": "demo_paid_skill",
            "{{PRIMARY_SKILL_FILE}}": "main_skill.md",
            "{{REVIEW_FILE}}": "demo_review_gate.md",
            "{{UTILITY_FILE}}": "demo_usage.md",
        }
        template_outputs = {
            "module.json.template": template_root / "module.json",
            "installer.json.template": template_root / "installer.json",
            "pack.json.template": pack_root / "pack.json",
            "pack_README.md.template": pack_root / "README.md",
            "routing.md.template": pack_root / "skills" / "demo_paid_skill" / "routing.md",
            "primary_skill.md.template": pack_root / "skills" / "demo_paid_skill" / "main_skill.md",
            "role.md.template": pack_root / "role" / "demo_paid_brain.md",
            "usage.md.template": pack_root / "utilities" / "demo_usage.md",
            "review_gate.md.template": pack_root / "reviews" / "demo_review_gate.md",
            "verify_commands.md.template": pack_root / "docs" / "verify_commands.md",
            "entitlements.personal_dev.json.template": self.home / "entitlements.json",
        }
        for template_name, output_path in template_outputs.items():
            text = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
            for token, value in replacements.items():
                text = text.replace(token, value)
            self.assertNotIn("{{", text, template_name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text, encoding="utf-8")
        for json_path in [
            template_root / "module.json",
            template_root / "installer.json",
            pack_root / "pack.json",
            self.home / "entitlements.json",
        ]:
            json.loads(json_path.read_text(encoding="utf-8"))
        (self.aimodules / "XCNT-P").symlink_to(template_root, target_is_directory=True)

        validate = self._run("validate")
        rollsync = self._run("rollsync")
        status = self._run("xuunity_module_status")
        installer = self._run("validate-installer", "--installer", str(template_root / "installer.json"))
        session = self._run(
            "session-plan",
            "--task-text",
            "demo paid validation",
            "--require-capability",
            "xuunity.demo.paid_skill",
        )
        route = self._run(
            "route-smoke",
            "--task-text",
            "demo paid validation",
            "--require-capability",
            "xuunity.demo.paid_skill",
            "--expect-pack",
            "xcntp.demo_paid_skill",
        )

        self.assertEqual(json.loads(validate.stdout)["status"], "valid")
        self.assertEqual(json.loads(rollsync.stdout)["status"], "ready")
        self.assertEqual(json.loads(status.stdout)["status"], "ready")
        self.assertEqual(json.loads(installer.stdout)["status"], "valid")
        self.assertEqual(json.loads(session.stdout)["status"], "private_pack_loaded")
        self.assertEqual(json.loads(route.stdout)["status"], "passed")
        self._assert_redacted_api_has_no_private_paths(status.stdout)


if __name__ == "__main__":
    unittest.main()
