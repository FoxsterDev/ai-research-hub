from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
CHECKER = SCRIPTS_DIR / "review_route_contract.py"
sys.path.insert(0, str(SCRIPTS_DIR))
import review_route_contract  # noqa: E402


GOOD_SKILL = """# Review skill

Read these files fully, first line through EOF, in this order:

1. `Modules/Protocol/tasks/code_review.md`
2. `Modules/Protocol/role/output_format.md`

Route to the narrowest review:

- explicit diff, branch, commit, PR, staged, or unstaged change -> `git_change_review.md`
- tests as the primary target -> `test_quality_review.md`
- SDK wrapper or integration -> `sdk_code_review.md`
- runtime or product feature implementation -> `feature_code_review.md`
- subsystem ownership or boundary design -> `architecture_review.md`
- rollout or release confidence -> `release_readiness_review.md`
- delivery or blast-radius assessment -> `delivery_risk_review.md`
- JNI, Swift, Java, Kotlin, manifest, plist, or native bridge -> `native_plugin_review.md`

Load `full_review.md` only for an explicit full review request.
"""

GOOD_START_SESSION = """# Start session

- `xuunity review ...` -> `tasks/code_review.md`
- `xuunity full review ...` -> `reviews/full_review.md`
- `xuunity review all ...` -> `reviews/full_review.md`
"""


def rules(skill: str = GOOD_SKILL, start_session: str = GOOD_START_SESSION) -> set[str]:
    return {
        violation.rule
        for violation in review_route_contract.check_contract(skill, start_session)
    }


class ReviewRouteContractTests(unittest.TestCase):
    def test_valid_synthetic_contract_passes(self) -> None:
        self.assertEqual(set(), rules())

    def test_full_review_reference_outside_bootstrap_is_allowed(self) -> None:
        self.assertNotIn("bootstrap_includes_full_review", rules())

    def test_bootstrap_requires_code_review_owner(self) -> None:
        skill = GOOD_SKILL.replace(
            "Modules/Protocol/tasks/code_review.md",
            "Modules/Protocol/tasks/architecture_plan.md",
        )
        self.assertIn("bootstrap_code_review_missing", rules(skill))

    def test_bootstrap_rejects_same_basename_under_wrong_owner(self) -> None:
        skill = GOOD_SKILL.replace(
            "Modules/Protocol/tasks/code_review.md",
            "Modules/Protocol/reviews/code_review.md",
        )
        self.assertIn("bootstrap_code_review_missing", rules(skill))

    def test_code_review_owner_must_be_first(self) -> None:
        skill = GOOD_SKILL.replace(
            "1. `Modules/Protocol/tasks/code_review.md`\n"
            "2. `Modules/Protocol/role/output_format.md`",
            "1. `Modules/Protocol/role/output_format.md`\n"
            "2. `Modules/Protocol/tasks/code_review.md`",
        )
        self.assertIn("bootstrap_code_review_not_first", rules(skill))

    def test_full_review_is_rejected_from_mandatory_bootstrap(self) -> None:
        skill = GOOD_SKILL.replace(
            "2. `Modules/Protocol/role/output_format.md`",
            "2. `Modules/Protocol/reviews/full_review.md`",
        )
        self.assertIn("bootstrap_includes_full_review", rules(skill))

    def test_each_narrow_route_requires_its_owner(self) -> None:
        owners = {
            "git": "git_change_review.md",
            "tests": "test_quality_review.md",
            "sdk": "sdk_code_review.md",
            "feature": "feature_code_review.md",
            "architecture": "architecture_review.md",
            "release": "release_readiness_review.md",
            "delivery": "delivery_risk_review.md",
            "native": "native_plugin_review.md",
        }
        for label, owner in owners.items():
            with self.subTest(route=label):
                skill = GOOD_SKILL.replace(owner, "wrong_review.md")
                self.assertIn(f"narrow_{label}_owner_mismatch", rules(skill))

    def test_missing_narrow_route_is_rejected(self) -> None:
        skill = GOOD_SKILL.replace(
            "- tests as the primary target -> `test_quality_review.md`\n",
            "",
        )
        self.assertIn("narrow_tests_route_missing", rules(skill))

    def test_each_explicit_full_review_command_must_remain(self) -> None:
        lines = {
            "full_review": "- `xuunity full review ...` -> `reviews/full_review.md`\n",
            "review_all": "- `xuunity review all ...` -> `reviews/full_review.md`\n",
        }
        for label, line in lines.items():
            with self.subTest(route=label):
                start_session = GOOD_START_SESSION.replace(line, "")
                self.assertIn(
                    f"explicit_{label}_route_missing",
                    rules(start_session=start_session),
                )

    def test_generic_review_command_must_remain_narrow(self) -> None:
        missing = GOOD_START_SESSION.replace(
            "- `xuunity review ...` -> `tasks/code_review.md`\n",
            "",
        )
        self.assertIn(
            "generic_review_route_missing",
            rules(start_session=missing),
        )

        wrong_owner = GOOD_START_SESSION.replace(
            "`xuunity review ...` -> `tasks/code_review.md`",
            "`xuunity review ...` -> `reviews/full_review.md`",
        )
        self.assertIn(
            "generic_review_owner_mismatch",
            rules(start_session=wrong_owner),
        )

    def test_explicit_full_review_command_requires_full_review_owner(self) -> None:
        start_session = GOOD_START_SESSION.replace(
            "`xuunity full review ...` -> `reviews/full_review.md`",
            "`xuunity full review ...` -> `reviews/architecture_review.md`",
        )
        self.assertIn(
            "explicit_full_review_owner_mismatch",
            rules(start_session=start_session),
        )

    def test_explicit_full_review_rejects_same_basename_under_wrong_owner(self) -> None:
        start_session = GOOD_START_SESSION.replace(
            "`xuunity full review ...` -> `reviews/full_review.md`",
            "`xuunity full review ...` -> `tasks/full_review.md`",
        )
        self.assertIn(
            "explicit_full_review_owner_mismatch",
            rules(start_session=start_session),
        )


class ReviewRouteContractCliTests(unittest.TestCase):
    def _run(self, skill: str, start_session: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            skill_path = root / "skill.md"
            start_path = root / "start.md"
            skill_path.write_text(skill, encoding="utf-8")
            start_path.write_text(start_session, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--skill",
                    str(skill_path),
                    "--start-session",
                    str(start_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_cli_passes_valid_contract(self) -> None:
        result = self._run(GOOD_SKILL, GOOD_START_SESSION)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("REVIEW ROUTE CONTRACT: PASS", result.stdout)

    def test_cli_fails_route_drift(self) -> None:
        skill = GOOD_SKILL.replace("git_change_review.md", "architecture_review.md")
        result = self._run(skill, GOOD_START_SESSION)
        self.assertEqual(1, result.returncode)
        self.assertIn("narrow_git_owner_mismatch", result.stdout)

    def test_cli_reports_unreadable_input_as_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            start_path = root / "start.md"
            start_path.write_text(GOOD_START_SESSION, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHECKER),
                    "--skill",
                    str(root / "missing.md"),
                    "--start-session",
                    str(start_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn("cannot read review routing input", result.stderr)


if __name__ == "__main__":
    unittest.main()
