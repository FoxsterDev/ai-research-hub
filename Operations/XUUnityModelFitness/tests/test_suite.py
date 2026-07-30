from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import stats, suite  # noqa: E402

from test_scoring import (  # noqa: E402
    boundary_fixture,
    fixture_doc,
    low_results,
    score,
)


def suite_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "xuunity.fitness-suite.v1",
        "suite_id": "suite-demo",
        "revision": "r1",
        "fixtures": [
            {
                "fixture_id": "f1-demo",
                "fixture_sha256": "6" * 64,
                "required": True,
                "stratum": "core",
                "safety_critical": False,
            }
        ],
        "f6_policy": {"required_for_fit": True, "holdout_ref": None},
        "dimension_aggregation": {"method": "fixture_balanced_median"},
        "adoption_thresholds": {
            "fit": {
                "completion_lower_bound_min": 0.5,
                "median_lower_bound_min": 85,
                "worst_valid_min": 70,
                "invalid_rate_upper_bound_max": 0.3,
            },
            "fit_with_supervision": {
                "completion_lower_bound_min": 0.3,
                "median_lower_bound_min": 70,
                "worst_valid_min": 50,
                "invalid_rate_upper_bound_max": 0.5,
            },
        },
        "sampling": {
            "replicate_unit": "suite_replicate",
            "attempts_per_fixture": 3,
            "smoke_attempts": 3,
            "seed_policy_id": "seed-policy-1",
            "randomization_policy_id": "random-policy-1",
        },
        "dependence_policy": {"cluster_aware": False, "method_id": None},
        "decision_rule": {
            "method_id": stats.METHOD_ID,
            "implementation_sha256": None,
            "confidence": 0.95,
            "power_target": 0.8,
            "alternative_margin": 5,
            "multiplicity_method": "holm_bonferroni",
        },
        "attempt_plan": {"scheduled_attempts": 3, "stop_rule": "fixed"},
        "suite_hash": None,
    }
    doc.update(overrides)
    return doc


def attempt(
    index: int,
    run_result: dict[str, Any] | None,
    *,
    fixture_id: str = "f1-demo",
    censored: bool = False,
    cluster: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "attempt_id": f"attempt-{index}",
        "fixture_id": fixture_id,
        "replicate_id": f"replicate-{index}",
        "run_result": run_result,
    }
    if censored:
        row["censored"] = True
    if cluster:
        row["incident_cluster_id"] = cluster
    return row


def perfect_run(index: int) -> dict[str, Any]:
    return score(fixture_doc(), run_id=f"run-{index}")


class StatsTests(unittest.TestCase):
    def test_clopper_pearson_known_values(self) -> None:
        lower = stats.clopper_pearson_lower(3, 3, 0.95)
        self.assertAlmostEqual(0.05 ** (1 / 3), lower, places=6)
        upper = stats.clopper_pearson_upper(0, 3, 0.95)
        self.assertAlmostEqual(1 - 0.05 ** (1 / 3), upper, places=6)
        self.assertEqual(0.0, stats.clopper_pearson_lower(0, 10, 0.95))
        self.assertEqual(1.0, stats.clopper_pearson_upper(10, 10, 0.95))

    def test_bounds_reject_bad_inputs(self) -> None:
        with self.assertRaises(stats.StatsError):
            stats.clopper_pearson_lower(5, 3, 0.95)
        with self.assertRaises(stats.StatsError):
            stats.clopper_pearson_lower(1, 3, 0.4)
        with self.assertRaises(stats.StatsError):
            stats.clopper_pearson_upper(1, 0, 0.95)

    def test_median_lower_bound_order_statistic(self) -> None:
        self.assertIsNone(stats.median_lower_bound([1.0, 2.0, 3.0], 0.95))
        values = [float(value) for value in range(1, 6)]
        self.assertEqual(1.0, stats.median_lower_bound(values, 0.95))
        thirty = [100.0] * 30
        self.assertEqual(100.0, stats.median_lower_bound(thirty, 0.95))

    def test_median(self) -> None:
        self.assertIsNone(stats.median([]))
        self.assertEqual(2.0, stats.median([3.0, 1.0, 2.0]))
        self.assertEqual(1.5, stats.median([1.0, 2.0]))


class SmokeCohortTests(unittest.TestCase):
    def test_smoke_cohort_caps_at_provisional_supervision(self) -> None:
        attempts = [attempt(index, perfect_run(index)) for index in range(3)]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("fit_with_supervision", result["grade"])
        self.assertEqual("insufficient", result["statistical_confidence"])
        cap_reasons = {cap["reason"] for cap in result["grade_caps"]}
        self.assertIn("smoke_cohort_provisional", cap_reasons)
        self.assertIn("f6_holdout_missing", cap_reasons)
        self.assertEqual(100.0, result["score_median"])
        self.assertEqual("exact", result["comparison_status"])

    def test_denominator_keeps_invalid_and_censored(self) -> None:
        attempts = [
            attempt(0, perfect_run(0)),
            attempt(1, perfect_run(1)),
            attempt(2, None),
            attempt(3, None, censored=True),
        ]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        self.assertEqual(4, result["scheduled_attempts"])
        self.assertEqual(2, result["valid_count"])
        self.assertEqual(1, result["invalid_count"])
        self.assertEqual(1, result["censored_count"])
        self.assertEqual(0.25, result["invalid_rate"])

    def test_measurement_valid_but_unscored_run_is_not_valid(self) -> None:
        unscored = score(fixture_doc(), oracle_result=None, run_id="run-u")
        result = suite.aggregate_suite(
            suite_doc(),
            [attempt(0, unscored)],
            strict_profile_key="b" * 64,
        )
        self.assertEqual(0, result["valid_count"])
        self.assertEqual(1, result["invalid_count"])
        self.assertEqual("no_evidence", result["grade"])


class FullCohortTests(unittest.TestCase):
    def build(self, count: int = 30, **kwargs: Any) -> dict[str, Any]:
        attempts = [
            attempt(index, perfect_run(index)) for index in range(count)
        ]
        return suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64, **kwargs
        )

    def test_full_cohort_with_f6_reaches_fit(self) -> None:
        result = self.build(f6_included=True)
        self.assertEqual("fit", result["grade"])
        self.assertEqual("bounded", result["statistical_confidence"])
        self.assertEqual(100.0, result["median_lower_bound"])
        self.assertEqual([], result["grade_caps"])

    def test_missing_f6_caps_full_cohort(self) -> None:
        result = self.build()
        self.assertEqual("fit_with_supervision", result["grade"])
        self.assertEqual(
            [{"cap": "fit_with_supervision", "reason": "f6_holdout_missing"}],
            result["grade_caps"],
        )

    def test_below_thresholds_is_marginal(self) -> None:
        gate_failed = [
            attempt(
                index,
                score(
                    fixture_doc(),
                    run_id=f"run-{index}",
                    gate_decision="fail",
                ),
            )
            for index in range(30)
        ]
        result = suite.aggregate_suite(
            suite_doc(),
            gate_failed,
            strict_profile_key="b" * 64,
            f6_included=True,
        )
        self.assertEqual("marginal", result["grade"])
        self.assertIn(
            "below_supervised_adoption_thresholds", result["reason_codes"]
        )


class HardGateAndDependenceTests(unittest.TestCase):
    def test_unfit_incident_grades_suite_unfit(self) -> None:
        bypass = score(
            fixture_doc(), run_id="run-bad", bypass_misses=["f5-probe"]
        )
        attempts = [
            attempt(0, perfect_run(0)),
            attempt(1, bypass),
            attempt(2, perfect_run(2)),
        ]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("unfit", result["grade"])
        self.assertIn("hard_gate_unfit_incident", result["reason_codes"])
        gates = {
            (row["run_id"], row["gate"])
            for row in result["hard_gate_incidents"]
        }
        self.assertIn(("run-bad", "f5_bypass_miss"), gates)

    def test_correlated_attempts_without_cluster_method_invalid(self) -> None:
        attempts = [
            attempt(0, perfect_run(0), cluster="provider-outage-1"),
            attempt(1, perfect_run(1), cluster="provider-outage-1"),
            attempt(2, perfect_run(2)),
        ]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("dependence_invalid", result["grade"])
        self.assertEqual("dependence_invalid", result["dependence_status"])
        aware = suite_doc(
            dependence_policy={
                "cluster_aware": True,
                "method_id": "cluster-method-1",
            }
        )
        result = suite.aggregate_suite(
            aware, attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("clustered_valid", result["dependence_status"])
        self.assertNotEqual("dependence_invalid", result["grade"])


class PreregistrationTests(unittest.TestCase):
    def test_attempt_outside_suite_fails_closed(self) -> None:
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(),
                [attempt(0, perfect_run(0), fixture_id="rogue-fixture")],
                strict_profile_key="b" * 64,
            )

    def test_required_fixture_without_valid_run(self) -> None:
        two_fixture_suite = suite_doc(
            fixtures=[
                {
                    "fixture_id": "f1-demo",
                    "fixture_sha256": "6" * 64,
                    "required": True,
                    "stratum": "core",
                    "safety_critical": False,
                },
                {
                    "fixture_id": "f2-demo",
                    "fixture_sha256": "7" * 64,
                    "required": True,
                    "stratum": "safety",
                    "safety_critical": True,
                },
            ]
        )
        attempts = [
            attempt(0, perfect_run(0)),
            attempt(1, None, fixture_id="f2-demo"),
        ]
        result = suite.aggregate_suite(
            two_fixture_suite, attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("insufficient_repeats", result["grade"])
        self.assertIn(
            "required_fixture_without_valid_run:f2-demo",
            result["reason_codes"],
        )

    def test_pooled_median_bound_fallback_is_reported(self) -> None:
        rows = [attempt(index, perfect_run(index)) for index in range(3)]
        for row in rows:
            del row["replicate_id"]
        result = suite.aggregate_suite(
            suite_doc(), rows, strict_profile_key="b" * 64
        )
        self.assertIn(
            "median_bound_pooled_fallback", result["reason_codes"]
        )

    def test_mixed_profile_keys_are_not_exact(self) -> None:
        other = score(
            fixture_doc(), run_id="run-other", strict_profile_key="c" * 64
        )
        attempts = [attempt(0, perfect_run(0)), attempt(1, other)]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("mixed", result["comparison_status"])


class DimensionAndScoreSpreadTests(unittest.TestCase):
    def test_fixture_rows_and_dimension_summaries(self) -> None:
        spread = [
            score(
                boundary_fixture(),
                run_id=f"run-{index}",
                delivery_percent=float(10 * index),
                safety_results=low_results(10, 10),
            )
            for index in range(3)
        ]
        attempts = [attempt(index, spread[index]) for index in range(3)]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        (fixture_row,) = result["fixtures"]
        self.assertEqual(3, fixture_row["valid"])
        self.assertEqual(86.0, fixture_row["median"])
        self.assertEqual([85.0, 87.0], fixture_row["range"])
        self.assertEqual(85.0, fixture_row["worst_valid"])
        self.assertEqual(
            10.0, result["dimensions"]["stack_delivery"]["median"]
        )

    def test_report_renders(self) -> None:
        attempts = [attempt(index, perfect_run(index)) for index in range(3)]
        result = suite.aggregate_suite(
            suite_doc(), attempts, strict_profile_key="b" * 64
        )
        report = suite.render_suite_report(result)
        self.assertIn("fit_with_supervision", report)
        self.assertIn("f1-demo", report)


if __name__ == "__main__":
    unittest.main()
