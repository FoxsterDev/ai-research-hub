"""Preregistered experiment decision evaluation (design P2.4).

Evaluates one single-treatment experiment against its immutable manifest:
target-metric decision, non-regression budgets, family-alpha and F6
exposure ledgers. Unknown metric ids fail closed. Acceptance never applies
anything — ``apply_authorization`` starts at ``not_requested`` and belongs
to the manifest's declared authority, outside this engine.
"""

from __future__ import annotations

from typing import Any

from .contracts import fractional_document_hash, require_valid
from .suite import suite_result_sha256

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


def evaluate_experiment(
    manifest: dict[str, Any],
    control_suite_result: dict[str, Any],
    treatment_suite_result: dict[str, Any],
    *,
    control_suite_ref: str,
    treatment_suite_ref: str,
    alpha_charge: float,
    alpha_spent_before: float,
    f6_exposures_used: int = 0,
    candidate_patch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one schema-valid ``xuunity.experiment-result.v1`` document."""
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
    if f6_exposures_used < 0:
        raise ExperimentError("f6_exposures_used must be non-negative")

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

    f6_before = int(manifest["f6_exposure_budget"]["consumed_before"])
    f6_after = f6_before + f6_exposures_used
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

    if (
        target_decision is None
        or regressions_ok is None
        or alpha_exhausted
        or f6_exceeded
        or unbounded
    ):
        status = "inconclusive"
    elif target_decision and regressions_ok:
        status = "accepted"
    else:
        status = "rejected"

    result = {
        "schema_version": "xuunity.experiment-result.v1",
        "experiment_id": manifest["experiment_id"],
        "manifest_hash": manifest.get("manifest_hash")
        or manifest_hash(manifest),
        "control_suite": {
            "suite_result_ref": control_suite_ref,
            "suite_result_sha256": suite_result_sha256(control_suite_result),
        },
        "treatment_suite": {
            "suite_result_ref": treatment_suite_ref,
            "suite_result_sha256": suite_result_sha256(
                treatment_suite_result
            ),
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
