"""Preregistered experiment decision evaluation (design P2.4).

Evaluates one single-treatment experiment against its immutable manifest:
target-metric decision, non-regression budgets, family-alpha and F6
exposure ledgers. Unknown metric ids fail closed. Acceptance never applies
anything — ``apply_authorization`` starts at ``not_requested`` and belongs
to the manifest's declared authority, outside this engine.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import f6
from .contracts import fractional_document_hash, require_valid
from .suite import UNGRADED, suite_result_sha256

METRICS = frozenset(
    {"score_median", "median_lower_bound", "worst_valid", "invalid_rate"}
)


class ExperimentError(ValueError):
    pass


def validate_manifest(manifest: dict[str, Any]) -> None:
    require_valid(
        "xuunity.experiment-manifest.schema.json", manifest,
        "experiment manifest",
    )
    metric_ids = {manifest["target_metric"]["metric_id"]} | {
        budget["metric_id"] for budget in manifest["non_regression_budgets"]
    }
    unknown = sorted(metric_ids - METRICS)
    if unknown:
        raise ExperimentError(f"unknown metric ids: {unknown}")
    declared_hash = manifest.get("manifest_hash")
    if declared_hash is not None and declared_hash != manifest_hash(manifest):
        raise ExperimentError("manifest_hash does not match preregistration")
    consumed = manifest["f6_exposure_budget"]["consumed_artifact_hashes"]
    if len(consumed) != len(set(consumed)):
        raise ExperimentError("F6 consumed artifact hashes must be unique")


def manifest_hash(manifest: dict[str, Any]) -> str:
    return fractional_document_hash(manifest, "manifest_hash")


def _metric_value(suite_result: dict[str, Any], metric_id: str) -> float | None:
    if metric_id not in METRICS:
        raise ExperimentError(f"unknown metric id: {metric_id}")
    value = suite_result[metric_id]
    return None if value is None else float(value)


def _degradation(
    direction: str, control: float, treatment: float
) -> float:
    if direction == "higher_is_better":
        return control - treatment
    return treatment - control


def _validate_suite_arm(
    arm: str,
    expected: dict[str, Any],
    result: dict[str, Any],
    *,
    attempts_per_cell: int,
) -> None:
    actual = {
        "suite_id": result["suite_id"],
        "suite_hash": result["suite_hash"],
        "strict_profile_key": result["strict_profile_key"],
    }
    if actual != expected:
        raise ExperimentError(f"{arm} suite identity does not match manifest")
    if result["scheduled_attempts"] != attempts_per_cell * len(result["fixtures"]):
        raise ExperimentError(f"{arm} suite schedule does not match manifest")
    if any(
        row["scheduled"] != attempts_per_cell for row in result["fixtures"]
    ):
        raise ExperimentError(f"{arm} fixture schedule does not match manifest")


def _verified_f6_hashes(
    suite_results: tuple[dict[str, Any], dict[str, Any]],
    *,
    artifacts: Mapping[str, dict[str, Any]],
    verification_keys: Mapping[str, bytes],
) -> set[str]:
    verified_hashes: set[str] = set()
    for result in suite_results:
        evidence = result["f6_evidence"]
        status = evidence["status"]
        if status not in {"verified_pass", "verified_fail"}:
            if (
                evidence["artifact_hash"] is not None
                or evidence["evidence_ref"] is not None
            ):
                raise ExperimentError(
                    "unverified F6 summary carries artifact identity"
                )
            continue
        required = (
            "artifact_hash",
            "evidence_ref",
            "holdout_ref",
            "fixture_id",
            "issuer_key_id",
        )
        if not all(
            isinstance(evidence[field], str) and evidence[field]
            for field in required
        ):
            raise ExperimentError("verified F6 summary has incomplete identity")
        artifact_hash = str(evidence["artifact_hash"])
        artifact = artifacts.get(artifact_hash)
        if artifact is None:
            raise ExperimentError("verified F6 artifact was not supplied")
        try:
            f6.verify_artifact_summary(
                artifact,
                verification_keys=verification_keys,
                expected_artifact_hash=artifact_hash,
                expected_evidence_ref=str(evidence["evidence_ref"]),
                expected_holdout_ref=str(evidence["holdout_ref"]),
                expected_issuer_key_id=str(evidence["issuer_key_id"]),
                expected_suite_id=result["suite_id"],
                expected_suite_sha256=result["suite_hash"],
                expected_fixture_id=str(evidence["fixture_id"]),
                expected_strict_profile_key=result["strict_profile_key"],
            )
        except f6.F6EvidenceError as error:
            raise ExperimentError(str(error)) from error
        verified_hashes.add(artifact_hash)
    return verified_hashes


def evaluate_experiment(
    manifest: dict[str, Any],
    control_suite_result: dict[str, Any],
    treatment_suite_result: dict[str, Any],
    *,
    control_suite_ref: str,
    treatment_suite_ref: str,
    alpha_charge: float,
    alpha_spent_before: float,
    f6_artifacts: Mapping[str, dict[str, Any]] | None = None,
    f6_verification_keys: Mapping[str, bytes] | None = None,
    candidate_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one schema-valid ``xuunity.experiment-result.v2`` document."""
    validate_manifest(manifest)
    require_valid(
        "xuunity.suite-result.schema.json", control_suite_result,
        "control suite result",
    )
    require_valid(
        "xuunity.suite-result.schema.json", treatment_suite_result,
        "treatment suite result",
    )
    if alpha_charge <= 0:
        raise ExperimentError("alpha_charge must be positive")
    attempts_per_cell = int(manifest["attempt_schedule"]["attempts_per_cell"])
    _validate_suite_arm(
        "control",
        manifest["suite_arms"]["control"],
        control_suite_result,
        attempts_per_cell=attempts_per_cell,
    )
    _validate_suite_arm(
        "treatment",
        manifest["suite_arms"]["treatment"],
        treatment_suite_result,
        attempts_per_cell=attempts_per_cell,
    )
    control_result_hash = suite_result_sha256(control_suite_result)
    treatment_result_hash = suite_result_sha256(treatment_suite_result)
    if control_suite_ref == treatment_suite_ref:
        raise ExperimentError("control and treatment suite refs must differ")
    if (
        control_suite_result["cohort_hash"]
        == treatment_suite_result["cohort_hash"]
    ):
        raise ExperimentError("control and treatment cohorts must differ")
    if control_result_hash == treatment_result_hash:
        raise ExperimentError("control and treatment suite results must differ")
    scheduled_runs = (
        control_suite_result["scheduled_attempts"]
        + treatment_suite_result["scheduled_attempts"]
    )
    if scheduled_runs > int(manifest["cost_limit"]["max_model_runs"]):
        raise ExperimentError(
            "preregistered suite schedule exceeds model-run budget"
        )
    reason_codes: set[str] = set()
    target = manifest["target_metric"]
    metric_id = target["metric_id"]
    direction = target["direction"]
    threshold = float(target["acceptance_threshold"])
    control_value = _metric_value(control_suite_result, metric_id)
    treatment_value = _metric_value(treatment_suite_result, metric_id)
    confidence = float(
        treatment_suite_result["decision_rule"]["confidence"]
    )

    target_decision: bool | None
    if treatment_value is None or (
        target["comparison"] == "treatment_vs_control_delta"
        and control_value is None
    ):
        target_decision = None
        reason_codes.add("target_metric_unavailable")
    elif target["comparison"] == "treatment_bound_vs_threshold":
        if direction == "higher_is_better":
            target_decision = treatment_value >= threshold
        else:
            target_decision = treatment_value <= threshold
    else:
        delta = treatment_value - float(control_value)
        if direction == "higher_is_better":
            target_decision = delta >= threshold
        else:
            target_decision = delta <= threshold

    non_regression: list[dict[str, Any]] = []
    regressions_ok: bool | None = True
    for budget in manifest["non_regression_budgets"]:
        budget_control = _metric_value(
            control_suite_result, budget["metric_id"]
        )
        budget_treatment = _metric_value(
            treatment_suite_result, budget["metric_id"]
        )
        if budget_control is None or budget_treatment is None:
            observed = None
            respected = False
            regressions_ok = None if regressions_ok is not False else False
            reason_codes.add(
                f"non_regression_metric_unavailable:{budget['metric_id']}"
            )
        else:
            observed = _degradation(
                budget["direction"], budget_control, budget_treatment
            )
            respected = observed <= float(budget["max_degradation"])
            if not respected:
                regressions_ok = False
                reason_codes.add(
                    f"non_regression_budget_exceeded:{budget['metric_id']}"
                )
        non_regression.append(
            {
                "metric_id": budget["metric_id"],
                "budget": float(budget["max_degradation"]),
                "observed_delta": observed,
                "respected": respected,
            }
        )

    family = manifest["family"]
    alpha_spent_after = alpha_spent_before + alpha_charge
    alpha_exhausted = alpha_spent_after > float(family["family_alpha"]) + 1e-12
    if alpha_exhausted:
        reason_codes.add("family_alpha_exhausted")

    consumed_hashes = set(
        manifest["f6_exposure_budget"]["consumed_artifact_hashes"]
    )
    f6_artifact_hashes = _verified_f6_hashes(
        (control_suite_result, treatment_suite_result),
        artifacts=f6_artifacts or {},
        verification_keys=f6_verification_keys or {},
    )
    replayed = consumed_hashes & f6_artifact_hashes
    if replayed:
        reason_codes.add("f6_artifact_replay")
    after_hashes = consumed_hashes | f6_artifact_hashes
    f6_before = len(consumed_hashes)
    f6_after = len(after_hashes)
    f6_budget = int(manifest["f6_exposure_budget"]["max_exposures"])
    f6_exceeded = f6_after > f6_budget
    if f6_exceeded:
        reason_codes.add("f6_exposure_budget_exceeded")

    unbounded = any(
        result["statistical_confidence"] != "bounded"
        for result in (control_suite_result, treatment_suite_result)
    )
    if unbounded:
        reason_codes.add("statistical_confidence_insufficient")

    ungraded = any(
        result["grade"] in UNGRADED
        for result in (control_suite_result, treatment_suite_result)
    )
    if ungraded:
        reason_codes.add("suite_not_adoption_graded")
    treatment_not_adoptable = treatment_suite_result["grade"] in {
        "marginal",
        "unfit",
    }
    if treatment_not_adoptable:
        reason_codes.add(
            f"treatment_suite_{treatment_suite_result['grade']}"
        )

    if (
        target_decision is None
        or regressions_ok is None
        or alpha_exhausted
        or f6_exceeded
        or bool(replayed)
        or unbounded
        or ungraded
    ):
        status = "inconclusive"
    elif treatment_not_adoptable:
        status = "rejected"
    elif target_decision and regressions_ok:
        status = "accepted"
    else:
        status = "rejected"

    result = {
        "schema_version": "xuunity.experiment-result.v2",
        "experiment_id": manifest["experiment_id"],
        "manifest_hash": manifest.get("manifest_hash")
        or manifest_hash(manifest),
        "control_suite": {
            "suite_result_ref": control_suite_ref,
            "suite_result_sha256": control_result_hash,
        },
        "treatment_suite": {
            "suite_result_ref": treatment_suite_ref,
            "suite_result_sha256": treatment_result_hash,
        },
        "statistics": {
            "metric_id": metric_id,
            "control_value": control_value,
            "treatment_value": treatment_value,
            "control_bound": control_value,
            "treatment_bound": treatment_value,
            "decision_rule_id": treatment_suite_result["decision_rule"][
                "method_id"
            ],
            "implementation_sha256": treatment_suite_result["decision_rule"][
                "implementation_sha256"
            ],
            "confidence": confidence,
        },
        "non_regression": non_regression,
        "status": status,
        "family_ledger": {
            "experiment_family_id": family["experiment_family_id"],
            "family_alpha": float(family["family_alpha"]),
            "alpha_spent_before": alpha_spent_before,
            "alpha_spent_after": alpha_spent_after,
            "f6_exposures_before": f6_before,
            "f6_exposures_after": f6_after,
            "f6_artifact_hashes_before": sorted(consumed_hashes),
            "f6_artifact_hashes_after": sorted(after_hashes),
            "f6_budget": f6_budget,
        },
        "candidate_patch": candidate_patch
        or {"ref": None, "sha256": None},
        "apply_authorization": {
            "state": "not_requested",
            "authorized_by": None,
        },
        "reason_codes": sorted(reason_codes),
    }
    require_valid(
        "xuunity.experiment-result.schema.json", result, "experiment result"
    )
    return result
