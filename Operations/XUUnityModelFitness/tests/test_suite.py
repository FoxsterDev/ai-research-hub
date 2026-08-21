from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import f6, scoring, stats, suite  # noqa: E402

import xuunity_canonical as xc  # noqa: E402

from test_scoring import (  # noqa: E402
    boundary_fixture,
    fixture_doc,
    low_results,
    score,
)


F6_KEY = b"f6-parent-owned-test-key-0123456789"
F6_KEY_ID = "f6-test-key-1"


def suite_doc(
    *, attempts_per_fixture: int = 3, **overrides: Any
) -> dict[str, Any]:
    default_fixture = fixture_doc()
    fixtures = overrides.pop(
        "fixtures",
        [
            {
                "fixture_id": "f1-demo",
                "fixture_sha256": scoring.fixture_sha256(default_fixture),
                "required": True,
                "stratum": "core",
                "safety_critical": False,
            }
        ],
    )
    plan_rows: list[dict[str, Any]] = []
    order = 0
    for replicate in range(attempts_per_fixture):
        for fixture in fixtures:
            fixture_id = fixture["fixture_id"]
            plan_rows.append(
                {
                    "attempt_id": f"{fixture_id}-attempt-{replicate}",
                    "fixture_id": fixture_id,
                    "replicate_id": f"replicate-{replicate}",
                    "order": order,
                }
            )
            order += 1

    doc: dict[str, Any] = {
        "schema_version": "xuunity.fitness-suite.v2",
        "suite_id": "suite-demo",
        "revision": "r1",
        "fixtures": fixtures,
        "f6_policy": {
            "required_for_fit": True,
            "holdout_ref": None,
            "fixture_id": None,
            "issuer_key_id": None,
        },
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
            "attempts_per_fixture": attempts_per_fixture,
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
        "attempt_plan": {
            "scheduled_attempts": attempts_per_fixture * len(fixtures),
            "stop_rule": "fixed",
            "attempts": plan_rows,
        },
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
    replicate_id: str | None = None,
) -> dict[str, Any]:
    attempt_id = f"{fixture_id}-attempt-{index}"
    row: dict[str, Any] = {
        "attempt_id": attempt_id,
        "fixture_id": fixture_id,
        "replicate_id": replicate_id or f"replicate-{index}",
        "run_result": run_result,
    }
    if censored:
        row["censored"] = True
    if cluster:
        row["incident_cluster_id"] = cluster
    if (
        run_result is not None
        and run_result.get("score_total") is not None
        and not censored
    ):
        row["run_manifest"] = run_manifest(
            attempt_id, fixture_id, run_result
        )
    return row


def run_manifest(
    attempt_id: str,
    fixture_id: str,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    final_tree = run_result["final_tree_identity"]
    manifest: dict[str, Any] = {
        "schema_version": "xuunity.protected-run-manifest.v1",
        "attempt_id": attempt_id,
        "session_attestation_id": "session-test-1",
        "session_attestation_hash": "1" * 64,
        "inputs": {
            "fixture_id": fixture_id,
            "fixture_hash": run_result["fixture_sha256"],
            "seed_identity": "2" * 64,
            "protocol_content_hash": "3" * 64,
            "ruleset_hash": "4" * 64,
            "task_identity": run_result["task_measurement_key"],
        },
        "task_measurement_key": run_result["task_measurement_key"],
        "strict_profile_key": run_result["strict_profile_key"],
        "start_state": {
            "seed_identity": "2" * 64,
            "started": "2026-08-20T00:00:00Z",
        },
        "end_state": {
            "final_tree_identity": final_tree,
            "ended": "2026-08-20T00:01:00Z",
            "terminal_status": "completed",
        },
        "raw_evidence_hashes": {"events.jsonl": "5" * 64},
        "oracle_materialization": (
            {
                "identity": final_tree,
                "ref": f"protected://oracle/{attempt_id}",
            }
            if final_tree is not None
            else None
        ),
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = xc.document_hash(manifest, "manifest_hash")
    return manifest


def perfect_run(index: int) -> dict[str, Any]:
    return eligible_score(fixture_doc(), run_id=f"run-{index}")


def eligible_score(fixture: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return score(
        fixture,
        enforcement_mode="authoritative",
        comparison_status="exact_repeat",
        **overrides,
    )


def f6_fixture_doc() -> dict[str, Any]:
    return fixture_doc(
        fixture_id="f6-demo",
        family="F6",
        seed={"content_hash": "6" * 64, "ref": None},
        task={"ref": "f6-task-opaque-1", "sha256": "7" * 64},
    )


def f6_suite_doc(attempts_per_fixture: int) -> dict[str, Any]:
    f1 = fixture_doc()
    f6_fixture = f6_fixture_doc()
    return suite_doc(
        attempts_per_fixture=attempts_per_fixture,
        fixtures=[
            {
                "fixture_id": "f1-demo",
                "fixture_sha256": scoring.fixture_sha256(f1),
                "required": True,
                "stratum": "core",
                "safety_critical": False,
            },
            {
                "fixture_id": "f6-demo",
                "fixture_sha256": scoring.fixture_sha256(f6_fixture),
                "required": True,
                "stratum": "blinded-holdout",
                "safety_critical": True,
            },
        ],
        f6_policy={
            "required_for_fit": True,
            "holdout_ref": "host-holdout-rotation-1",
            "fixture_id": "f6-demo",
            "issuer_key_id": F6_KEY_ID,
        },
    )


def f6_cohort(
    count: int, *, f6_gate_decision: str = "pass"
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    doc = f6_suite_doc(count)
    rows: list[dict[str, Any]] = []
    f6_rows: list[dict[str, Any]] = []
    for index in range(count):
        rows.append(attempt(index, perfect_run(index)))
        holdout = attempt(
            index,
            eligible_score(
                f6_fixture_doc(),
                run_id=f"f6-run-{index}",
                gate_decision=f6_gate_decision,
            ),
            fixture_id="f6-demo",
        )
        rows.append(holdout)
        f6_rows.append(holdout)
    artifact = sign_f6(doc, f6_rows)
    return doc, rows, artifact


def sign_f6(
    doc: dict[str, Any], f6_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return f6.build_artifact(
        F6_KEY,
        evidence_ref="protected://f6/result-1.json",
        issuer_key_id=F6_KEY_ID,
        holdout_ref="host-holdout-rotation-1",
        suite_id=doc["suite_id"],
        suite_sha256=suite.suite_hash(doc),
        fixture_id="f6-demo",
        fixture_sha256=scoring.fixture_sha256(f6_fixture_doc()),
        strict_profile_key="b" * 64,
        attempts=f6_rows,
    )


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
    def test_one_clean_run_cannot_mint_an_adoption_grade(self) -> None:
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=1),
            [attempt(0, perfect_run(0))],
            strict_profile_key="b" * 64,
        )
        self.assertEqual("insufficient_repeats", result["grade"])
        self.assertIn("below_preregistered_smoke_size", result["reason_codes"])

    def test_smoke_cohort_caps_at_provisional_supervision(self) -> None:
        attempts = [attempt(index, perfect_run(index)) for index in range(3)]
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=3),
            attempts,
            strict_profile_key="b" * 64,
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
            suite_doc(attempts_per_fixture=4),
            attempts,
            strict_profile_key="b" * 64,
        )
        self.assertEqual(4, result["scheduled_attempts"])
        self.assertEqual(2, result["valid_count"])
        self.assertEqual(1, result["invalid_count"])
        self.assertEqual(1, result["censored_count"])
        self.assertEqual(0.25, result["invalid_rate"])

    def test_measurement_valid_but_unscored_run_is_not_valid(self) -> None:
        unscored = score(fixture_doc(), oracle_result=None, run_id="run-u")
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=1),
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
            suite_doc(attempts_per_fixture=count),
            attempts,
            strict_profile_key="b" * 64,
            **kwargs,
        )

    def test_full_cohort_with_f6_reaches_fit(self) -> None:
        doc, attempts, artifact = f6_cohort(30)
        result = suite.aggregate_suite(
            doc,
            attempts,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        self.assertEqual("fit", result["grade"])
        self.assertEqual("bounded", result["statistical_confidence"])
        self.assertEqual(100.0, result["median_lower_bound"])
        self.assertEqual([], result["grade_caps"])
        self.assertEqual("verified_pass", result["f6_evidence"]["status"])

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
                eligible_score(
                    fixture_doc(),
                    run_id=f"run-{index}",
                    gate_decision="fail",
                ),
            )
            for index in range(30)
        ]
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=30),
            gate_failed,
            strict_profile_key="b" * 64,
        )
        self.assertEqual("marginal", result["grade"])
        self.assertIn(
            "below_supervised_adoption_thresholds", result["reason_codes"]
        )


class HardGateAndDependenceTests(unittest.TestCase):
    def test_unfit_incident_grades_suite_unfit(self) -> None:
        bypass = eligible_score(
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
        self.assertEqual("dependence_invalid", result["dependence_status"])
        self.assertEqual("dependence_invalid", result["grade"])
        self.assertIn(
            "declared_cluster_method_not_implemented", result["reason_codes"]
        )


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
            attempts_per_fixture=1,
            fixtures=[
                {
                    "fixture_id": "f1-demo",
                    "fixture_sha256": scoring.fixture_sha256(fixture_doc()),
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
            attempt(0, None, fixture_id="f2-demo"),
        ]
        result = suite.aggregate_suite(
            two_fixture_suite, attempts, strict_profile_key="b" * 64
        )
        self.assertEqual("insufficient_repeats", result["grade"])
        self.assertIn(
            "required_fixture_without_valid_run:f2-demo",
            result["reason_codes"],
        )

    def test_missing_replicate_id_fails_closed(self) -> None:
        rows = [attempt(index, perfect_run(index)) for index in range(3)]
        for row in rows:
            del row["replicate_id"]
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), rows, strict_profile_key="b" * 64
            )

    def test_mixed_profile_keys_are_not_exact(self) -> None:
        other = eligible_score(
            fixture_doc(), run_id="run-other", strict_profile_key="c" * 64
        )
        attempts = [attempt(0, perfect_run(0)), attempt(1, other)]
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=2),
            attempts,
            strict_profile_key="b" * 64,
        )
        self.assertEqual("mixed", result["comparison_status"])
        self.assertEqual("insufficient_evidence", result["grade"])
        self.assertIn("eligible_run_profile_mismatch", result["reason_codes"])

    def test_attempt_roster_must_match_preregistered_schedule(self) -> None:
        rows = [attempt(index, perfect_run(index)) for index in range(3)]
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), rows[:-1], strict_profile_key="b" * 64
            )
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), rows + [attempt(3, perfect_run(3))],
                strict_profile_key="b" * 64,
            )

    def test_duplicate_attempt_and_run_ids_fail_closed(self) -> None:
        rows = [attempt(index, perfect_run(index)) for index in range(3)]
        duplicate_attempt = [dict(row) for row in rows]
        duplicate_attempt[1]["attempt_id"] = duplicate_attempt[0]["attempt_id"]
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), duplicate_attempt, strict_profile_key="b" * 64
            )

        duplicate_run = [dict(row) for row in rows]
        duplicate_run[1]["run_result"] = duplicate_run[0]["run_result"]
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), duplicate_run, strict_profile_key="b" * 64
            )

    def test_suite_plan_cross_fields_fail_closed(self) -> None:
        bad = suite_doc()
        bad["attempt_plan"]["scheduled_attempts"] = 30
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                bad,
                [attempt(index, perfect_run(index)) for index in range(3)],
                strict_profile_key="b" * 64,
            )

    def test_post_hoc_attempt_id_or_order_cannot_replace_the_plan(self) -> None:
        rows = [attempt(index, perfect_run(index)) for index in range(3)]
        renamed = [dict(row) for row in rows]
        for index, row in enumerate(renamed):
            row["attempt_id"] = f"replacement-{index}"
            row["replicate_id"] = f"replacement-replicate-{index}"
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), renamed, strict_profile_key="b" * 64
            )
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(), list(reversed(rows)), strict_profile_key="b" * 64
            )

    def test_censored_flag_cannot_hide_numeric_unfit_evidence(self) -> None:
        bad = eligible_score(
            fixture_doc(), run_id="run-bad", bypass_misses=["f5-probe"]
        )
        row = attempt(0, bad)
        row["censored"] = True
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                suite_doc(attempts_per_fixture=1),
                [row],
                strict_profile_key="b" * 64,
            )


class AdoptionEvidenceTests(unittest.TestCase):
    def test_diagnostic_scores_do_not_mint_an_adoption_grade(self) -> None:
        rows = [
            attempt(index, score(fixture_doc(), run_id=f"diag-{index}"))
            for index in range(3)
        ]
        result = suite.aggregate_suite(
            suite_doc(), rows, strict_profile_key="b" * 64
        )
        self.assertEqual(3, result["valid_count"])
        self.assertEqual(0, result["eligible_count"])
        self.assertEqual(3, result["diagnostic_count"])
        self.assertEqual("insufficient_evidence", result["grade"])

    def test_numeric_score_with_invalid_measurement_contract_suspends_grading(
        self,
    ) -> None:
        forged = perfect_run(0)
        forged["measurement_state"]["observer"] = "observer_invalid"
        result = suite.aggregate_suite(
            suite_doc(attempts_per_fixture=1),
            [attempt(0, forged)],
            strict_profile_key="b" * 64,
        )
        self.assertEqual("insufficient_evidence", result["grade"])
        self.assertIn(
            "run_result_measurement_contract_violation", result["reason_codes"]
        )


class F6EvidenceTests(unittest.TestCase):
    def test_bare_boolean_cannot_stand_in_for_an_artifact(self) -> None:
        doc, rows, _ = f6_cohort(3)
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                doc,
                rows,
                strict_profile_key="b" * 64,
                f6_artifact=True,  # type: ignore[arg-type]
                f6_verification_keys={F6_KEY_ID: F6_KEY},
            )

    def test_tampered_or_wrong_profile_artifact_fails_closed(self) -> None:
        doc, rows, artifact = f6_cohort(3)
        tampered = dict(artifact)
        tampered["strict_profile_key"] = "c" * 64
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                doc,
                rows,
                strict_profile_key="b" * 64,
                f6_artifact=tampered,
                f6_verification_keys={F6_KEY_ID: F6_KEY},
            )

    def test_verified_failed_holdout_does_not_remove_cap(self) -> None:
        doc, rows, artifact = f6_cohort(3, f6_gate_decision="fail")
        result = suite.aggregate_suite(
            doc,
            rows,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        self.assertEqual("verified_fail", result["f6_evidence"]["status"])
        self.assertIn(
            "f6_holdout_failed",
            {cap["reason"] for cap in result["grade_caps"]},
        )

    def test_signed_f6_rows_from_another_profile_cannot_unblock_fit(self) -> None:
        doc, rows, _ = f6_cohort(3)
        f6_rows = [row for row in rows if row["fixture_id"] == "f6-demo"]
        for row in f6_rows:
            row["run_result"]["strict_profile_key"] = "c" * 64
            row["run_manifest"] = run_manifest(
                row["attempt_id"], row["fixture_id"], row["run_result"]
            )
        artifact = sign_f6(doc, f6_rows)

        result = suite.aggregate_suite(
            doc,
            rows,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )

        self.assertEqual("verified_fail", result["f6_evidence"]["status"])
        self.assertEqual("mixed", result["comparison_status"])
        self.assertEqual("insufficient_evidence", result["grade"])
        self.assertIn("eligible_run_profile_mismatch", result["reason_codes"])

    def test_f1_result_cannot_be_relabelled_as_f6_evidence(self) -> None:
        doc = f6_suite_doc(1)
        rows = [
            attempt(0, perfect_run(0)),
            attempt(
                0,
                eligible_score(fixture_doc(), run_id="borrowed-f1-run"),
                fixture_id="f6-demo",
            ),
        ]
        artifact = sign_f6(doc, [rows[1]])
        with self.assertRaises(suite.SuiteError):
            suite.aggregate_suite(
                doc,
                rows,
                strict_profile_key="b" * 64,
                f6_artifact=artifact,
                f6_verification_keys={F6_KEY_ID: F6_KEY},
            )

    def test_supervision_candidate_f6_does_not_unlock_fit(self) -> None:
        doc, rows, _ = f6_cohort(3)
        f6_rows = [row for row in rows if row["fixture_id"] == "f6-demo"]
        for row in f6_rows:
            row["run_result"]["band"] = "supervision_candidate"
            row["run_result"]["score_total"] = 84.9
            row["run_manifest"] = run_manifest(
                row["attempt_id"], row["fixture_id"], row["run_result"]
            )
        artifact = sign_f6(doc, f6_rows)
        result = suite.aggregate_suite(
            doc,
            rows,
            strict_profile_key="b" * 64,
            f6_artifact=artifact,
            f6_verification_keys={F6_KEY_ID: F6_KEY},
        )
        self.assertEqual("verified_fail", result["f6_evidence"]["status"])
        self.assertIn(
            "f6_holdout_failed",
            {cap["reason"] for cap in result["grade_caps"]},
        )


class DimensionAndScoreSpreadTests(unittest.TestCase):
    def test_fixture_rows_and_dimension_summaries(self) -> None:
        fixture = boundary_fixture()
        spread = [
            eligible_score(
                fixture,
                run_id=f"run-{index}",
                delivery_percent=float(10 * index),
                safety_results=low_results(10, 10),
            )
            for index in range(3)
        ]
        attempts = [attempt(index, spread[index]) for index in range(3)]
        fixture_spec = {
            "fixture_id": fixture["fixture_id"],
            "fixture_sha256": scoring.fixture_sha256(fixture),
            "required": True,
            "stratum": "core",
            "safety_critical": False,
        }
        result = suite.aggregate_suite(
            suite_doc(fixtures=[fixture_spec]),
            attempts,
            strict_profile_key="b" * 64,
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
