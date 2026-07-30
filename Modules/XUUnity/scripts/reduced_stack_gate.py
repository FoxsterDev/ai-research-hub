#!/usr/bin/env python3
"""Mechanical reduced-stack gate: derive, check, and reconcile.

Loose-file invocations are always ``audited`` and never mint authoritative
authorization — an authoritative result exists only behind the parent-owned
broker (design P2). Claims never earn delivery credit: the gate consumes only
independently collected observation-ledger events and trusted context
manifests. Semantic rules are composed, not copied: the routing rules stay in
``routing_gate_check.py`` and are invoked through a validated wrapper.

Exit codes: 0 pass; 1 gate fail or reopen required; 2 usage/schema error;
3 measurement invalid or observer unsupported; 4 not runnable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract_validator  # noqa: E402
import observation_contract as oc  # noqa: E402
import reduced_stack_resolver as resolver  # noqa: E402
import routing_gate_check  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_INVALID = 3
EXIT_NOT_RUNNABLE = 4

GATE_RESULT_SCHEMA_VERSION = "xuunity.stack-gate-result.v1"

SEMANTIC_CHECKERS = {
    "routing_gate_check": lambda payload: [
        {"rule": violation.rule, "message": violation.message}
        for violation in routing_gate_check.check_contract(payload)
    ],
}

FAR_FUTURE_SEQ = 10**12


class GateUsageError(ValueError):
    pass


def _load_json(path: Path, schema_name: str | None, label: str) -> dict[str, Any]:
    try:
        document = xc.load_strict(Path(path))
    except (OSError, xc.CanonicalizationError) as error:
        raise GateUsageError(f"cannot read {label}: {error}") from error
    if schema_name:
        errors = contract_validator.validate_against(schema_name, document)
        if errors:
            raise GateUsageError(f"{label} schema errors: {errors[:5]}")
    return document


def _verify_attestation(path: Path | None) -> tuple[str | None, list[str]]:
    if path is None:
        return None, ["audited_no_session_attestation"]
    attestation = _load_json(
        path, "xuunity.session-attestation.schema.json", "session attestation"
    )
    computed = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    if computed != attestation["attestation_hash"]:
        raise GateUsageError("session attestation hash mismatch")
    return attestation["attestation_id"], []


def _event_seq(event: dict[str, Any]) -> int | None:
    if event.get("started_seq") is not None:
        return int(event["started_seq"])
    if event.get("completed_seq") is not None:
        return int(event["completed_seq"])
    return None


def _mutation_cutoff(
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str, list[dict[str, Any]], list[dict[str, Any]]]:
    mutations = [
        event
        for event in events
        if event.get("kind") == "mutation" and event.get("success")
    ]
    observable = [
        event for event in mutations if event.get("started_seq") is not None
    ]
    first = min(
        observable, key=lambda event: int(event["started_seq"]), default=None
    )
    cutoff_seq = int(first["started_seq"]) if first else FAR_FUTURE_SEQ

    ambiguous = [
        event
        for event in events
        if event.get("parser_result") == "ambiguous"
        or event.get("kind") == "ambiguous_command"
    ]
    unsupported = [
        event
        for event in events
        if event.get("parser_result") == "unsupported"
        or event.get("kind") == "unsupported_command"
    ]
    boundary_ambiguous = any(
        (seq := _event_seq(event)) is not None and seq < cutoff_seq
        for event in ambiguous
    ) or any(event.get("started_seq") is None for event in mutations)

    cutoff = None
    if first:
        cutoff = {
            "started_seq": int(first["started_seq"]),
            "completed_seq": first.get("completed_seq"),
            "event_id": first["event_id"],
            "mechanism": first.get("evidence_source"),
            "target": (first.get("targets") or [None])[0],
            "actor": first.get("actor", "unknown"),
        }
    confidence = (
        "ambiguous_prior_commands"
        if boundary_ambiguous
        else "unambiguous"
        if first
        else "no_mutation_observed"
    )
    return cutoff, confidence, ambiguous, unsupported


def _flagged_row(event: dict[str, Any], cutoff_seq: int) -> dict[str, Any]:
    seq = _event_seq(event)
    return {
        "event_id": event["event_id"],
        "started_seq": event.get("started_seq"),
        "completed_seq": event.get("completed_seq"),
        "programs": list(event.get("targets") or []),
        "command_sha256": event.get("command_sha256"),
        "required_paths_mentioned": list(event.get("targets") or []),
        "before_mutation_cutoff": seq is not None and seq < cutoff_seq,
    }


def _merged_intervals(
    intervals: list[list[int]],
) -> list[tuple[int, int]]:
    ordered = sorted(
        (int(start), int(end))
        for start, end in intervals
        if int(start) > 0 and int(end) >= int(start)
    )
    merged: list[tuple[int, int]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def resolve_artifact_state(
    artifact: dict[str, Any],
    ledger: dict[str, Any],
    cutoff_seq: int,
) -> oc.ArtifactResolution:
    path = artifact["path"]
    direct_states: list[str] = []
    unsupported_present = False
    runtime_unverified = False
    case_alias = False
    intervals: list[list[int]] = []

    for event in ledger.get("events") or []:
        targets = event.get("targets") or []
        if path not in targets:
            continue
        if event.get("actor") == "subagent":
            continue
        kind = event.get("kind")
        parser_result = event.get("parser_result")
        completed = event.get("completed_seq")
        if parser_result in {"unsupported", "ambiguous"} or kind in {
            "unsupported_command",
            "ambiguous_command",
        }:
            unsupported_present = True
            continue
        if kind != "read":
            continue
        if completed is None or int(completed) >= cutoff_seq:
            continue
        if not event.get("success"):
            direct_states.append("failed_read")
            continue
        observed = event.get("observed_sha256")
        if observed and observed == artifact["sha256"]:
            direct_states.append("proven_delivered")
            continue
        if event.get("line_intervals"):
            intervals.extend(event["line_intervals"])
        direct_states.append("partial_read")

    expected_lines = int(artifact.get("lines") or 0)
    if expected_lines > 0 and intervals:
        merged = _merged_intervals(intervals)
        if (
            merged
            and merged[0][0] <= 1
            and merged[-1][1] >= expected_lines
            and all(
                merged[index][1] + 1 >= merged[index + 1][0]
                for index in range(len(merged) - 1)
            )
        ):
            direct_states.append("proven_delivered")

    for entry in ledger.get("context_manifest") or []:
        if entry.get("path") != path:
            continue
        case_alias = bool(entry.get("case_alias"))
        if entry.get("trust") == "attested" and entry.get("sha256") == (
            artifact["sha256"]
        ):
            direct_states.append("trusted_runtime_delivered")
        elif entry.get("trust") == "unverified":
            runtime_unverified = True

    return oc.resolve_artifact_state(
        direct_states,
        unsupported_present=unsupported_present,
        runtime_unverified_present=runtime_unverified,
        case_alias=case_alias,
    )


def evaluate_groups(
    plan: dict[str, Any],
    ledger: dict[str, Any],
    cutoff_seq: int,
    phases: set[str],
) -> tuple[list[dict[str, Any]], list[oc.ArtifactResolution]]:
    artifacts = {
        artifact["path"]: artifact for artifact in plan["required_artifacts"]
    }
    resolutions: dict[str, oc.ArtifactResolution] = {}
    rows: list[dict[str, Any]] = []
    for group in plan["requirement_groups"]:
        if group["phase"] not in phases:
            continue
        member_rows = []
        for path in group["member_paths"]:
            if path not in resolutions:
                resolutions[path] = resolve_artifact_state(
                    artifacts[path], ledger, cutoff_seq
                )
            resolution = resolutions[path]
            member = {"path": path, "state": resolution.state}
            if resolution.case_alias:
                member["case_alias"] = True
            member_rows.append(member)
        satisfied_paths = {
            path
            for path in group["member_paths"]
            if resolutions[path].satisfied
        }
        policy = oc.GroupPolicy(
            group_id=group["group_id"],
            mode=group["mode"],
            weight=group["weight"],
            members=tuple(group["member_paths"])
            if group["mode"] in {"all_of", "any_of"}
            else (),
            min_count=group["min_count"] or 0,
            matched_paths=tuple(group["member_paths"])
            if group["mode"] == "at_least"
            else (),
        )
        gate_satisfied, fraction = oc.group_satisfaction(
            policy, satisfied_paths
        )
        rows.append(
            {
                "group_id": group["group_id"],
                "mode": group["mode"],
                "weight": group["weight"],
                "min_count": group["min_count"],
                "gate_satisfied": gate_satisfied,
                "leaf_fraction": round(fraction, 4),
                "members": member_rows,
            }
        )
    return rows, list(resolutions.values())


def run_semantic_checks(
    plan: dict[str, Any],
    manifest_path: Path | None,
    checker_dir: Path,
) -> list[dict[str, Any]]:
    checks = plan.get("semantic_checks") or []
    if not checks:
        return []
    manifest_inputs: dict[str, dict[str, Any]] = {}
    if manifest_path is not None:
        manifest = _load_json(manifest_path, None, "semantic input manifest")
        for entry in manifest.get("inputs") or []:
            manifest_inputs[str(entry.get("checker_id"))] = entry

    results: list[dict[str, Any]] = []
    for check in checks:
        checker_id = check["checker_id"]
        row = {
            "checker_id": checker_id,
            "checker_sha256": check.get("checker_sha256"),
            "input_sha256": check.get("input_sha256"),
            "status": "not_run",
            "reason_codes": [],
        }
        results.append(row)
        checker = SEMANTIC_CHECKERS.get(checker_id)
        checker_path = checker_dir / f"{checker_id}.py"
        if checker is None or not checker_path.is_file():
            row["status"] = "invalid_input"
            row["reason_codes"] = ["checker_unavailable"]
            continue
        actual_checker_sha = xc.sha256_file(checker_path)
        if check.get("checker_sha256") and actual_checker_sha != check[
            "checker_sha256"
        ]:
            row["status"] = "invalid_input"
            row["reason_codes"] = ["checker_implementation_changed"]
            continue
        entry = manifest_inputs.get(checker_id)
        if entry is None or not entry.get("ref"):
            if check.get("empty_input_policy") == "skip":
                row["status"] = "not_run"
                row["reason_codes"] = ["input_missing_skipped"]
                continue
            row["status"] = "invalid_input"
            row["reason_codes"] = ["input_missing"]
            continue
        try:
            raw = Path(entry["ref"]).read_bytes()
        except OSError:
            row["status"] = "invalid_input"
            row["reason_codes"] = ["input_unreadable"]
            continue
        actual_sha = xc.sha256_bytes(raw)
        row["input_sha256"] = actual_sha
        if check.get("input_sha256") and actual_sha != check["input_sha256"]:
            row["status"] = "invalid_input"
            row["reason_codes"] = ["input_swapped_after_derivation"]
            continue
        try:
            payload = xc.strict_parse(raw)
        except xc.CanonicalizationError:
            row["status"] = "invalid_input"
            row["reason_codes"] = ["input_unparseable"]
            continue
        if not isinstance(payload, dict) or not payload:
            row["status"] = "invalid_input"
            row["reason_codes"] = ["input_empty"]
            continue
        missing_fields = [
            name
            for name in check.get("required_fields") or []
            if name not in payload or payload[name] in ("", None, [])
        ]
        if missing_fields:
            row["status"] = "invalid_input"
            row["reason_codes"] = [
                f"required_field_missing:{name}" for name in missing_fields
            ]
            continue
        violations = checker(payload)
        if violations:
            row["status"] = "fail"
            row["reason_codes"] = sorted(
                violation["rule"] for violation in violations
            )
        else:
            row["status"] = "pass"
    return results


def _decide(
    plan: dict[str, Any],
    group_rows: list[dict[str, Any]],
    resolutions: list[oc.ArtifactResolution],
    semantic_rows: list[dict[str, Any]],
    confidence: str,
    profile_identity: dict[str, Any],
    post_diff_additions: list[dict[str, Any]],
    reason_codes: list[str],
) -> str:
    observer = oc.observer_axis(
        profile_mismatch=profile_identity["mismatch"],
        boundary_ambiguous=(confidence == "ambiguous_prior_commands"),
        artifact_resolutions=resolutions,
    )
    if profile_identity["mismatch"]:
        reason_codes.append("model_identity_mismatch")
    if observer != "valid":
        if confidence == "ambiguous_prior_commands":
            reason_codes.append("mutation_boundary_ambiguous")
        for resolution in resolutions:
            if resolution.blocks_observer:
                if resolution.runtime_unverified_present:
                    reason_codes.append("runtime_context_unverified")
                if resolution.unsupported_present:
                    reason_codes.append("unsupported_read_observation")
        return "invalid"

    for addition in post_diff_additions:
        if addition["phase"] == "before_first_mutation":
            if addition["derivable_from_original_facts"]:
                reason_codes.append(
                    f"resolver_missed_obligation:{addition['path']}"
                )
                return "invalid"
            reason_codes.append(
                f"scope_drift_before_first_mutation:{addition['path']}"
            )
            return "fail"

    failed_groups = [
        row["group_id"] for row in group_rows if not row["gate_satisfied"]
    ]
    failed_checks = [
        row["checker_id"]
        for row in semantic_rows
        if row["status"] in {"fail", "invalid_input"}
    ]
    critical_signals = [
        signal["signal"]
        for signal in plan.get("unresolved_signals") or []
        if signal["severity"] == "critical"
    ]
    if failed_groups:
        reason_codes.extend(
            f"required_group_unsatisfied:{group_id}"
            for group_id in failed_groups
        )
    if failed_checks:
        reason_codes.extend(
            f"semantic_check_blocking:{checker_id}"
            for checker_id in failed_checks
        )
    if critical_signals:
        reason_codes.extend(
            f"unresolved_critical_signal:{signal}"
            for signal in critical_signals
        )
    if not plan.get("planned_mutation_scope"):
        reason_codes.append("planned_mutation_scope_empty")
    if failed_groups or failed_checks or critical_signals or not plan.get(
        "planned_mutation_scope"
    ):
        return "fail"
    return "pass"


def _gate_result(
    plan: dict[str, Any],
    ledger: dict[str, Any],
    attestation_id: str | None,
    cutoff: dict[str, Any] | None,
    confidence: str,
    group_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    ambiguous: list[dict[str, Any]],
    unsupported: list[dict[str, Any]],
    post_diff_additions: list[dict[str, Any]],
    decision: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    result = {
        "schema_version": GATE_RESULT_SCHEMA_VERSION,
        "decision": decision,
        "enforcement_mode": "audited",
        "plan_hash": plan["plan_hash"],
        "ledger_hash": ledger["ledger_hash"],
        "session_attestation_id": attestation_id,
        "mutation_cutoff": cutoff,
        "mutation_cutoff_confidence": confidence,
        "group_results": group_rows,
        "semantic_check_results": semantic_rows,
        "unsupported_events": unsupported,
        "ambiguous_events": ambiguous,
        "post_diff_additions": [
            {
                "path": addition["path"],
                "phase": addition["phase"],
                "source_rule_ids": addition["source_rule_ids"],
            }
            for addition in post_diff_additions
        ],
        "reason_codes": sorted(set(reason_codes)),
        "authorization": None,
    }
    errors = contract_validator.validate_against(
        "xuunity.stack-gate-result.schema.json", result
    )
    semantic_errors = oc.gate_result_semantic_errors(result)
    if errors or semantic_errors:
        raise GateUsageError(
            f"internal error: gate result invalid: {(errors + semantic_errors)[:5]}"
        )
    return result


def _check_or_reconcile(args: argparse.Namespace, reconcile: bool) -> int:
    plan = _load_json(
        Path(args.plan), "xuunity.stack-plan.schema.json", "stack plan"
    )
    ledger = _load_json(
        Path(args.ledger), "xuunity.observation-ledger.schema.json",
        "observation ledger",
    )
    computed_ledger_hash = xc.document_hash(ledger, "ledger_hash")
    reason_codes: list[str] = []
    attestation_id, attestation_reasons = _verify_attestation(
        Path(args.session_attestation) if args.session_attestation else None
    )
    reason_codes.extend(attestation_reasons)
    if computed_ledger_hash != ledger["ledger_hash"]:
        result = _gate_result(
            plan, ledger, attestation_id, None, "no_mutation_observed",
            [], [], [], [], [], "invalid",
            reason_codes + ["ledger_hash_mismatch"],
        )
        _write_result(args, result)
        return EXIT_INVALID

    events = ledger.get("events") or []
    cutoff, confidence, ambiguous_events, unsupported_events = (
        _mutation_cutoff(events)
    )
    cutoff_seq = cutoff["started_seq"] if cutoff else FAR_FUTURE_SEQ
    group_rows, resolutions = evaluate_groups(
        plan, ledger, cutoff_seq, {"before_first_mutation"}
    )
    semantic_rows = run_semantic_checks(
        plan,
        Path(args.semantic_input_manifest)
        if args.semantic_input_manifest
        else None,
        Path(__file__).resolve().parent,
    )
    profile_identity = oc.profile_identity_check(
        (ledger.get("requested_profile") or {}).get("model"),
        (ledger.get("observed_profile") or {}).get("model"),
    )

    post_diff_additions: list[dict[str, Any]] = []
    closeout_rows: list[dict[str, Any]] = []
    reopen_reasons: list[str] = []
    if reconcile:
        envelope = _load_json(
            Path(args.task_envelope), "xuunity.task-envelope.schema.json",
            "task envelope",
        )
        diff_text = Path(args.parent_diff).read_text(encoding="utf-8")
        try:
            reconciliation = resolver.reconcile_additions(
                Path(args.repo_root),
                Path(args.ruleset),
                envelope,
                plan,
                diff_text,
                task_text_file=(
                    Path(args.task_text_file)
                    if args.task_text_file and args.task_text_file != "none"
                    else None
                ),
                extension_paths=[
                    Path(path) for path in args.ruleset_extension or []
                ],
            )
        except (resolver.ResolverUsageError, resolver.PlanError) as error:
            print(f"reconcile error: {error}", file=sys.stderr)
            return EXIT_USAGE
        post_diff_additions = reconciliation["additions"]
        for addition in post_diff_additions:
            if addition["phase"] in {"before_closeout", "on_reconcile"}:
                artifact = next(
                    artifact
                    for artifact in reconciliation["diff_plan"][
                        "required_artifacts"
                    ]
                    if artifact["path"] == addition["path"]
                )
                resolution = resolve_artifact_state(
                    artifact, ledger, FAR_FUTURE_SEQ
                )
                addition["satisfied_by_end"] = resolution.satisfied
                if not resolution.satisfied:
                    reopen_reasons.append(
                        f"reopen_required:{addition['path']}"
                    )
        closeout_rows, closeout_resolutions = evaluate_groups(
            plan, ledger, FAR_FUTURE_SEQ, {"before_closeout", "on_reconcile"}
        )
        for row in closeout_rows:
            if not row["gate_satisfied"]:
                reopen_reasons.append(f"reopen_required:{row['group_id']}")
        resolutions = resolutions + closeout_resolutions

    decision = _decide(
        plan, group_rows, resolutions, semantic_rows, confidence,
        profile_identity, post_diff_additions, reason_codes,
    )
    if decision == "pass" and reopen_reasons:
        decision = "reopen_required"
        reason_codes.extend(reopen_reasons)

    cutoff_for_rows = cutoff_seq
    result = _gate_result(
        plan, ledger, attestation_id, cutoff, confidence,
        group_rows + closeout_rows, semantic_rows,
        [_flagged_row(event, cutoff_for_rows) for event in ambiguous_events],
        [_flagged_row(event, cutoff_for_rows) for event in unsupported_events],
        post_diff_additions, decision, reason_codes,
    )
    _write_result(args, result)
    if decision == "pass":
        return EXIT_PASS
    if decision in {"fail", "reopen_required"}:
        return EXIT_FAIL
    if decision == "not_runnable":
        return EXIT_NOT_RUNNABLE
    return EXIT_INVALID


def _write_result(args: argparse.Namespace, result: dict[str, Any]) -> None:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        f"{result['decision']} ({result['enforcement_mode']}); "
        f"reasons: {', '.join(result['reason_codes']) or 'none'}"
    )


def _derive(args: argparse.Namespace) -> int:
    envelope = _load_json(
        Path(args.task_envelope), "xuunity.task-envelope.schema.json",
        "task envelope",
    )
    execution_contract = None
    if envelope.get("execution_contract_ref"):
        contract_path = Path(envelope["execution_contract_ref"])
        if contract_path.is_file():
            execution_contract = xc.strict_parse(contract_path.read_bytes())
    try:
        plan = resolver.derive_plan(
            Path(args.repo_root),
            Path(args.ruleset),
            envelope,
            task_text_file=(
                Path(args.task_text_file)
                if args.task_text_file and args.task_text_file != "none"
                else None
            ),
            extension_paths=[
                Path(path) for path in args.ruleset_extension or []
            ],
            execution_contract=execution_contract,
        )
    except resolver.ResolverUsageError as error:
        print(f"derive error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except resolver.PlanError as error:
        print(f"plan error: {error}", file=sys.stderr)
        return EXIT_INVALID
    _verify_attestation(
        Path(args.session_attestation) if args.session_attestation else None
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        f"plan {plan['plan_hash'][:12]}…: "
        f"{len(plan['required_artifacts'])} artifacts, "
        f"{len(plan['requirement_groups'])} groups, "
        f"{len(plan['semantic_checks'])} semantic checks, "
        f"{len(plan['matched_rule_ids'])} rules"
    )
    return EXIT_PASS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    derive = subparsers.add_parser("derive")
    derive.add_argument("--repo-root", required=True)
    derive.add_argument("--ruleset", required=True)
    derive.add_argument("--ruleset-extension", action="append")
    derive.add_argument("--task-envelope", required=True)
    derive.add_argument("--task-text-file")
    derive.add_argument("--session-attestation")
    derive.add_argument("--output", required=True)

    for name in ("check", "reconcile"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--plan", required=True)
        sub.add_argument("--ledger", required=True)
        sub.add_argument("--semantic-input-manifest")
        sub.add_argument("--session-attestation")
        sub.add_argument("--output", required=True)
        if name == "reconcile":
            sub.add_argument("--parent-diff", required=True)
            sub.add_argument("--repo-root", required=True)
            sub.add_argument("--ruleset", required=True)
            sub.add_argument("--ruleset-extension", action="append")
            sub.add_argument("--task-envelope", required=True)
            sub.add_argument("--task-text-file")

    args = parser.parse_args()
    try:
        if args.command == "derive":
            return _derive(args)
        return _check_or_reconcile(args, args.command == "reconcile")
    except GateUsageError as error:
        print(f"gate error: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
