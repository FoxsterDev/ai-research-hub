from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import experiment, suite  # noqa: E402

from test_scoring import fixture_doc, score  # noqa: E402
from test_suite import attempt, suite_doc  # noqa: E402


def manifest_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "xuunity.experiment-manifest.v1",
        "experiment_id": "exp-1",
        "hypothesis": "tighter stack rules raise the score median",
        "treatment_variable": "reduced_stack_rules revision",
        "control": {"ref": "rules-r1", "content_sha256": "8" * 64},
        "treatment": {"ref": "rules-r2", "content_sha256": "9" * 64},
        "matrix": {"ref": None, "sha256": "a" * 64},
        "attempt_schedule": {
            "attempts_per_cell": 30,
            "order_policy_id": "interleaved-1",
        },
        "family": {
            "experiment_family_id": "family-opaque-1",
            "family_alpha": 0.05,
            "alpha_spending_method": "bonferroni",
            "multiplicity_method": "holm_bonferroni",
        },
        "f6_exposure_budget": {"max_exposures": 2, "consumed_before": 0},
        "target_metric": {
            "metric_id": "median_lower_bound",
            "direction": "higher_is_better",
            "acceptance_threshold": 90.0,
            "comparison": "treatment_bound_vs_threshold",
        },
        "non_regression_budgets": [
            {
                "metric_id": "worst_valid",
                "direction": "higher_is_better",
                "max_degradation": 50.0,
            }
        ],
        "cost_limit": {"max_model_runs": 120, "max_cost_usd": None},
        "apply_authority": {"holder": "human_review", "auto_apply": False},
        "manifest_hash": None,
    }
    doc.update(overrides)
    return doc


def cohort(count: int, *, gate_decision: str = "pass") -> dict[str, Any]:
    attempts = [
        attempt(
            index,
            score(
                fixture_doc(),
                run_id=f"run-{gate_decision}-{index}",
                gate_decision=gate_decision,
            ),
        )
        for index in range(count)
    ]
    return suite.aggregate_suite(
        suite_doc(), attempts, strict_profile_key="b" * 64, f6_included=True
    )


class ExperimentDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full_cohort = cohort(30)
        cls.weak_cohort = cohort(30, gate_decision="fail")
        cls.smoke_cohort = cohort(3)

    def evaluate(self, manifest: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        control = overrides.pop("control", self.weak_cohort)
        treatment = overrides.pop("treatment", self.full_cohort)
        arguments: dict[str, Any] = {
            "control_suite_ref": "control-cohort",
            "treatment_suite_ref": "treatment-cohort",
            "alpha_charge": 0.025,
            "alpha_spent_before": 0.0,
        }
        arguments.update(overrides)
        return experiment.evaluate_experiment(
            manifest, control, treatment, **arguments
        )

    def test_accepted_when_target_met_and_budgets_respected(self) -> None:
        result = self.evaluate(manifest_doc())
        self.assertEqual("accepted", result["status"])
        self.assertEqual(100.0, result["statistics"]["treatment_value"])
        (regression,) = result["non_regression"]
        self.assertTrue(regression["respected"])
        self.assertEqual(
            "not_requested", result["apply_authorization"]["state"]
        )
        self.assertEqual(0.025, result["family_ledger"]["alpha_spent_after"])

    def test_rejected_below_threshold(self) -> None:
        manifest = manifest_doc(
            target_metric={
                "metric_id": "median_lower_bound",
                "direction": "higher_is_better",
                "acceptance_threshold": 100.5,
                "comparison": "treatment_bound_vs_threshold",
            }
        )
        result = self.evaluate(manifest)
        self.assertEqual("rejected", result["status"])

    def test_rejected_on_non_regression_breach(self) -> None:
        manifest = manifest_doc(
            non_regression_budgets=[
                {
                    "metric_id": "worst_valid",
                    "direction": "higher_is_better",
                    "max_degradation": 5.0,
                }
            ]
        )
        result = self.evaluate(
            manifest, control=self.full_cohort, treatment=self.weak_cohort
        )
        self.assertEqual("rejected", result["status"])
        (regression,) = result["non_regression"]
        self.assertFalse(regression["respected"])
        self.assertIn(
            "non_regression_budget_exceeded:worst_valid",
            result["reason_codes"],
        )

    def test_delta_comparison(self) -> None:
        manifest = manifest_doc(
            target_metric={
                "metric_id": "score_median",
                "direction": "higher_is_better",
                "acceptance_threshold": 10.0,
                "comparison": "treatment_vs_control_delta",
            }
        )
        result = self.evaluate(manifest)
        self.assertEqual("accepted", result["status"])
        self.assertEqual(69.9, result["statistics"]["control_value"])

    def test_insufficient_confidence_is_inconclusive(self) -> None:
        result = self.evaluate(manifest_doc(), treatment=self.smoke_cohort)
        self.assertEqual("inconclusive", result["status"])
        self.assertIn(
            "statistical_confidence_insufficient", result["reason_codes"]
        )

    def test_alpha_exhaustion_is_inconclusive(self) -> None:
        result = self.evaluate(
            manifest_doc(), alpha_spent_before=0.04, alpha_charge=0.02
        )
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("family_alpha_exhausted", result["reason_codes"])
        self.assertAlmostEqual(
            0.06, result["family_ledger"]["alpha_spent_after"]
        )

    def test_f6_budget_overrun_is_inconclusive(self) -> None:
        result = self.evaluate(manifest_doc(), f6_exposures_used=3)
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("f6_exposure_budget_exceeded", result["reason_codes"])

    def test_unknown_metric_fails_closed(self) -> None:
        manifest = manifest_doc(
            target_metric={
                "metric_id": "vibes",
                "direction": "higher_is_better",
                "acceptance_threshold": 1.0,
                "comparison": "treatment_bound_vs_threshold",
            }
        )
        with self.assertRaises(experiment.ExperimentError):
            self.evaluate(manifest)

    def test_manifest_hash_is_stable_and_recorded(self) -> None:
        manifest = manifest_doc()
        result = self.evaluate(manifest)
        self.assertEqual(
            experiment.manifest_hash(manifest), result["manifest_hash"]
        )
        pinned = manifest_doc(manifest_hash=experiment.manifest_hash(manifest))
        self.assertEqual(
            result["manifest_hash"],
            self.evaluate(pinned)["manifest_hash"],
        )

    def test_suite_refs_are_content_hashed(self) -> None:
        result = self.evaluate(manifest_doc())
        self.assertEqual(
            suite.suite_result_sha256(self.full_cohort),
            result["treatment_suite"]["suite_result_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
