"""Explicit-path Model Fitness operator interface. No implicit provider launch."""

import argparse
import json
import sys
from pathlib import Path

import xuunity_canonical as xc

from . import calibration, executor, experiment_journal, operations, profiles, records, reporting, schedule, suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="bind an installed CLI and parser; no model call")
    inspect.add_argument("--adapter", choices=["codex", "claude"], required=True)
    inspect.add_argument("--executable", type=Path, required=True)
    inspect.add_argument("--model", required=True)
    inspect.add_argument("--effort", required=True)
    inspect.add_argument("--output", type=Path, required=True)
    prepare = commands.add_parser("prepare", help="verify fixture and freeze its seed and guidance")
    prepare.add_argument("--fixture", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--seed", type=Path)
    prepare.add_argument("--task-file", type=Path)
    prepare.add_argument("--ruleset-relative", required=True)
    prepare.add_argument("--planned-path", action="append", required=True)
    prepare.add_argument("--project")
    prepare.add_argument("--protocol-hash")
    prepare.add_argument("--semantic-input-manifest", type=Path)
    prepare.add_argument("--suite", type=Path)
    prepare.add_argument("--task-kind", default="feature_development")
    prepare.add_argument("--risk-class", default="normal")
    prepare.add_argument("--referenced-path", action="append")
    prepare.add_argument("--ruleset-extension", type=Path, action="append")
    plan = commands.add_parser("plan", help="freeze the complete launch roster before execution")
    plan.add_argument("--attempts", type=Path, required=True)
    plan.add_argument("--schedule-id", required=True)
    plan.add_argument("--journal-root", type=Path, required=True)
    plan.add_argument("--max-wall-seconds", type=int, required=True)
    plan.add_argument("--stop-rule", choices=["fixed", "stop_on_evaluator_or_budget"], default="stop_on_evaluator_or_budget")
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--suite", type=Path)
    plan.add_argument("--fixture-profile-keys", type=Path)
    plan.add_argument("--comparison-contracts", type=Path)
    for name in ("calibrate", "run"):
        command = commands.add_parser(name, help="launch exactly one preregistered model attempt")
        command.add_argument("--profile", type=Path, required=True)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--attempt", required=True)
        command.add_argument("--workspace", type=Path, required=True)
        if name == "run":
            command.add_argument("--prepared", type=Path, required=True)
            command.add_argument("--calibration", type=Path, required=True)
    score = commands.add_parser("score", help="verify and rescore captured evidence without a model call")
    score.add_argument("--evidence", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    full = commands.add_parser("run-schedule", help="execute a complete frozen roster without retrying completed attempts")
    full.add_argument("--plan", type=Path, required=True)
    recover = commands.add_parser("recover", help="record a dead-parent interruption; never relaunch")
    recover.add_argument("--plan", type=Path, required=True)
    recover.add_argument("--attempt", required=True)
    close = commands.add_parser("close", help="censor remaining rows under an explicit stop reason")
    close.add_argument("--plan", type=Path, required=True)
    close.add_argument("--reason", required=True)
    aggregate = commands.add_parser("aggregate", help="join a fixed suite to its journal and render results")
    aggregate.add_argument("--suite", type=Path, required=True)
    aggregate.add_argument("--plan", type=Path, required=True)
    aggregate.add_argument("--profile-key", required=True)
    aggregate.add_argument("--fixture-profile-keys", type=Path)
    aggregate.add_argument("--output", type=Path, required=True)
    aggregate.add_argument("--report", type=Path, required=True)
    report = commands.add_parser("report", help="render installation health and task diagnostics separately")
    report.add_argument("--plan", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--report", type=Path, required=True)
    exp = commands.add_parser("experiment", help="evaluate persisted arms and reserve family alpha once")
    exp.add_argument("--manifest", type=Path, required=True)
    exp.add_argument("--control", type=Path, required=True)
    exp.add_argument("--treatment", type=Path, required=True)
    exp.add_argument("--journal-root", type=Path, required=True)
    exp.add_argument("--alpha-charge", type=float, required=True)
    exp.add_argument("--output", type=Path, required=True)
    telemetry = commands.add_parser("telemetry", help="record a verified real session for rollout review")
    telemetry.add_argument("--evidence", type=Path, required=True)
    telemetry.add_argument("--root", type=Path, required=True)
    rollout = commands.add_parser("rollout", help="set observe/off or require verified conformance for later stages")
    rollout.add_argument("--root", type=Path, required=True)
    rollout.add_argument("--mode", choices=["off", "observe", "advisory", "blocking"], required=True)
    rollout.add_argument("--profile", type=Path)
    rollout.add_argument("--calibration", type=Path)
    changed = commands.add_parser("protocol-change", help="mark baselines stale and persist a pending smoke roster")
    changed.add_argument("--root", type=Path, required=True)
    changed.add_argument("--change-id", required=True)
    changed.add_argument("--before", required=True)
    changed.add_argument("--after", required=True)
    changed.add_argument("--baseline", action="append", type=Path, required=True)
    changed.add_argument("--fixture-id", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        for name in ("output", "report"):
            path = getattr(args, name, None)
            if path and path.exists():
                raise ValueError("output_already_exists:" + name)
        result = None
        if args.command == "inspect":
            result = profiles.inspect(args.adapter, args.executable, args.model, args.effort)
        elif args.command == "prepare":
            result = executor.prepare(args.fixture, output=args.output, seed=args.seed,
                                      task_text=args.task_file.read_text() if args.task_file else None,
                                      ruleset_relative=args.ruleset_relative, planned_paths=args.planned_path,
                                      project=args.project, protocol_content_hash=args.protocol_hash,
                                      semantic_input_manifest=args.semantic_input_manifest,
                                      suite_document=records.read(args.suite) if args.suite else None,
                                      task_kind=args.task_kind, risk_class=args.risk_class,
                                      referenced_paths=args.referenced_path, ruleset_extensions=args.ruleset_extension)
        elif args.command == "plan":
            result = schedule.build(xc.load_strict(args.attempts), schedule_id=args.schedule_id,
                                    journal_root=args.journal_root, max_wall_seconds=args.max_wall_seconds,
                                    stop_rule=args.stop_rule,
                                    suite_document=records.read(args.suite) if args.suite else None,
                                    fixture_profile_keys=records.read(args.fixture_profile_keys) if args.fixture_profile_keys else None,
                                    comparison_contracts=records.read(args.comparison_contracts) if args.comparison_contracts else None)
        elif args.command == "calibrate":
            result = calibration.run(records.read(args.profile), records.read(args.plan), args.attempt, workspace=args.workspace)
        elif args.command == "run":
            result = executor.run(args.prepared, records.read(args.profile), args.calibration,
                                  records.read(args.plan), args.attempt, workspace=args.workspace)
        elif args.command == "score":
            records.disjoint(args.evidence, args.output)
            result = executor.score(args.evidence)
        elif args.command == "run-schedule":
            result = {"accounting": executor.run_schedule(records.read(args.plan))}
        elif args.command == "recover":
            result = executor.recover(records.read(args.plan), args.attempt)
        elif args.command == "close":
            schedule.close(records.read(args.plan), args.reason)
            result = {"status": "closed"}
        elif args.command == "aggregate":
            definition = records.read(args.suite)
            plan = records.read(args.plan)
            contract = schedule.comparison_contract(plan, definition)
            keys = records.read(args.fixture_profile_keys) if args.fixture_profile_keys else None
            if contract.get("strict_profile_key") != args.profile_key or contract.get("fixture_profile_keys") != keys:
                raise ValueError("aggregation_comparison_contract_changed")
            result = suite.aggregate_suite(
                definition, reporting.cohort(plan, definition),
                strict_profile_key=args.profile_key,
                fixture_profile_keys=keys,
            )
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x") as stream:
                stream.write(suite.render_suite_report(result))
        elif args.command == "report":
            result = reporting.diagnostic_report(records.read(args.plan))
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x") as stream:
                stream.write(reporting.render_diagnostic(result))
        elif args.command == "experiment":
            result = experiment_journal.evaluate(
                records.read(args.manifest), records.read(args.control), records.read(args.treatment),
                root=args.journal_root, alpha_charge=args.alpha_charge,
                control_ref=str(args.control), treatment_ref=str(args.treatment),
            )
        elif args.command == "telemetry":
            result = operations.record_session(args.root, args.evidence)
        elif args.command == "rollout":
            result = operations.set_rollout(args.root, args.mode,
                                           installed=records.read(args.profile) if args.profile else None,
                                           calibration_path=args.calibration)
        elif args.command == "protocol-change":
            result = operations.protocol_changed(args.root, change_id=args.change_id, before=args.before,
                                                 after=args.after, baseline_refs=args.baseline,
                                                 smoke_fixture_ids=args.fixture_id)
        if getattr(args, "output", None) and args.command != "prepare":
            records.write(args.output, result, exclusive=True)
        print(json.dumps({k: result[k] for k in
                          ("record_hash", "run_id", "score_total", "diagnostic_compatible", "score_eligible", "status", "grade", "accounting", "mode")
                          if k in result}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"fitness error: {error}", file=sys.stderr)
        return 2
