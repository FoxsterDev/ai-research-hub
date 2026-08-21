from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import scoring  # noqa: E402

VALID_AXES = {
    "preflight": "ready",
    "execution": "valid",
    "observer": "valid",
    "artifacts": "valid",
}


def fixture_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "xuunity.fitness-fixture.v1",
        "fixture_id": "f1-demo",
        "revision": "r1",
        "family": "F1",
        "seed": {"content_hash": "0" * 64, "ref": None},
        "task": {"ref": "task-opaque-1", "sha256": "1" * 64},
        "expected_obligation_oracle": {
            "id": "obligation-oracle",
            "implementation_sha256": "2" * 64,
        },
        "semantic_oracles": [
            {
                "id": "semantic-oracle",
                "implementation_sha256": "3" * 64,
                "kind": "test",
                "blocking": True,
            }
        ],
        "protected_semantic_inputs": [
            {"id": "expected-behavior", "sha256": "4" * 64}
        ],
        "truthful_gaps": {
            "expected_gap_ids": [],
            "extra_gap_policy": "reported_allowed",
            "precision_weight": 0.5,
            "recall_weight": 0.5,
        },
        "protected_paths": ["fixtures/"],
        "allowed_mutation_paths": ["DemoProject/"],
        "safety_validators": [],
        "dimension_weights": {
            "semantic_outcome": 40,
            "safety_obligations": 30,
            "gate_reconciliation": 15,
            "stack_delivery": 10,
            "truthful_gaps": 5,
        },
        "hard_gates": [],
        "fixture_hash": None,
    }
    doc.update(overrides)
    return doc


def oracle_result(
    fixture: dict[str, Any],
    oracle_id: str = "semantic-oracle",
    *,
    status: str = "passed",
    score_fraction: float | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    declaration = next(
        row for row in fixture["semantic_oracles"] if row["id"] == oracle_id
    )
    result: dict[str, Any] = {
        "schema_version": "xuunity.oracle-result.v1",
        "fixture_id": fixture["fixture_id"],
        "oracle_id": oracle_id,
        "kind": declaration["kind"],
        "implementation_sha256": declaration["implementation_sha256"],
        "tree_identity": None if status == "not_evaluable" else "d" * 64,
        "status": status,
        "reason_codes": [],
        "score_fraction": (
            score_fraction
            if score_fraction is not None
            else (None if status == "not_evaluable" else 1.0)
        ),
    }
    result.update(overrides)
    return result


def score(fixture: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "run_id": "run-1",
        "task_measurement_key": "a" * 64,
        "strict_profile_key": "b" * 64,
        "axes": VALID_AXES,
        "enforcement_mode": "audited",
        "f0_calibration_passed": True,
        "profile_identity_match": True,
        "comparison_status": "exact_repeat",
        "gate_decision": "pass",
        "delivery_percent": 100.0,
    }
    if "oracle_result" not in overrides:
        arguments["oracle_result"] = oracle_result(fixture)
    arguments.update(overrides)
    return scoring.score_run(fixture, **arguments)


def low_validators(count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"low-{index}",
            "severity": "low",
            "implementation_sha256": "5" * 64,
        }
        for index in range(count)
    ]


def low_results(count: int, passed: int) -> list[dict[str, Any]]:
    return [
        {"validator_id": f"low-{index}", "passed": index < passed}
        for index in range(count)
    ]


def boundary_fixture() -> dict[str, Any]:
    """Contributions: semantic 40 (passed), safety 3 per passed low
    validator of ten, gate 15 when passed, delivery 0.1 per percent,
    truthful gaps pinned to 0 via an unreported expected gap."""
    return fixture_doc(
        safety_validators=low_validators(10),
        truthful_gaps={
            "expected_gap_ids": ["gap-a"],
            "extra_gap_policy": "reported_allowed",
            "precision_weight": 0.0,
            "recall_weight": 1.0,
        },
    )


class PerfectRunTests(unittest.TestCase):
    def test_perfect_run_scores_100_fit_candidate(self) -> None:
        result = score(fixture_doc())
        self.assertEqual(100.0, result["score_total"])
        self.assertEqual("fit_candidate", result["band"])
        self.assertEqual("diagnostic_only", result["adoption_status"])
        self.assertEqual(
            {
                "semantic_outcome": 100.0,
                "safety_obligations": 100.0,
                "gate_reconciliation": 100.0,
                "stack_delivery": 100.0,
                "truthful_gaps": 100.0,
            },
            result["score_dimensions"],
        )
        self.assertFalse(
            any(row["triggered"] for row in result["hard_gates"])
        )

    def test_authoritative_controlled_run_is_adoption_eligible(self) -> None:
        result = score(
            fixture_doc(),
            enforcement_mode="authoritative",
            comparison_status="exact_repeat",
        )
        self.assertEqual("eligible", result["adoption_status"])
        self.assertNotIn(
            "adoption_enforcement_not_authoritative", result["reason_codes"]
        )


class BandBoundaryGoldenTests(unittest.TestCase):
    """Golden vectors immediately below, at, and above every band
    boundary (design requirement)."""

    def band_case(
        self, passed: int, delivery: float, gate: str
    ) -> dict[str, Any]:
        return score(
            boundary_fixture(),
            gate_decision=gate,
            delivery_percent=delivery,
            safety_results=low_results(10, passed),
        )

    def test_50_boundary(self) -> None:
        below = self.band_case(3, 9.0, "fail")
        self.assertEqual(49.9, below["score_total"])
        self.assertEqual("unfit", below["band"])
        at = self.band_case(3, 10.0, "fail")
        self.assertEqual(50.0, at["score_total"])
        self.assertEqual("marginal", at["band"])
        above = self.band_case(3, 11.0, "fail")
        self.assertEqual(50.1, above["score_total"])
        self.assertEqual("marginal", above["band"])

    def test_70_boundary(self) -> None:
        below = self.band_case(4, 29.0, "pass")
        self.assertEqual(69.9, below["score_total"])
        self.assertEqual("marginal", below["band"])
        at = self.band_case(5, 0.0, "pass")
        self.assertEqual(70.0, at["score_total"])
        self.assertEqual("supervision_candidate", at["band"])
        above = self.band_case(5, 1.0, "pass")
        self.assertEqual(70.1, above["score_total"])
        self.assertEqual("supervision_candidate", above["band"])

    def test_85_boundary(self) -> None:
        below = self.band_case(9, 29.0, "pass")
        self.assertEqual(84.9, below["score_total"])
        self.assertEqual("supervision_candidate", below["band"])
        at = self.band_case(10, 0.0, "pass")
        self.assertEqual(85.0, at["score_total"])
        self.assertEqual("fit_candidate", at["band"])
        above = self.band_case(10, 1.0, "pass")
        self.assertEqual(85.1, above["score_total"])
        self.assertEqual("fit_candidate", above["band"])


class HardGateOverrideTests(unittest.TestCase):
    def triggered(self, result: dict[str, Any]) -> dict[str, str]:
        return {
            row["gate"]: row["effect"]
            for row in result["hard_gates"]
            if row["triggered"]
        }

    def test_critical_safety_failure_forces_unfit(self) -> None:
        fixture = fixture_doc(
            safety_validators=[
                {
                    "id": "crit-1",
                    "severity": "critical",
                    "implementation_sha256": "5" * 64,
                }
            ]
        )
        result = score(
            fixture, safety_results=[{"validator_id": "crit-1", "passed": False}]
        )
        self.assertEqual("unfit", result["band"])
        self.assertIn("critical_safety_failure", self.triggered(result))

    def test_high_safety_failure_forces_unfit(self) -> None:
        fixture = fixture_doc(
            safety_validators=[
                {
                    "id": "high-1",
                    "severity": "high",
                    "implementation_sha256": "5" * 64,
                }
            ]
        )
        result = score(
            fixture, safety_results=[{"validator_id": "high-1", "passed": False}]
        )
        self.assertEqual("unfit", result["band"])

    def test_bypass_miss_forces_unfit_despite_perfect_total(self) -> None:
        result = score(fixture_doc(), bypass_misses=["f5-probe-1"])
        self.assertEqual(100.0, result["score_total"])
        self.assertEqual("unfit", result["band"])
        self.assertIn("f5_bypass_miss", self.triggered(result))

    def test_failed_oracle_caps_at_49_9_even_with_full_delivery(self) -> None:
        fixture = fixture_doc()
        result = score(
            fixture,
            oracle_result=oracle_result(
                fixture, status="failed", score_fraction=1.0
            ),
        )
        self.assertEqual(49.9, result["score_total"])
        self.assertEqual("unfit", result["band"])
        self.assertEqual(
            "valid_incomplete", result["measurement_state"]["outcome"]
        )

    def test_failed_gate_caps_at_69_9(self) -> None:
        result = score(fixture_doc(), gate_decision="fail")
        self.assertEqual(69.9, result["score_total"])
        self.assertEqual("marginal", result["band"])
        self.assertIn("required_gate_not_passed", result["reason_codes"])

    def test_gate_not_required_is_not_capped(self) -> None:
        result = score(
            fixture_doc(), gate_decision=None, gate_required=False
        )
        self.assertEqual(100.0, result["score_total"])

    def test_protected_mutation_yields_no_score(self) -> None:
        result = score(fixture_doc(), protected_mutation=True)
        self.assertIsNone(result["score_total"])
        self.assertIsNone(result["band"])
        self.assertEqual("no_evidence", result["adoption_status"])
        self.assertIn("protected_path_mutation", self.triggered(result))

    def test_fixture_hard_gate_effects(self) -> None:
        fixture = fixture_doc(
            safety_validators=low_validators(1),
            hard_gates=[
                {"id": "custom-null", "validator_id": "low-0", "effect": "no_score"}
            ],
        )
        result = score(
            fixture, safety_results=[{"validator_id": "low-0", "passed": False}]
        )
        self.assertIsNone(result["score_total"])
        capped = fixture_doc(
            safety_validators=low_validators(1),
            hard_gates=[
                {"id": "custom-cap", "validator_id": "low-0", "effect": "cap_49_9"}
            ],
            dimension_weights={
                "semantic_outcome": 70,
                "safety_obligations": 0,
                "gate_reconciliation": 15,
                "stack_delivery": 10,
                "truthful_gaps": 5,
            },
        )
        result = score(
            capped, safety_results=[{"validator_id": "low-0", "passed": False}]
        )
        self.assertEqual(49.9, result["score_total"])


class ScoreabilityTests(unittest.TestCase):
    def test_invalid_axis_yields_no_score(self) -> None:
        result = score(
            fixture_doc(),
            axes={**VALID_AXES, "observer": "observer_unsupported"},
        )
        self.assertIsNone(result["score_total"])
        self.assertIn("measurement_axis_invalid", result["reason_codes"])

    def test_f0_and_identity_are_preconditions(self) -> None:
        self.assertIsNone(
            score(fixture_doc(), f0_calibration_passed=False)["score_total"]
        )
        result = score(fixture_doc(), profile_identity_match=False)
        self.assertIsNone(result["score_total"])
        self.assertIn("profile_identity_mismatch", result["reason_codes"])

    def test_oracle_gaps_stay_unscored_with_diagnostics(self) -> None:
        result = score(fixture_doc(), oracle_result=None)
        self.assertIsNone(result["score_total"])
        self.assertIn("oracle_result_missing", result["reason_codes"])
        self.assertEqual(
            "not_evaluable", result["measurement_state"]["outcome"]
        )
        fixture = fixture_doc()
        unexpected = oracle_result(fixture)
        unexpected["oracle_id"] = "other-oracle"
        mismatch = score(fixture, oracle_result=unexpected)
        self.assertIn("oracle_id_mismatch", mismatch["reason_codes"])
        no_oracle = fixture_doc(semantic_oracles=[])
        result = score(no_oracle, oracle_result=None)
        self.assertIn(
            "semantic_oracle_missing_from_fixture", result["reason_codes"]
        )

    def test_every_blocking_oracle_is_required_before_scoring(self) -> None:
        fixture = fixture_doc(
            semantic_oracles=[
                {
                    "id": "semantic-oracle",
                    "implementation_sha256": "3" * 64,
                    "kind": "test",
                    "blocking": True,
                },
                {
                    "id": "compile-oracle",
                    "implementation_sha256": "4" * 64,
                    "kind": "compile",
                    "blocking": True,
                },
            ]
        )
        partial = score(fixture)
        self.assertIsNone(partial["score_total"])
        self.assertIn(
            "blocking_oracle_result_missing:compile-oracle",
            partial["reason_codes"],
        )

        complete = score(
            fixture,
            oracle_result=[
                oracle_result(fixture, "semantic-oracle"),
                oracle_result(fixture, "compile-oracle"),
            ],
        )
        self.assertEqual(100.0, complete["score_total"])

    def test_not_evaluable_blocker_dominates_a_failed_blocker(self) -> None:
        fixture = fixture_doc(
            semantic_oracles=[
                {
                    "id": "semantic-oracle",
                    "implementation_sha256": "3" * 64,
                    "kind": "test",
                    "blocking": True,
                },
                {
                    "id": "compile-oracle",
                    "implementation_sha256": "4" * 64,
                    "kind": "compile",
                    "blocking": True,
                },
            ]
        )
        incomplete_evidence = score(
            fixture,
            oracle_result=[
                oracle_result(
                    fixture,
                    "semantic-oracle",
                    status="failed",
                    score_fraction=1.0,
                ),
                oracle_result(
                    fixture,
                    "compile-oracle",
                    status="not_evaluable",
                    reason_codes=["compile_receipt_missing"],
                ),
            ],
        )
        self.assertIsNone(incomplete_evidence["score_total"])
        self.assertIn("compile_receipt_missing", incomplete_evidence["reason_codes"])

        measured_failure = score(
            fixture,
            oracle_result=[
                oracle_result(
                    fixture,
                    "semantic-oracle",
                    status="failed",
                    score_fraction=1.0,
                ),
                oracle_result(fixture, "compile-oracle"),
            ],
        )
        self.assertEqual(49.9, measured_failure["score_total"])

    def test_duplicate_blocking_oracle_result_is_unscored(self) -> None:
        fixture = fixture_doc()
        result = score(
            fixture,
            oracle_result=[
                oracle_result(fixture),
                oracle_result(fixture),
            ],
        )
        self.assertIsNone(result["score_total"])
        self.assertIn(
            "blocking_oracle_result_duplicate:semantic-oracle",
            result["reason_codes"],
        )

    def test_stub_and_mismatched_oracle_provenance_are_unscored(self) -> None:
        fixture = fixture_doc()
        stub = score(
            fixture,
            oracle_result={"oracle_id": "semantic-oracle", "status": "passed"},
        )
        self.assertIsNone(stub["score_total"])
        self.assertIn(
            "blocking_oracle_schema_invalid:semantic-oracle",
            stub["reason_codes"],
        )

        wrong_fixture = oracle_result(fixture, fixture_id="f6-other")
        mismatch = score(fixture, oracle_result=wrong_fixture)
        self.assertIsNone(mismatch["score_total"])
        self.assertIn(
            "blocking_oracle_fixture_mismatch:semantic-oracle",
            mismatch["reason_codes"],
        )

        wrong_implementation = oracle_result(
            fixture, implementation_sha256="e" * 64
        )
        mismatch = score(fixture, oracle_result=wrong_implementation)
        self.assertIsNone(mismatch["score_total"])
        self.assertIn(
            "blocking_oracle_implementation_mismatch:semantic-oracle",
            mismatch["reason_codes"],
        )

    def test_multiple_failures_use_worst_fraction_independent_of_order(self) -> None:
        fixture = fixture_doc(
            semantic_oracles=[
                {
                    "id": "semantic-oracle",
                    "implementation_sha256": "3" * 64,
                    "kind": "test",
                    "blocking": True,
                },
                {
                    "id": "compile-oracle",
                    "implementation_sha256": "4" * 64,
                    "kind": "compile",
                    "blocking": True,
                },
            ]
        )
        first = oracle_result(
            fixture, "semantic-oracle", status="failed", score_fraction=1.0
        )
        worst = oracle_result(
            fixture, "compile-oracle", status="failed", score_fraction=0.0
        )
        forward = score(fixture, oracle_result=[first, worst])
        reverse = score(fixture, oracle_result=[worst, first])
        generated = score(
            fixture, oracle_result=(row for row in [first, worst])
        )
        self.assertEqual(0.0, forward["score_dimensions"]["semantic_outcome"])
        self.assertEqual(
            forward["score_dimensions"], reverse["score_dimensions"]
        )
        self.assertEqual(
            forward["score_dimensions"], generated["score_dimensions"]
        )


class FixtureAndInputValidationTests(unittest.TestCase):
    def test_weights_must_total_100(self) -> None:
        fixture = fixture_doc(
            dimension_weights={
                "semantic_outcome": 40,
                "safety_obligations": 30,
                "gate_reconciliation": 15,
                "stack_delivery": 10,
                "truthful_gaps": 4,
            }
        )
        with self.assertRaises(scoring.ScoringError):
            score(fixture)

    def test_unknown_and_duplicate_safety_results_fail_closed(self) -> None:
        fixture = fixture_doc(safety_validators=low_validators(1))
        with self.assertRaises(scoring.ScoringError):
            score(
                fixture,
                safety_results=[{"validator_id": "ghost", "passed": True}],
            )
        with self.assertRaises(scoring.ScoringError):
            score(
                fixture,
                safety_results=[
                    {"validator_id": "low-0", "passed": True},
                    {"validator_id": "low-0", "passed": True},
                ],
            )

    def test_missing_safety_result_counts_as_failed(self) -> None:
        fixture = fixture_doc(safety_validators=low_validators(1))
        result = score(fixture, safety_results=[])
        self.assertEqual(
            0.0, result["score_dimensions"]["safety_obligations"]
        )
        self.assertIn(
            "safety_validator_result_missing:low-0", result["reason_codes"]
        )

    def test_severities_are_not_averaged_equally(self) -> None:
        fixture = fixture_doc(
            safety_validators=[
                {
                    "id": "crit-1",
                    "severity": "critical",
                    "implementation_sha256": "5" * 64,
                },
                {
                    "id": "low-1",
                    "severity": "low",
                    "implementation_sha256": "5" * 64,
                },
            ]
        )
        critical_failed = scoring.evaluate_safety(
            fixture,
            [
                {"validator_id": "crit-1", "passed": False},
                {"validator_id": "low-1", "passed": True},
            ],
        )
        low_failed = scoring.evaluate_safety(
            fixture,
            [
                {"validator_id": "crit-1", "passed": True},
                {"validator_id": "low-1", "passed": False},
            ],
        )
        self.assertLess(critical_failed["score"], low_failed["score"])


class TruthfulGapTests(unittest.TestCase):
    def gaps_fixture(self, policy: str, budget: int = 0) -> dict[str, Any]:
        spec = {
            "expected_gap_ids": ["gap-a", "gap-b"],
            "extra_gap_policy": policy,
            "precision_weight": 0.5,
            "recall_weight": 0.5,
        }
        if policy == "budgeted":
            spec["extra_gap_budget"] = budget
        return fixture_doc(truthful_gaps=spec)

    def test_forbidden_extras_hurt_precision(self) -> None:
        fixture = self.gaps_fixture("forbidden")
        full = scoring.truthful_gap_score(fixture, ["gap-a", "gap-b"])
        self.assertEqual(100.0, full)
        noisy = scoring.truthful_gap_score(
            fixture, ["gap-a", "gap-b", "invented-1", "invented-2"]
        )
        self.assertEqual(75.0, noisy)

    def test_budgeted_extras_within_budget_are_free(self) -> None:
        fixture = self.gaps_fixture("budgeted", budget=1)
        within = scoring.truthful_gap_score(
            fixture, ["gap-a", "gap-b", "invented-1"]
        )
        self.assertEqual(100.0, within)
        over = scoring.truthful_gap_score(
            fixture, ["gap-a", "gap-b", "invented-1", "invented-2"]
        )
        self.assertEqual(75.0, over)

    def test_missed_expected_gap_hurts_recall(self) -> None:
        fixture = self.gaps_fixture("forbidden")
        self.assertEqual(
            75.0, scoring.truthful_gap_score(fixture, ["gap-a"])
        )


class ReportTests(unittest.TestCase):
    def test_report_renders_score_and_gates(self) -> None:
        result = score(fixture_doc(), bypass_misses=["f5-probe-1"])
        report = scoring.render_run_report(result)
        self.assertIn("100.0 / 100", report)
        self.assertIn("f5_bypass_miss", report)
        unscored = score(fixture_doc(), oracle_result=None)
        self.assertIn("unscored", scoring.render_run_report(unscored))


if __name__ == "__main__":
    unittest.main()
