from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reduced_stack_resolver as resolver  # noqa: E402
import reduced_stack_testkit as kit  # noqa: E402
import ruleset_check  # noqa: E402

SHIPPED_PROBES = MODULE_DIR / "knowledge" / "reduced_stack_probes.json"

MINIMALITY_PROBE = {
    "id": "docs_minimal",
    "task_text": "Correct a typo in the contribution guide wording.",
    "task_kind": "documentation_update",
    "risk_class": "baseline",
    "planned_mutation_paths": ["docs/contributing_notes.md"],
    "expect_matched_rule_ids": [
        "base_role",
        "entrypoint_kernel",
        "repo_router",
    ],
}
OVERRIDE_PROBE = {
    "id": "async_override_owner",
    "task_text": "Move the upload continuation off the main thread with "
    "async scheduling.",
    "task_kind": "documentation_update",
    "risk_class": "normal",
    "resolved_project": kit.PROJECT,
    "planned_mutation_paths": [f"{kit.PROJECT}/Scripts/Foo.cs"],
    "expect_rule_ids_include": ["async_threading"],
    "expect_artifact_owner": {
        f"{kit.PROJECT}/Assets/AIOutput/ProjectMemory/SkillOverrides/"
        f"async.md": "project"
    },
}


def probes_document(*probes: dict) -> dict:
    return {
        "schema_version": ruleset_check.PROBES_SCHEMA_VERSION,
        "authored_by": "human",
        "probes": list(probes),
    }


class RulesetCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.repo = kit.build_fixture_repo(Path(self._scratch.name))
        self.ruleset = kit.ruleset_path(self.repo)

    def _write_probes(self, document: dict) -> Path:
        path = self.repo / "probes.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_document_and_authored_probes_pass(self) -> None:
        self.assertEqual(
            [], ruleset_check.check_document(self.repo, self.ruleset)
        )
        probes = self._write_probes(
            probes_document(MINIMALITY_PROBE, OVERRIDE_PROBE)
        )
        self.assertEqual(
            [], ruleset_check.run_probes(self.repo, self.ruleset, probes)
        )

    def test_shipped_probe_corpus_passes_on_fixture_repo(self) -> None:
        self.assertEqual(
            [],
            ruleset_check.run_probes(self.repo, self.ruleset, SHIPPED_PROBES),
        )

    def test_hash_mismatch_detected_then_fixed(self) -> None:
        document = json.loads(self.ruleset.read_text(encoding="utf-8"))
        document["ruleset_version"] = "999.0.0"
        self.ruleset.write_text(json.dumps(document), encoding="utf-8")
        findings = ruleset_check.check_document(self.repo, self.ruleset)
        self.assertTrue(
            any("ruleset_hash mismatch" in finding for finding in findings)
        )
        self.assertEqual(
            [],
            ruleset_check.check_document(
                self.repo, self.ruleset, fix_hash=True
            ),
        )

    def test_overrouting_rule_trips_minimality_probe(self) -> None:
        document = json.loads(self.ruleset.read_text(encoding="utf-8"))
        document["rules"].append(
            {
                "id": "overeager_family",
                "description": "Deliberately over-routed family.",
                "priority": 99,
                "selectors": {"always": True},
                "requirements": [
                    {
                        "id": "guidance",
                        "mode": "all_of",
                        "paths": ["{module}/skills/async/routing.md"],
                        "weight": 1,
                        "phase": "before_first_mutation",
                    }
                ],
                "risk": "baseline",
                "human_owner": "{module}/skills/async/routing.md",
            }
        )
        document["ruleset_hash"] = resolver.compute_ruleset_hash(document)
        self.ruleset.write_text(json.dumps(document), encoding="utf-8")
        probes = self._write_probes(probes_document(MINIMALITY_PROBE))
        findings = ruleset_check.run_probes(self.repo, self.ruleset, probes)
        self.assertTrue(
            any("overeager_family" in finding for finding in findings)
        )

    def test_owner_probe_detects_lost_override(self) -> None:
        override = (
            self.repo
            / kit.PROJECT
            / "Assets/AIOutput/ProjectMemory/SkillOverrides/async.md"
        )
        override.unlink()
        probes = self._write_probes(probes_document(OVERRIDE_PROBE))
        findings = ruleset_check.run_probes(self.repo, self.ruleset, probes)
        self.assertTrue(
            any("effective owner" in finding for finding in findings)
        )

    def test_probes_require_human_authorship(self) -> None:
        document = probes_document(MINIMALITY_PROBE)
        document["authored_by"] = "resolver"
        probes = self._write_probes(document)
        findings = ruleset_check.run_probes(self.repo, self.ruleset, probes)
        self.assertTrue(
            any("authored_by" in finding for finding in findings)
        )

    def test_main_exit_codes(self) -> None:
        probes = self._write_probes(probes_document(MINIMALITY_PROBE))
        arguments = [
            "--repo-root",
            str(self.repo),
            "--ruleset",
            str(self.ruleset),
            "--probes",
            str(probes),
        ]
        self.assertEqual(0, ruleset_check.main(arguments))
        document = json.loads(self.ruleset.read_text(encoding="utf-8"))
        document["ruleset_version"] = "999.0.0"
        self.ruleset.write_text(json.dumps(document), encoding="utf-8")
        self.assertEqual(1, ruleset_check.main(arguments))


if __name__ == "__main__":
    unittest.main()
