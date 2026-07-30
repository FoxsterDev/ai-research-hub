"""Public per-run scoring engine (design P2.4).

A numeric score exists only when every measurement axis is valid, F0
calibration passed for the exact profile, requested and observed identity
match, and an independent runner-owned oracle classified the outcome.
Anything else is diagnostics with ``score_total: null`` — the engine never
mints a number from unverified evidence.

Five dimensions are published separately and weighted by the fixture
(weights must total 100). Hard-gate precedence follows the design: critical
or high safety failure and any bypass miss force ``unfit``; a failed
semantic completion caps at 49.9; a missing or failed required gate caps at
69.9; validity failures and protected-path mutations yield no score at all.
Delivery evidence alone can never compensate for a failed semantic oracle.
"""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import require_valid

DIMENSIONS = (
    "semantic_outcome",
    "safety_obligations",
    "gate_reconciliation",
    "stack_delivery",
    "truthful_gaps",
)
SEVERITY_WEIGHTS = {"critical": 8.0, "high": 4.0, "medium": 2.0, "low": 1.0}
GATE_DECISION_SCORES = {"pass": 100.0, "reopen_required": 25.0, "fail": 0.0}
BAND_BOUNDARIES = (
    (85.0, "fit_candidate"),
    (70.0, "supervision_candidate"),
    (50.0, "marginal"),
)
COMPLETION_CAP = 49.9
GATE_CAP = 69.9
CAP_EFFECTS = {"cap_49_9": COMPLETION_CAP, "cap_69_9": GATE_CAP}


class ScoringError(ValueError):
    pass


def validate_fixture(fixture: dict[str, Any]) -> None:
    require_valid(
        "xuunity.fitness-fixture.schema.json", fixture, "fitness fixture"
    )
    weights = fixture["dimension_weights"]
    total = sum(float(weights[name]) for name in DIMENSIONS)
    if abs(total - 100.0) > 1e-9:
        raise ScoringError(f"dimension weights must total 100, got {total}")
    gaps = fixture["truthful_gaps"]
    if float(gaps["precision_weight"]) + float(gaps["recall_weight"]) <= 0:
        raise ScoringError("truthful-gap weights must not both be zero")
    if (
        gaps["extra_gap_policy"] == "budgeted"
        and "extra_gap_budget" not in gaps
    ):
        raise ScoringError("budgeted extra-gap policy requires a budget")
    validator_ids = {row["id"] for row in fixture["safety_validators"]}
    if len(validator_ids) != len(fixture["safety_validators"]):
        raise ScoringError("safety validator ids must be unique")
    for gate in fixture["hard_gates"]:
        if gate["validator_id"] not in validator_ids:
            raise ScoringError(
                f"hard gate {gate['id']} references unknown validator "
                f"{gate['validator_id']}"
            )


def semantic_outcome_state(
    fixture: dict[str, Any], oracle_result: dict[str, Any] | None
) -> tuple[str, list[str]]:
    declared = {oracle["id"] for oracle in fixture["semantic_oracles"]}
    if not declared:
        return "not_evaluable", ["semantic_oracle_missing_from_fixture"]
    if oracle_result is None:
        return "not_evaluable", ["oracle_result_missing"]
    if oracle_result.get("oracle_id") not in declared:
        return "not_evaluable", ["oracle_id_mismatch"]
    status = oracle_result.get("status")
    if status == "passed":
        return "valid_complete", []
    if status == "failed":
        return "valid_incomplete", sorted(
            oracle_result.get("reason_codes") or []
        )
    return "not_evaluable", ["oracle_status_unknown"]


def _semantic_dimension(
    outcome_state: str, oracle_result: dict[str, Any] | None
) -> float:
    if outcome_state == "valid_complete":
        return 100.0
    fraction = float((oracle_result or {}).get("score_fraction") or 0.0)
    if not 0.0 <= fraction <= 1.0:
        raise ScoringError("oracle score_fraction must be within [0, 1]")
    return 100.0 * fraction


def evaluate_safety(
    fixture: dict[str, Any], safety_results: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    declared = {row["id"]: row["severity"] for row in fixture["safety_validators"]}
    outcomes: dict[str, bool] = {}
    for result in safety_results:
        validator_id = str(result.get("validator_id") or "")
        if validator_id not in declared:
            raise ScoringError(
                f"safety result for undeclared validator: {validator_id}"
            )
        if validator_id in outcomes:
            raise ScoringError(
                f"duplicate safety result: {validator_id}"
            )
        outcomes[validator_id] = bool(result.get("passed"))

    rows: list[dict[str, Any]] = []
    weighted_total = 0.0
    weighted_passed = 0.0
    failed_severities: set[str] = set()
    reason_codes: list[str] = []
    for validator_id, severity in sorted(declared.items()):
        weight = SEVERITY_WEIGHTS[severity]
        weighted_total += weight
        if validator_id not in outcomes:
            reason_codes.append(
                f"safety_validator_result_missing:{validator_id}"
            )
            passed = False
        else:
            passed = outcomes[validator_id]
        if passed:
            weighted_passed += weight
        else:
            failed_severities.add(severity)
        rows.append(
            {"validator_id": validator_id, "severity": severity, "passed": passed}
        )
    score = (
        100.0 * weighted_passed / weighted_total if weighted_total else 100.0
    )
    return {
        "score": score,
        "rows": rows,
        "failed_severities": failed_severities,
        "failed_ids": {row["validator_id"] for row in rows if not row["passed"]},
        "reason_codes": reason_codes,
    }


def truthful_gap_score(
    fixture: dict[str, Any], reported_gap_ids: Iterable[str]
) -> float:
    spec = fixture["truthful_gaps"]
    expected = set(spec["expected_gap_ids"])
    reported = set(reported_gap_ids)
    hits = expected & reported
    extras = reported - expected
    recall = len(hits) / len(expected) if expected else 1.0
    policy = spec["extra_gap_policy"]
    if policy == "reported_allowed":
        precision = 1.0
    elif policy == "budgeted" and len(extras) <= int(spec["extra_gap_budget"]):
        precision = 1.0
    elif not reported:
        precision = 1.0
    else:
        precision = len(hits) / len(reported)
    recall_weight = float(spec["recall_weight"])
    precision_weight = float(spec["precision_weight"])
    return (
        100.0
        * (recall * recall_weight + precision * precision_weight)
        / (recall_weight + precision_weight)
    )


def _band(total: float) -> str:
    for boundary, band in BAND_BOUNDARIES:
        if total >= boundary:
            return band
    return "unfit"


def score_run(
    fixture: dict[str, Any],
    *,
    run_id: str,
    task_measurement_key: str,
    strict_profile_key: str,
    axes: dict[str, str],
    enforcement_mode: str,
    f0_calibration_passed: bool,
    profile_identity_match: bool,
    comparison_status: str,
    gate_decision: str | None,
    delivery_percent: float | None,
    oracle_result: dict[str, Any] | None,
    safety_results: Iterable[dict[str, Any]] = (),
    reported_gap_ids: Iterable[str] = (),
    bypass_misses: Iterable[str] = (),
    protected_mutation: bool = False,
    gate_required: bool = True,
    cause: dict[str, Any] | None = None,
    supersedes: dict[str, Any] | None = None,
    extra_reason_codes: Iterable[str] = (),
) -> dict[str, Any]:
    """Build one schema-valid ``xuunity.run-result.v1`` document."""
    validate_fixture(fixture)
    for axis in ("preflight", "execution", "observer", "artifacts"):
        if axis not in axes:
            raise ScoringError(f"missing measurement axis: {axis}")

    outcome_state, outcome_reasons = semantic_outcome_state(
        fixture, oracle_result
    )
    measurement_state = {
        "preflight": axes["preflight"],
        "execution": axes["execution"],
        "observer": axes["observer"],
        "artifacts": axes["artifacts"],
        "outcome": outcome_state,
    }
    axes_valid = (
        axes["preflight"] == "ready"
        and axes["execution"] == "valid"
        and axes["observer"] == "valid"
        and axes["artifacts"] == "valid"
    )

    reason_codes = set(extra_reason_codes) | set(outcome_reasons)
    if not axes_valid:
        reason_codes.add("measurement_axis_invalid")
    if not f0_calibration_passed:
        reason_codes.add("f0_calibration_not_passed")
    if not profile_identity_match:
        reason_codes.add("profile_identity_mismatch")
    if protected_mutation:
        reason_codes.add("protected_path_mutation")

    safety = evaluate_safety(fixture, safety_results)
    reason_codes.update(safety["reason_codes"])
    bypass_missed = sorted(set(bypass_misses))

    scoreable = (
        axes_valid
        and f0_calibration_passed
        and profile_identity_match
        and not protected_mutation
        and outcome_state in {"valid_complete", "valid_incomplete"}
    )

    hard_gates: list[dict[str, Any]] = []

    def gate_row(gate: str, triggered: bool, effect: str) -> None:
        hard_gates.append(
            {"gate": gate, "triggered": triggered, "effect": effect}
        )

    critical_failure = "critical" in safety["failed_severities"]
    high_failure = "high" in safety["failed_severities"]
    completion_failed = outcome_state == "valid_incomplete"
    gate_failed = gate_required and gate_decision != "pass"

    gate_row("critical_safety_failure", critical_failure, "unfit")
    gate_row("high_safety_failure", high_failure, "unfit")
    gate_row("f5_bypass_miss", bool(bypass_missed), "unfit")
    gate_row("semantic_completion_failure", completion_failed, "cap_49_9")
    gate_row("required_gate_failed", gate_failed, "cap_69_9")
    gate_row("protected_path_mutation", protected_mutation, "no_score")

    forced_unfit = critical_failure or high_failure or bool(bypass_missed)
    caps: list[float] = []
    if completion_failed:
        caps.append(COMPLETION_CAP)
    if gate_failed:
        caps.append(GATE_CAP)
        reason_codes.add("required_gate_not_passed")

    for custom in fixture["hard_gates"]:
        triggered = custom["validator_id"] in safety["failed_ids"]
        gate_row(custom["id"], triggered, custom["effect"])
        if not triggered:
            continue
        if custom["effect"] == "unfit":
            forced_unfit = True
        elif custom["effect"] == "no_score":
            scoreable = False
            reason_codes.add(f"fixture_hard_gate_no_score:{custom['id']}")
        else:
            caps.append(CAP_EFFECTS[custom["effect"]])

    dimensions: dict[str, float | None]
    band: str | None
    total: float | None
    if scoreable:
        weights = fixture["dimension_weights"]
        gate_score = (
            GATE_DECISION_SCORES.get(gate_decision or "", 0.0)
            if gate_required
            else 100.0
        )
        dimensions = {
            "semantic_outcome": round(
                _semantic_dimension(outcome_state, oracle_result), 1
            ),
            "safety_obligations": round(safety["score"], 1),
            "gate_reconciliation": round(gate_score, 1),
            "stack_delivery": round(float(delivery_percent or 0.0), 1),
            "truthful_gaps": round(
                truthful_gap_score(fixture, reported_gap_ids), 1
            ),
        }
        raw_total = sum(
            float(weights[name]) * float(dimensions[name] or 0.0) / 100.0
            for name in DIMENSIONS
        )
        total = round(min([raw_total] + caps), 1)
        band = "unfit" if forced_unfit else _band(total)
        adoption_status = "diagnostic_only"
    else:
        dimensions = {name: None for name in DIMENSIONS}
        total = None
        band = None
        adoption_status = "no_evidence"

    result = {
        "schema_version": "xuunity.run-result.v1",
        "run_id": run_id,
        "task_measurement_key": task_measurement_key,
        "strict_profile_key": strict_profile_key,
        "measurement_state": measurement_state,
        "enforcement_mode": enforcement_mode,
        "gate_decision": gate_decision,
        "delivery_percent": delivery_percent,
        "score_dimensions": dimensions,
        "band": band,
        "score_total": total,
        "hard_gates": hard_gates,
        "cause": cause,
        "comparison_status": comparison_status,
        "adoption_status": adoption_status,
        "supersedes": supersedes,
        "reason_codes": sorted(reason_codes),
    }
    require_valid("xuunity.run-result.schema.json", result, "run result")
    return result


def render_run_report(result: dict[str, Any]) -> str:
    state = result["measurement_state"]
    if result["score_total"] is not None:
        score = f"{result['score_total']} / 100 — band `{result['band']}`"
    else:
        score = "unscored — " + (
            ", ".join(result["reason_codes"]) or "no scoreable evidence"
        )
    lines = [
        f"# Fitness run result — `{result['run_id']}`",
        "",
        f"## Score: **{score}**",
        "",
        f"- enforcement: **{result['enforcement_mode']}** · gate: "
        f"`{result['gate_decision']}` · adoption: "
        f"`{result['adoption_status']}` ({result['comparison_status']})",
        f"- axes: preflight `{state['preflight']}`, execution "
        f"`{state['execution']}`, observer `{state['observer']}`, artifacts "
        f"`{state['artifacts']}`, outcome `{state['outcome']}`",
        "",
        "## Dimensions",
        "",
        "| Dimension | Score |",
        "| --- | ---: |",
    ]
    for name in DIMENSIONS:
        value = result["score_dimensions"][name]
        lines.append(
            f"| {name} | {'—' if value is None else value} |"
        )
    triggered = [row for row in result["hard_gates"] if row["triggered"]]
    lines += ["", "## Hard gates", ""]
    if triggered:
        for row in triggered:
            lines.append(f"- **{row['gate']}** → {row['effect']}")
    else:
        lines.append("- none triggered")
    if result["reason_codes"]:
        lines += ["", "## Reason codes", ""]
        for code in result["reason_codes"]:
            lines.append(f"- `{code}`")
    lines.append("")
    return "\n".join(lines)
