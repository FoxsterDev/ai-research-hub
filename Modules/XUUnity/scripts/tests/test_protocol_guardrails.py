from __future__ import annotations

import re
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[2]
AIRROOT_DIR = MODULE_DIR.parents[1]


def read_module(relative: str) -> str:
    return (MODULE_DIR / relative).read_text(encoding="utf-8")


class ProtocolGuardrailTests(unittest.TestCase):
    def test_concurrency_owner_defines_all_four_evidence_classes(self) -> None:
        text = read_module("skills/async/concurrency_classification.md")
        for classification in (
            "main_thread_confined",
            "temporal_reentrancy",
            "cross_thread_shared",
            "unknown",
        ):
            with self.subTest(classification=classification):
                self.assertIn(f"`{classification}`", text)
        self.assertIn(
            "They are not by themselves evidence of `cross_thread_shared`",
            text,
        )

    def test_generic_review_routes_evidence_and_complexity_owners(self) -> None:
        text = read_module("tasks/code_review.md")
        for owner in (
            "skills/async/concurrency_classification.md",
            "knowledge/change_complexity_budget.md",
            "knowledge/review_evidence_provenance.md",
        ):
            with self.subTest(owner=owner):
                self.assertIn(owner, text)
        self.assertIn("Do not call a temporal ordering collision a thread race", text)

    def test_default_score_weights_stay_at_one_hundred(self) -> None:
        text = read_module("knowledge/review_quality_scoring.md")
        dimensions = text.split("Default dimensions:", 1)[1].split(
            "### Dimension Guidance", 1
        )[0]
        parsed = re.findall(r"^- `([0-9]+)` (.+)$", dimensions, re.MULTILINE)
        weights = {name: int(weight) for weight, name in parsed}
        self.assertEqual(100, sum(weights.values()))
        self.assertEqual(15, weights["Security, privacy, and abuse resistance"])
        self.assertEqual(
            10,
            weights[
                "Simplicity, project fit, maintainability, and change safety"
            ],
        )
        self.assertNotIn("Project fit and simplicity", weights)

    def test_branch_memory_cannot_validate_its_own_change(self) -> None:
        decision_rules = read_module("knowledge/decision_rules.md")
        provenance = read_module("knowledge/review_evidence_provenance.md")
        git_review = read_module("reviews/git_change_review.md")
        artifact_contract = read_module("reviews/review_artifact_contract.md")
        template = (AIRROOT_DIR / "Templates/XUUNITY_GIT_CHANGE_REVIEW_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("memory added or changed by the target branch", decision_rules)
        self.assertIn("candidate design record", provenance)
        self.assertIn("review_evidence_provenance.md", git_review)
        self.assertIn("normal extraction and approval boundary", artifact_contract)
        for field in (
            "Comparison-base project memory",
            "Branch-derived candidate evidence",
            "Independent approval",
            "Unresolved evidence conflicts",
        ):
            with self.subTest(field=field):
                self.assertIn(field, template)
                self.assertIn(field, git_review)

    def test_reduced_stack_owner_precedence_is_not_review_approval(self) -> None:
        contract = read_module("knowledge/reduced_stack_gate_contract.md")
        rules = read_module("knowledge/reduced_stack_rules.json")
        schema = read_module("schemas/xuunity.stack-plan.schema.json")
        self.assertIn("not evidence provenance or independent approval", contract)
        self.assertIn('"id": "change_review_provenance"', rules)
        self.assertIn("This is not evidence provenance or approval", schema)

    def test_entrypoint_allows_not_applicable_concurrency(self) -> None:
        text = read_module("tasks/start_session.md")
        self.assertNotIn("async, callback, thread, or Unity-API path", text)
        self.assertIn(
            "for a path with an async, callback, or thread boundary",
            text,
        )
        self.assertIn(
            "Concurrency and thread-safety classification when applicable, "
            "otherwise `not_applicable`",
            text,
        )

    def test_validation_evidence_identity_covers_dirty_and_non_code_changes(self) -> None:
        text = read_module("knowledge/unity_validation_boundaries.md")
        for requirement in (
            "whether the source tree was clean or dirty",
            "stable diff or content digest",
            "supporting metadata, never proof of content identity",
            "other non-code assets",
            "A script recompile alone does not prove",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)

    def test_runtime_evidence_loop_keeps_playmode_and_injection_conditional(self) -> None:
        playmode = read_module("skills/tests/playmode_tests.md")
        doctrine = read_module("skills/tests/testing_doctrine.md")
        for requirement in (
            "depends on live scene wiring",
            "not mandatory for copy-only or static visual claims",
            "When controlled external input or a payload is required",
            "otherwise drive the real user or input path",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, playmode)
        self.assertIn(
            "do not owe a PlayMode red solely because the result is user-visible",
            doctrine,
        )

    def test_ui_smoke_authorization_has_one_scoped_owner(self) -> None:
        playmode = read_module("skills/tests/playmode_tests.md")
        ui_policy = read_module("reviews/policy_packs/ui_heavy_changes.md")
        for text in (playmode, ui_policy):
            with self.subTest(path="playmode" if text is playmode else "ui_policy"):
                self.assertIn("explicit user request to execute validation", text)
                self.assertIn("materially expands", text)
        self.assertIn("Non-UI PlayMode work does not inherit", playmode)
        self.assertIn("does not extend to non-UI PlayMode work", ui_policy)


if __name__ == "__main__":
    unittest.main()
