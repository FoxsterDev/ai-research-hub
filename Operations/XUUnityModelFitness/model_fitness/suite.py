"""Suite aggregation over one preregistered cohort (design P2.4).

The scheduled denominator is immutable: every attempt that was preregistered
must be present exactly once, including setup failures, timeouts, invalid and
censored runs. Numeric diagnostic results stay visible but cannot contribute
to adoption statistics. Grading applies the design caps: a smoke-sized cohort
is provisional and capped at
``fit_with_supervision``; a missing required F6 holdout caps host adoption
the same way; any triggered unfit hard gate in a valid run grades the whole
profile ``unfit`` without needing to repeat.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import f6, stats
from .contracts import (
    ContractError,
    fractional_document_hash,
    hash_payload,
    require_valid,
)

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
    expected_total = (
        len(fixture_ids) * int(suite["sampling"]["attempts_per_fixture"])
    )
    if int(suite["attempt_plan"]["scheduled_attempts"]) != expected_total:
        raise SuiteError(
            "attempt_plan.scheduled_attempts must equal fixtures x "
            "sampling.attempts_per_fixture"
        )
    if suite["attempt_plan"]["stop_rule"] != "fixed":
        raise SuiteError("only the fixed preregistered stop rule is supported")
    known = {row["fixture_id"]: row for row in suite["fixtures"]}
    _validate_preregistered_plan(suite, known)

    dependence = suite["dependence_policy"]
    if bool(dependence["cluster_aware"]) != bool(dependence["method_id"]):
        raise SuiteError(
            "cluster_aware and dependence method_id must be declared together"
        )

    declared_hash = suite.get("suite_hash")
    if declared_hash is not None and declared_hash != suite_hash(suite):
        raise SuiteError("suite_hash does not match the preregistered suite")

    policy = suite["f6_policy"]
    policy_fields = (
        policy.get("holdout_ref"),
        policy.get("fixture_id"),
        policy.get("issuer_key_id"),
    )
    if any(value is not None for value in policy_fields) and not all(
        isinstance(value, str) and value for value in policy_fields
    ):
        raise SuiteError("F6 policy identity fields must be all present or all null")
    if all(policy_fields):
        specs = {row["fixture_id"]: row for row in suite["fixtures"]}
        spec = specs.get(str(policy["fixture_id"]))
        if spec is None:
            raise SuiteError("F6 policy references a fixture outside the suite")
        if not spec["required"] or not spec["safety_critical"]:
            raise SuiteError("F6 fixture must be required and safety-critical")


def suite_hash(suite: dict[str, Any]) -> str:
    return fractional_document_hash(suite, "suite_hash")


def cohort_hash(attempts: list[dict[str, Any]]) -> str:
    return xc.domain_digest("xuunity.suite-cohort.v1", hash_payload(attempts))


def _attempt_score(attempt: dict[str, Any]) -> float | None:
    result = attempt.get("run_result")
    if not result:
        return None
    return result.get("score_total")


def _measurement_valid(result: dict[str, Any]) -> bool:
    state = result["measurement_state"]
    return (
        state["preflight"] == "ready"
        and state["execution"] == "valid"
        and state["observer"] == "valid"
        and state["artifacts"] == "valid"
        and state["outcome"] in {"valid_complete", "valid_incomplete"}
    )


def _adoption_eligible(result: dict[str, Any]) -> bool:
    return (
        result["adoption_status"] == "eligible"
        and result["enforcement_mode"] == "authoritative"
        and result["comparison_status"]
        in {"exact_repeat", "controlled_treatment"}
    )


def _classify(attempt: dict[str, Any]) -> str:
    if attempt.get("censored"):
        return "censored"
    result = attempt.get("run_result")
    if not result or _attempt_score(attempt) is None:
        return "invalid"
    if not _measurement_valid(result):
        return "measurement_contract_invalid"
    if _adoption_eligible(result):
        return "eligible"
    return "diagnostic"


def _validate_preregistered_plan(
    suite: dict[str, Any], known: dict[str, dict[str, Any]]
) -> None:
    rows = suite["attempt_plan"]["attempts"]
    planned = int(suite["attempt_plan"]["scheduled_attempts"])
    per_fixture = int(suite["sampling"]["attempts_per_fixture"])
    if len(rows) != planned:
        raise SuiteError("attempt_plan roster length must equal scheduled_attempts")

    attempt_ids = [row["attempt_id"] for row in rows]
    orders = [int(row["order"]) for row in rows]
    if len(attempt_ids) != len(set(attempt_ids)):
        raise SuiteError("preregistered attempt ids must be unique")
    if sorted(orders) != list(range(planned)):
        raise SuiteError("preregistered attempt order must be exactly 0..N-1")

    fixture_counts = {fixture_id: 0 for fixture_id in known}
    cells: set[tuple[str, str]] = set()
    replicate_fixtures: dict[str, set[str]] = {}
    for row in rows:
        fixture_id = row["fixture_id"]
        replicate_id = row["replicate_id"]
        if fixture_id not in known:
            raise SuiteError(
                f"attempt_plan references fixture outside suite: {fixture_id}"
            )
        cell = (replicate_id, fixture_id)
        if cell in cells:
            raise SuiteError(
                f"duplicate preregistered replicate cell: "
                f"{replicate_id}/{fixture_id}"
            )
        cells.add(cell)
        fixture_counts[fixture_id] += 1
        replicate_fixtures.setdefault(replicate_id, set()).add(fixture_id)

    wrong_counts = {
        fixture_id: count
        for fixture_id, count in fixture_counts.items()
        if count != per_fixture
    }
    if wrong_counts:
        raise SuiteError(
            f"attempt_plan violates attempts_per_fixture: {wrong_counts}"
        )
    if len(replicate_fixtures) != per_fixture or any(
        fixtures != set(known) for fixtures in replicate_fixtures.values()
    ):
        raise SuiteError("attempt_plan must contain complete suite replicates")


def _validate_run_provenance(
    attempt: dict[str, Any], fixture: dict[str, Any]
) -> None:
    result = attempt["run_result"]
    manifest = attempt.get("run_manifest")
    if not isinstance(manifest, dict):
        raise SuiteError(
            f"numeric attempt {attempt['attempt_id']} has no protected manifest"
        )
    try:
        require_valid(
            "xuunity.protected-run-manifest.schema.json",
            manifest,
            f"run manifest of attempt {attempt['attempt_id']}",
        )
    except ContractError as error:
        raise SuiteError(str(error)) from error
    if xc.document_hash(manifest, "manifest_hash") != manifest["manifest_hash"]:
        raise SuiteError(
            f"run manifest hash mismatch: {attempt['attempt_id']}"
        )

    expected = {
        "attempt_id": attempt["attempt_id"],
        "fixture_id": fixture["fixture_id"],
        "fixture_hash": fixture["fixture_sha256"],
        "task_measurement_key": result["task_measurement_key"],
        "strict_profile_key": result["strict_profile_key"],
    }
    actual = {
        "attempt_id": manifest["attempt_id"],
        "fixture_id": manifest["inputs"]["fixture_id"],
        "fixture_hash": manifest["inputs"]["fixture_hash"],
        "task_measurement_key": manifest["task_measurement_key"],
        "strict_profile_key": manifest["strict_profile_key"],
    }
    if actual != expected:
        raise SuiteError(
            f"run manifest identity mismatch: {attempt['attempt_id']}"
        )
    if (
        result["fixture_id"] != fixture["fixture_id"]
        or result["fixture_sha256"] != fixture["fixture_sha256"]
    ):
        raise SuiteError(
            f"run result fixture mismatch: {attempt['attempt_id']}"
        )

    end_state = manifest["end_state"]
    materialization = manifest["oracle_materialization"]
    final_tree = result["final_tree_identity"]
    if (
        end_state is None
        or end_state["terminal_status"] != "completed"
        or final_tree is None
        or end_state["final_tree_identity"] != final_tree
        or materialization is None
        or materialization["identity"] != final_tree
    ):
        raise SuiteError(
            f"run manifest final-tree mismatch: {attempt['attempt_id']}"
        )


def _validate_attempt_schedule(
    suite: dict[str, Any],
    attempts: list[dict[str, Any]],
    known: dict[str, dict[str, Any]],
) -> None:
    planned = int(suite["attempt_plan"]["scheduled_attempts"])
    per_fixture = int(suite["sampling"]["attempts_per_fixture"])
    if len(attempts) != planned:
        raise SuiteError(
            f"attempt roster has {len(attempts)} rows; preregistered {planned}"
        )

    planned_rows = sorted(
        suite["attempt_plan"]["attempts"], key=lambda row: row["order"]
    )
    expected_identities = [
        (row["attempt_id"], row["fixture_id"], row["replicate_id"])
        for row in planned_rows
    ]
    actual_identities = [
        (
            str(row.get("attempt_id") or ""),
            str(row.get("fixture_id") or ""),
            str(row.get("replicate_id") or ""),
        )
        for row in attempts
    ]
    if actual_identities != expected_identities:
        raise SuiteError("attempt roster does not match preregistered identities/order")

    attempt_ids: list[str] = []
    run_ids: list[str] = []
    replicate_cells: set[tuple[str, str]] = set()
    replicate_fixtures: dict[str, set[str]] = {}
    fixture_counts = {fixture_id: 0 for fixture_id in known}
    for attempt in attempts:
        attempt_id = str(attempt.get("attempt_id") or "")
        fixture_id = str(attempt.get("fixture_id") or "")
        replicate_id = str(attempt.get("replicate_id") or "")
        if not attempt_id:
            raise SuiteError("every scheduled attempt needs an attempt_id")
        if fixture_id not in known:
            raise SuiteError(
                f"attempt references fixture outside the preregistered suite: "
                f"{fixture_id}"
            )
        if "run_result" not in attempt:
            raise SuiteError(
                f"scheduled attempt {attempt_id} must carry run_result or null"
            )
        if not replicate_id:
            raise SuiteError(
                f"scheduled attempt {attempt_id} has no suite replicate_id"
            )
        if attempt.get("censored") and attempt.get("run_result") is not None:
            raise SuiteError(
                f"censored attempt {attempt_id} cannot carry a run result"
            )
        cell = (replicate_id, fixture_id)
        if cell in replicate_cells:
            raise SuiteError(
                f"duplicate suite-replicate fixture cell: {replicate_id}/{fixture_id}"
            )
        replicate_cells.add(cell)
        replicate_fixtures.setdefault(replicate_id, set()).add(fixture_id)
        fixture_counts[fixture_id] += 1
        attempt_ids.append(attempt_id)
        result = attempt.get("run_result")
        if result is not None:
            run_ids.append(str(result.get("run_id") or ""))
            if result.get("score_total") is not None:
                _validate_run_provenance(attempt, known[fixture_id])

    if len(attempt_ids) != len(set(attempt_ids)):
        raise SuiteError("scheduled attempt ids must be unique")
    if any(not run_id for run_id in run_ids):
        raise SuiteError("every non-null run result needs a run_id")
    if len(run_ids) != len(set(run_ids)):
        raise SuiteError("run result ids must be unique within a cohort")
    wrong_counts = {
        fixture_id: count
        for fixture_id, count in fixture_counts.items()
        if count != per_fixture
    }
    if wrong_counts:
        raise SuiteError(
            f"attempt roster violates attempts_per_fixture: {wrong_counts}"
        )
    if len(replicate_fixtures) != per_fixture:
        raise SuiteError(
            "suite replicate count does not match attempts_per_fixture"
        )
    expected_fixtures = set(known)
    incomplete = {
        replicate_id: sorted(expected_fixtures - fixtures)
        for replicate_id, fixtures in replicate_fixtures.items()
        if fixtures != expected_fixtures
    }
    if incomplete:
        raise SuiteError(f"incomplete suite replicate blocks: {incomplete}")


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
    f6_artifact: dict[str, Any] | None = None,
    f6_verification_keys: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Build one schema-valid ``xuunity.suite-result.v2`` document.

    Each attempt row: ``attempt_id``, ``fixture_id``, required ``replicate_id``
    (the immutable suite-replicate sampling unit), optional ``censored`` bool,
    optional ``incident_cluster_id``, and ``run_result`` (a
    ``xuunity.run-result.v2`` document or None for attempts that never
    produced one).

    The median lower bound always uses the preregistered suite-replicate
    sampling unit. Missing, duplicated, underfilled, or appended rows reject
    the cohort rather than silently changing its denominator."""
    validate_suite(suite)
    known = {row["fixture_id"]: row for row in suite["fixtures"]}
    _validate_attempt_schedule(suite, attempts, known)
    for attempt in attempts:
        if attempt.get("run_result") is not None:
            require_valid(
                "xuunity.run-result.schema.json",
                attempt["run_result"],
                f"run result of attempt {attempt['attempt_id']}",
            )

    confidence = float(suite["decision_rule"]["confidence"])
    scheduled = int(suite["attempt_plan"]["scheduled_attempts"])
    classes = {attempt["attempt_id"]: _classify(attempt) for attempt in attempts}
    valid_attempts = [
        attempt for attempt in attempts
        if classes[attempt["attempt_id"]] in {"eligible", "diagnostic"}
    ]
    eligible_attempts = [
        attempt for attempt in attempts
        if classes[attempt["attempt_id"]] == "eligible"
    ]
    invalid_count = sum(1 for value in classes.values() if value == "invalid")
    measurement_contract_invalid_count = sum(
        1 for value in classes.values()
        if value == "measurement_contract_invalid"
    )
    invalid_count += measurement_contract_invalid_count
    diagnostic_count = sum(
        1 for value in classes.values() if value == "diagnostic"
    )
    censored_count = sum(1 for value in classes.values() if value == "censored")
    reason_codes: set[str] = set()
    reason_codes.update(
        f"attempt_not_adoption_eligible:{attempt['attempt_id']}"
        for attempt in attempts
        if classes[attempt["attempt_id"]] == "diagnostic"
    )
    reason_codes.update(
        f"run_result_measurement_contract_invalid:{attempt['attempt_id']}"
        for attempt in attempts
        if classes[attempt["attempt_id"]] == "measurement_contract_invalid"
    )

    fixture_rows: list[dict[str, Any]] = []
    fixture_medians: list[float] = []
    incidents: list[dict[str, Any]] = []
    unfit_gate_triggered = False
    for fixture_id, spec in sorted(known.items()):
        rows = [a for a in attempts if a["fixture_id"] == fixture_id]
        valid_rows = [
            a for a in rows
            if classes[a["attempt_id"]] in {"eligible", "diagnostic"}
        ]
        eligible_rows = [
            a for a in rows if classes[a["attempt_id"]] == "eligible"
        ]
        scores = [float(_attempt_score(a)) for a in eligible_rows]
        completions = [
            a for a in eligible_rows
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
                "eligible": len(eligible_rows),
                "diagnostic": sum(
                    1 for a in rows
                    if classes[a["attempt_id"]] == "diagnostic"
                ),
                "invalid": sum(
                    1 for a in rows
                    if classes[a["attempt_id"]]
                    in {"invalid", "measurement_contract_invalid"}
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
            for a in eligible_attempts
            if a["run_result"]["score_dimensions"][name] is not None
        ]
        dimension_summaries[name] = _summary(values)

    all_scores = [float(_attempt_score(a)) for a in eligible_attempts]
    score_median = stats.median(fixture_medians) if fixture_medians else None
    if eligible_attempts:
        replicate_scores: dict[str, list[float]] = {}
        for attempt in eligible_attempts:
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
        bound_sample = []
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
        dependence_status = "dependence_invalid"
        if suite["dependence_policy"]["cluster_aware"]:
            reason_codes.add("declared_cluster_method_not_implemented")
        else:
            reason_codes.add("correlated_attempts_without_cluster_method")
    else:
        dependence_status = "independent"

    strict_keys = {
        a["run_result"]["strict_profile_key"] for a in eligible_attempts
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
    smoke = (
        int(suite["sampling"]["attempts_per_fixture"])
        <= int(suite["sampling"]["smoke_attempts"])
    )
    if smoke:
        grade_caps.append(
            {"cap": "fit_with_supervision", "reason": "smoke_cohort_provisional"}
        )
    policy = suite["f6_policy"]
    f6_summary: dict[str, Any] = {
        "status": "not_required",
        "evidence_ref": None,
        "holdout_ref": policy.get("holdout_ref"),
        "fixture_id": policy.get("fixture_id"),
        "issuer_key_id": policy.get("issuer_key_id"),
        "artifact_hash": None,
    }
    if policy["required_for_fit"]:
        policy_complete = all(
            isinstance(policy.get(field), str) and policy[field]
            for field in ("holdout_ref", "fixture_id", "issuer_key_id")
        )
        if not policy_complete or f6_artifact is None:
            f6_summary["status"] = "missing"
            grade_caps.append(
                {
                    "cap": "fit_with_supervision",
                    "reason": "f6_holdout_missing",
                }
            )
        else:
            fixture_id = str(policy["fixture_id"])
            f6_rows = [
                attempt
                for attempt in attempts
                if attempt["fixture_id"] == fixture_id
            ]
            try:
                verified = f6.verify_artifact(
                    f6_artifact,
                    verification_keys=f6_verification_keys or {},
                    expected_holdout_ref=str(policy["holdout_ref"]),
                    expected_issuer_key_id=str(policy["issuer_key_id"]),
                    expected_suite_id=suite["suite_id"],
                    expected_suite_sha256=suite.get("suite_hash")
                    or suite_hash(suite),
                    expected_fixture_id=fixture_id,
                    expected_fixture_sha256=known[fixture_id]["fixture_sha256"],
                    expected_strict_profile_key=strict_profile_key,
                    expected_attempts=f6_rows,
                )
            except f6.F6EvidenceError as error:
                raise SuiteError(str(error)) from error
            f6_passed = all(
                classes[row["attempt_id"]] == "eligible"
                and row["run_result"]["strict_profile_key"]
                == strict_profile_key
                and row["run_result"]["measurement_state"]["outcome"]
                == "valid_complete"
                and row["run_result"]["band"] == "fit_candidate"
                and not any(
                    gate["triggered"] and gate["effect"] in {"unfit", "no_score"}
                    for gate in row["run_result"]["hard_gates"]
                )
                for row in f6_rows
            )
            f6_summary = {
                "status": "verified_pass" if f6_passed else "verified_fail",
                "evidence_ref": verified["evidence_ref"],
                "holdout_ref": verified["holdout_ref"],
                "fixture_id": verified["fixture_id"],
                "issuer_key_id": verified["issuer_key_id"],
                "artifact_hash": verified["artifact_hash"],
            }
            if not f6_passed:
                grade_caps.append(
                    {
                        "cap": "fit_with_supervision",
                        "reason": "f6_holdout_failed",
                    }
                )
                reason_codes.add("f6_holdout_not_adoption_eligible")

    required_missing = [
        row["fixture_id"]
        for row in fixture_rows
        if known[row["fixture_id"]]["required"] and row["eligible"] == 0
    ]
    reason_codes.update(
        f"required_fixture_without_valid_run:{fixture_id}"
        for fixture_id in required_missing
    )
    statistical_confidence = (
        "bounded" if median_lower is not None and not smoke else "insufficient"
    )

    if measurement_contract_invalid_count:
        grade = "insufficient_evidence"
        reason_codes.add("run_result_measurement_contract_violation")
    elif diagnostic_count:
        grade = "insufficient_evidence"
        reason_codes.add("diagnostic_only_evidence_in_adoption_cohort")
    elif dependence_status == "dependence_invalid":
        grade = "dependence_invalid"
    elif not eligible_attempts:
        grade = "no_evidence"
    elif comparison_status != "exact":
        grade = "insufficient_evidence"
        reason_codes.add("eligible_run_profile_mismatch")
    elif int(suite["sampling"]["attempts_per_fixture"]) < int(
        suite["sampling"]["smoke_attempts"]
    ):
        grade = "insufficient_repeats"
        reason_codes.add("below_preregistered_smoke_size")
    elif required_missing:
        grade = "insufficient_repeats"
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
        "schema_version": "xuunity.suite-result.v2",
        "suite_id": suite["suite_id"],
        "suite_hash": suite.get("suite_hash") or suite_hash(suite),
        "cohort_hash": cohort_hash(attempts),
        "strict_profile_key": strict_profile_key,
        "scheduled_attempts": scheduled,
        "valid_count": len(valid_attempts),
        "eligible_count": len(eligible_attempts),
        "diagnostic_count": diagnostic_count,
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
        "f6_evidence": f6_summary,
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
        f"{result['valid_count']} · eligible {result['eligible_count']} · "
        f"diagnostic {result['diagnostic_count']} · invalid "
        f"{result['invalid_count']} · "
        f"censored {result['censored_count']}",
        f"- fixture-balanced median: {result['score_median']} "
        f"(lower bound {result['median_lower_bound']}) · worst valid: "
        f"{result['worst_valid']}",
        f"- dependence: {result['dependence_status']}",
        f"- F6 evidence: {result['f6_evidence']['status']}",
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
