from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import experiment, suite  # noqa: E402

from test_scoring import fixture_doc, score  # noqa: E402
from test_suite import attempt, suite_doc  # noqa: E402


def manifest_doc(**overrides: Any) -> dict[str, Any]:
    default_suite = suite_doc(attempts_per_fixture=30)
    default_arm = {
        "suite_id": default_suite["suite_id"],
        "suite_hash": suite.suite_hash(default_suite),
        "strict_profile_key": "b" * 64,
    }
    doc: dict[str, Any] = {
        "schema_version": "xuunity.experiment-manifest.v2",
        "experiment_id": "exp-1",
        "hypothesis": "tighter stack rules raise the score median",
        "treatment_variable": "reduced_stack_rules revision",
        "control": {"ref": "rules-r1", "content_sha256": "8" * 64},
        "treatment": {"ref": "rules-r2", "content_sha256": "9" * 64},
        "suite_arms": {
            "control": dict(default_arm),
            "treatment": dict(default_arm),
        },
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
        "f6_exposure_budget": {
            "max_exposures": 2,
            "consumed_artifact_hashes": [],
        },
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
                enforcement_mode="authoritative",
                comparison_status="exact_repeat",
            ),
        )
        for index in range(count)
    ]
    return suite.aggregate_suite(
        suite_doc(attempts_per_fixture=count),
        attempts,
        strict_profile_key="b" * 64,
    )


def suite_arm(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite_id": result["suite_id"],
        "suite_hash": result["suite_hash"],
        "strict_profile_key": result["strict_profile_key"],
    }


def manifest_for(
    control: dict[str, Any],
    treatment: dict[str, Any],
    attempts_per_cell: int,
    **overrides: Any,
) -> dict[str, Any]:
    return manifest_doc(
        suite_arms={
            "control": suite_arm(control),
            "treatment": suite_arm(treatment),
        },
        attempt_schedule={
            "attempts_per_cell": attempts_per_cell,
            "order_policy_id": "interleaved-1",
        },
        **overrides,
    )


class ExperimentDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full_cohort = cohort(30)
        cls.weak_cohort = cohort(30, gate_decision="fail")
        cls.smoke_cohort = cohort(3)
        cls.smoke_control = cohort(3, gate_decision="fail")

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
        manifest = manifest_for(
            self.smoke_control, self.smoke_cohort, attempts_per_cell=3
        )
        result = self.evaluate(
            manifest,
            control=self.smoke_control,
            treatment=self.smoke_cohort,
        )
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
        from test_suite import F6_KEY, F6_KEY_ID, f6_cohort

        doc, rows, artifact = f6_cohort(30)
        with_f6 = suite.aggregate_suite(
            doc,
            rows,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        manifest = manifest_for(
            self.weak_cohort,
            with_f6,
            attempts_per_cell=30,
            f6_exposure_budget={
                "max_exposures": 0,
                "consumed_artifact_hashes": [],
            },
        )
        result = self.evaluate(
            manifest,
            treatment=with_f6,
            f6_artifacts={artifact["artifact_hash"]: artifact},
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("f6_exposure_budget_exceeded", result["reason_codes"])

    def test_ungraded_suite_cannot_be_accepted(self) -> None:
        diagnostic_attempts = [
            attempt(index, score(fixture_doc(), run_id=f"diag-{index}"))
            for index in range(30)
        ]
        diagnostic = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=30),
            diagnostic_attempts,
            strict_profile_key="b" * 64,
        )
        result = self.evaluate(manifest_doc(), treatment=diagnostic)
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("suite_not_adoption_graded", result["reason_codes"])

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

    def test_mutated_pinned_manifest_is_rejected(self) -> None:
        manifest = manifest_doc()
        manifest["manifest_hash"] = experiment.manifest_hash(manifest)
        manifest["f6_exposure_budget"]["max_exposures"] = 99
        with self.assertRaises(experiment.ExperimentError):
            self.evaluate(manifest)

    def test_manifest_schedule_must_match_both_arms(self) -> None:
        manifest = manifest_doc(
            attempt_schedule={
                "attempts_per_cell": 999,
                "order_policy_id": "interleaved-1",
            }
        )
        with self.assertRaises(experiment.ExperimentError):
            self.evaluate(manifest)

    def test_same_cohort_cannot_be_both_arms(self) -> None:
        manifest = manifest_for(
            self.full_cohort, self.full_cohort, attempts_per_cell=30
        )
        with self.assertRaises(experiment.ExperimentError):
            self.evaluate(
                manifest,
                control=self.full_cohort,
                treatment=self.full_cohort,
            )

    def test_unfit_treatment_cannot_be_accepted(self) -> None:
        attempts = [
            attempt(
                index,
                score(
                    fixture_doc(),
                    run_id=f"unfit-{index}",
                    enforcement_mode="authoritative",
                    comparison_status="exact_repeat",
                    bypass_misses=["f5-probe"],
                ),
            )
            for index in range(30)
        ]
        unfit = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=30),
            attempts,
            strict_profile_key="b" * 64,
        )
        manifest = manifest_for(
            self.weak_cohort, unfit, attempts_per_cell=30
        )
        result = self.evaluate(manifest, treatment=unfit)
        self.assertEqual("rejected", result["status"])
        self.assertIn("treatment_suite_unfit", result["reason_codes"])

    def test_forged_verified_f6_summary_is_rejected(self) -> None:
        forged = deepcopy(self.full_cohort)
        forged["f6_evidence"] = {
            "status": "verified_pass",
            "evidence_ref": "protected://forged.json",
            "holdout_ref": "forged-holdout",
            "fixture_id": "f6-forged",
            "issuer_key_id": "forged-key",
            "artifact_hash": "f" * 64,
        }
        forged["cohort_hash"] = "e" * 64
        manifest = manifest_for(
            self.weak_cohort, forged, attempts_per_cell=30
        )
        with self.assertRaises(experiment.ExperimentError):
            self.evaluate(manifest, treatment=forged)

    def test_consumed_f6_artifact_replay_is_inconclusive(self) -> None:
        from test_suite import F6_KEY, F6_KEY_ID, f6_cohort

        doc, rows, artifact = f6_cohort(30)
        with_f6 = suite.aggregate_suite(
            doc,
            rows,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        manifest = manifest_for(
            self.weak_cohort,
            with_f6,
            attempts_per_cell=30,
            f6_exposure_budget={
                "max_exposures": 2,
                "consumed_artifact_hashes": [artifact["artifact_hash"]],
            },
        )
        result = self.evaluate(
            manifest,
            treatment=with_f6,
            f6_artifacts={artifact["artifact_hash"]: artifact},
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("f6_artifact_replay", result["reason_codes"])

    def test_suite_refs_are_content_hashed(self) -> None:
        result = self.evaluate(manifest_doc())
        self.assertEqual(
            suite.suite_result_sha256(self.full_cohort),
            result["treatment_suite"]["suite_result_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
