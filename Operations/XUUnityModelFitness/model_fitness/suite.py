"""Suite aggregation over one preregistered cohort (design P2.4).

The scheduled denominator is immutable: every attempt that was scheduled —
including setup failures, timeouts, invalid and censored runs — stays
counted. Valid means "produced a numeric score"; a measurement-valid but
unscored run is diagnostic and never enters medians. Grading applies the
design caps: a smoke-sized cohort is provisional and capped at
``fit_with_supervision``; a missing required F6 holdout caps host adoption
the same way; any triggered unfit hard gate in a valid run grades the whole
profile ``unfit`` without needing to repeat.
"""

from __future__ import annotations

from typing import Any

from . import stats
from .contracts import fractional_document_hash, hash_payload, require_valid

import xuunity_canonical as xc

GRADE_ORDER = {"fit": 4, "fit_with_supervision": 3, "marginal": 2, "unfit": 1}
UNGRADED = {
    "insufficient_repeats",
    "insufficient_evidence",
    "dependence_invalid",
    "no_evidence",
}


class SuiteError(ValueError):
    pass


def validate_suite(suite: dict[str, Any]) -> None:
    require_valid("xuunity.fitness-suite.schema.json", suite, "fitness suite")
    fixture_ids = [row["fixture_id"] for row in suite["fixtures"]]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise SuiteError("suite fixture ids must be unique")


def suite_hash(suite: dict[str, Any]) -> str:
    return fractional_document_hash(suite, "suite_hash")


def _attempt_score(attempt: dict[str, Any]) -> float | None:
    result = attempt.get("run_result")
    if not result:
        return None
    return result.get("score_total")


def _classify(attempt: dict[str, Any]) -> str:
    if attempt.get("censored"):
        return "censored"
    if _attempt_score(attempt) is not None:
        return "valid"
    return "invalid"


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"median": None, "range": None}
    return {
        "median": stats.median(values),
        "range": [min(values), max(values)],
    }


def aggregate_suite(
    suite: dict[str, Any],
    attempts: list[dict[str, Any]],
    *,
    strict_profile_key: str,
    f6_included: bool = False,
) -> dict[str, Any]:
    """Build one schema-valid ``xuunity.suite-result.v1`` document.

    Each attempt row: ``attempt_id``, ``fixture_id``, optional ``censored``
    bool, optional ``incident_cluster_id``, optional ``replicate_id`` (the
    immutable suite-replicate sampling unit), and ``run_result`` (a
    ``xuunity.run-result.v1`` document or None for attempts that never
    produced one).

    The median lower bound uses the preregistered sampling unit: when every
    attempt carries a ``replicate_id``, the bound is taken over
    fixture-balanced per-replicate scores; otherwise it falls back to the
    pooled valid scores and records ``median_bound_pooled_fallback``."""
    validate_suite(suite)
    known = {row["fixture_id"]: row for row in suite["fixtures"]}
    for attempt in attempts:
        if attempt["fixture_id"] not in known:
            raise SuiteError(
                f"attempt references fixture outside the preregistered "
                f"suite: {attempt['fixture_id']}"
            )
        if attempt.get("run_result") is not None:
            require_valid(
                "xuunity.run-result.schema.json",
                attempt["run_result"],
                f"run result of attempt {attempt['attempt_id']}",
            )

    confidence = float(suite["decision_rule"]["confidence"])
    scheduled = len(attempts)
    classes = {attempt["attempt_id"]: _classify(attempt) for attempt in attempts}
    valid_attempts = [
        attempt for attempt in attempts
        if classes[attempt["attempt_id"]] == "valid"
    ]
    invalid_count = sum(1 for value in classes.values() if value == "invalid")
    censored_count = sum(1 for value in classes.values() if value == "censored")
    reason_codes: set[str] = set()

    fixture_rows: list[dict[str, Any]] = []
    fixture_medians: list[float] = []
    incidents: list[dict[str, Any]] = []
    unfit_gate_triggered = False
    for fixture_id, spec in sorted(known.items()):
        rows = [a for a in attempts if a["fixture_id"] == fixture_id]
        valid_rows = [
            a for a in rows if classes[a["attempt_id"]] == "valid"
        ]
        scores = [float(_attempt_score(a)) for a in valid_rows]
        completions = [
            a for a in valid_rows
            if (a["run_result"]["measurement_state"]["outcome"]
                == "valid_complete")
        ]
        incident_count = 0
        for attempt in valid_rows:
            for gate in attempt["run_result"]["hard_gates"]:
                if not gate["triggered"]:
                    continue
                incident_count += 1
                incidents.append(
                    {
                        "run_id": attempt["run_result"]["run_id"],
                        "fixture_id": fixture_id,
                        "gate": gate["gate"],
                        "effect": gate["effect"],
                    }
                )
                if gate["effect"] == "unfit":
                    unfit_gate_triggered = True
        summary = _summary(scores)
        if summary["median"] is not None:
            fixture_medians.append(float(summary["median"]))
        fixture_rows.append(
            {
                "fixture_id": fixture_id,
                "stratum": spec["stratum"],
                "safety_critical": spec["safety_critical"],
                "scheduled": len(rows),
                "valid": len(valid_rows),
                "invalid": sum(
                    1 for a in rows if classes[a["attempt_id"]] == "invalid"
                ),
                "censored": sum(
                    1 for a in rows if classes[a["attempt_id"]] == "censored"
                ),
                "median": summary["median"],
                "range": summary["range"],
                "worst_valid": min(scores) if scores else None,
                "completion_rate": (
                    len(completions) / len(valid_rows) if valid_rows else None
                ),
                "completion_lower_bound": (
                    stats.clopper_pearson_lower(
                        len(completions), len(valid_rows), confidence
                    )
                    if valid_rows
                    else None
                ),
                "hard_gate_incident_count": incident_count,
            }
        )

    dimension_summaries: dict[str, dict[str, Any]] = {}
    for name in (
        "semantic_outcome",
        "safety_obligations",
        "gate_reconciliation",
        "stack_delivery",
        "truthful_gaps",
    ):
        values = [
            float(a["run_result"]["score_dimensions"][name])
            for a in valid_attempts
            if a["run_result"]["score_dimensions"][name] is not None
        ]
        dimension_summaries[name] = _summary(values)

    all_scores = [float(_attempt_score(a)) for a in valid_attempts]
    score_median = stats.median(fixture_medians) if fixture_medians else None
    if valid_attempts and all(
        attempt.get("replicate_id") for attempt in attempts
    ):
        replicate_scores: dict[str, list[float]] = {}
        for attempt in valid_attempts:
            replicate_scores.setdefault(
                str(attempt["replicate_id"]), []
            ).append(float(_attempt_score(attempt)))
        bound_sample = [
            value
            for scores in replicate_scores.values()
            for value in [stats.median(scores)]
            if value is not None
        ]
    else:
        bound_sample = all_scores
        if valid_attempts:
            reason_codes.add("median_bound_pooled_fallback")
    median_lower = (
        stats.median_lower_bound(bound_sample, confidence)
        if bound_sample
        else None
    )
    worst_valid = min(all_scores) if all_scores else None
    invalid_rate = invalid_count / scheduled if scheduled else None

    clusters: dict[str, list[str]] = {}
    for attempt in attempts:
        cluster_id = attempt.get("incident_cluster_id")
        if cluster_id:
            clusters.setdefault(str(cluster_id), []).append(
                str(attempt["attempt_id"])
            )
    incident_clusters = [
        {"incident_cluster_id": cluster_id, "run_ids": sorted(members)}
        for cluster_id, members in sorted(clusters.items())
        if len(members) >= 2
    ]
    if incident_clusters:
        if suite["dependence_policy"]["cluster_aware"]:
            dependence_status = "clustered_valid"
        else:
            dependence_status = "dependence_invalid"
            reason_codes.add("correlated_attempts_without_cluster_method")
    else:
        dependence_status = "independent"

    strict_keys = {
        a["run_result"]["strict_profile_key"] for a in valid_attempts
    }
    if not strict_keys:
        comparison_status = "non_controlled"
    elif strict_keys == {strict_profile_key}:
        comparison_status = "exact"
    elif strict_profile_key in strict_keys:
        comparison_status = "mixed"
    else:
        comparison_status = "non_controlled"

    grade_caps: list[dict[str, str]] = []
    smoke = all(
        row["scheduled"] <= int(suite["sampling"]["smoke_attempts"])
        for row in fixture_rows
    )
    if smoke:
        grade_caps.append(
            {"cap": "fit_with_supervision", "reason": "smoke_cohort_provisional"}
        )
    if suite["f6_policy"]["required_for_fit"] and not f6_included:
        grade_caps.append(
            {"cap": "fit_with_supervision", "reason": "f6_holdout_missing"}
        )

    required_missing = [
        row["fixture_id"]
        for row in fixture_rows
        if known[row["fixture_id"]]["required"] and row["valid"] == 0
    ]
    statistical_confidence = (
        "bounded" if median_lower is not None and not smoke else "insufficient"
    )

    if dependence_status == "dependence_invalid":
        grade = "dependence_invalid"
    elif not valid_attempts:
        grade = "no_evidence"
    elif required_missing:
        grade = "insufficient_repeats"
        reason_codes.update(
            f"required_fixture_without_valid_run:{fixture_id}"
            for fixture_id in required_missing
        )
    elif unfit_gate_triggered:
        grade = "unfit"
        reason_codes.add("hard_gate_unfit_incident")
    else:
        grade = _threshold_grade(
            suite["adoption_thresholds"],
            fixture_rows=fixture_rows,
            median_value=score_median if smoke else median_lower,
            worst_valid=worst_valid,
            invalid_count=invalid_count,
            scheduled=scheduled,
            confidence=confidence,
            use_bounds=not smoke,
            reason_codes=reason_codes,
        )
        for cap in grade_caps:
            if GRADE_ORDER.get(grade, 0) > GRADE_ORDER.get(cap["cap"], 0):
                grade = cap["cap"]

    result = {
        "schema_version": "xuunity.suite-result.v1",
        "suite_id": suite["suite_id"],
        "suite_hash": suite.get("suite_hash") or suite_hash(suite),
        "strict_profile_key": strict_profile_key,
        "scheduled_attempts": scheduled,
        "valid_count": len(valid_attempts),
        "invalid_count": invalid_count,
        "censored_count": censored_count,
        "invalid_rate": invalid_rate,
        "fixtures": fixture_rows,
        "dimensions": dimension_summaries,
        "score_median": score_median,
        "median_lower_bound": median_lower,
        "worst_valid": worst_valid,
        "hard_gate_incidents": sorted(
            incidents,
            key=lambda row: (row["fixture_id"], row["run_id"], row["gate"]),
        ),
        "incident_clusters": incident_clusters,
        "dependence_status": dependence_status,
        "grade": grade,
        "grade_caps": grade_caps,
        "statistical_confidence": statistical_confidence,
        "decision_rule": {
            "method_id": suite["decision_rule"]["method_id"],
            "implementation_sha256": suite["decision_rule"][
                "implementation_sha256"
            ],
            "confidence": confidence,
        },
        "comparison_status": comparison_status,
        "reason_codes": sorted(reason_codes),
    }
    require_valid("xuunity.suite-result.schema.json", result, "suite result")
    return result


def _threshold_grade(
    thresholds: dict[str, Any],
    *,
    fixture_rows: list[dict[str, Any]],
    median_value: float | None,
    worst_valid: float | None,
    invalid_count: int,
    scheduled: int,
    confidence: float,
    use_bounds: bool,
    reason_codes: set[str],
) -> str:
    """Bounded thresholds for full cohorts; a smoke cohort is graded on
    point estimates, stays provisional, and is capped by its smoke cap."""
    if use_bounds:
        invalid_metric = (
            stats.clopper_pearson_upper(invalid_count, scheduled, confidence)
            if scheduled
            else None
        )
        completion_key = "completion_lower_bound"
    else:
        invalid_metric = invalid_count / scheduled if scheduled else None
        completion_key = "completion_rate"
    completion_values = [
        row[completion_key] for row in fixture_rows if row["valid"] > 0
    ]
    completion_floor = min(completion_values) if completion_values else None

    def meets(spec: dict[str, Any]) -> bool:
        checks = (
            (
                completion_floor is not None
                and completion_floor >= float(spec["completion_lower_bound_min"])
            ),
            (
                median_value is not None
                and median_value >= float(spec["median_lower_bound_min"])
            ),
            (
                worst_valid is not None
                and worst_valid >= float(spec["worst_valid_min"])
            ),
            (
                invalid_metric is not None
                and invalid_metric <= float(spec["invalid_rate_upper_bound_max"])
            ),
        )
        return all(checks)

    if meets(thresholds["fit"]):
        return "fit"
    if meets(thresholds["fit_with_supervision"]):
        return "fit_with_supervision"
    reason_codes.add("below_supervised_adoption_thresholds")
    return "marginal"


def suite_result_sha256(result: dict[str, Any]) -> str:
    return xc.sha256_bytes(xc.canonical_bytes(hash_payload(result)))


def render_suite_report(result: dict[str, Any]) -> str:
    lines = [
        f"# Suite result — `{result['suite_id']}`",
        "",
        f"## Grade: **{result['grade']}** "
        f"(confidence: {result['statistical_confidence']}, "
        f"comparison: {result['comparison_status']})",
        "",
        f"- scheduled {result['scheduled_attempts']} · valid "
        f"{result['valid_count']} · invalid {result['invalid_count']} · "
        f"censored {result['censored_count']}",
        f"- fixture-balanced median: {result['score_median']} "
        f"(lower bound {result['median_lower_bound']}) · worst valid: "
        f"{result['worst_valid']}",
        f"- dependence: {result['dependence_status']}",
    ]
    for cap in result["grade_caps"]:
        lines.append(f"- cap `{cap['cap']}`: {cap['reason']}")
    lines += [
        "",
        "| Fixture | Valid/Sched | Median | Worst | Completion LB | Gates |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result["fixtures"]:
        completion = row["completion_lower_bound"]
        lines.append(
            f"| {row['fixture_id']} | {row['valid']}/{row['scheduled']} | "
            f"{row['median'] if row['median'] is not None else '—'} | "
            f"{row['worst_valid'] if row['worst_valid'] is not None else '—'} | "
            f"{round(completion, 3) if completion is not None else '—'} | "
            f"{row['hard_gate_incident_count']} |"
        )
    if result["hard_gate_incidents"]:
        lines += ["", "## Hard-gate incidents", ""]
        for incident in result["hard_gate_incidents"]:
            lines.append(
                f"- `{incident['run_id']}` ({incident['fixture_id']}): "
                f"{incident['gate']} → {incident['effect']}"
            )
    if result["reason_codes"]:
        lines += ["", "## Reason codes", ""]
        for code in result["reason_codes"]:
            lines.append(f"- `{code}`")
    lines.append("")
    return "\n".join(lines)
