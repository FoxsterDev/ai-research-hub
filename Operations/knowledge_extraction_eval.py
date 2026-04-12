#!/usr/bin/env python3

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_PACK = ROOT / "Operations" / "XUUNITY_KNOWLEDGE_EXTRACTION_GOLDEN_CASES.json"
WEIGHTS = {
    "critical_recall": 0.30,
    "precision": 0.15,
    "routing_accuracy": 0.20,
    "semantic_preservation": 0.15,
    "duplication_safety": 0.10,
    "boundary_safety": 0.10,
}
ALL_SCORES = [
    "critical_recall",
    "precision",
    "routing_accuracy",
    "semantic_preservation",
    "duplication_safety",
    "boundary_safety",
    "actionability",
]
ALL_GATES = [
    "critical_omissions",
    "wrong_critical_destinations",
    "unsafe_shared_leaks",
    "conflict_flattening",
]


@dataclass
class RunPaths:
    run_json: Path
    prompts_dir: Path
    report_md: Path
    summary_json: Path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n")


def resolve_default_report_dir() -> Path:
    host_dir = ROOT.parent / "AIOutput" / "Reports" / "System"
    if host_dir.parent.parent.exists():
        return host_dir
    raise ValueError("No default host AIOutput root found. Pass --output-dir explicitly.")


def build_paths(run_name: str, output_dir: Path) -> RunPaths:
    return RunPaths(
        run_json=output_dir / f"{run_name}.json",
        prompts_dir=output_dir / f"{run_name}_prompts",
        report_md=output_dir / f"{run_name}.md",
        summary_json=output_dir / f"{run_name}_summary.json",
    )


def make_run_bundle(case_pack: dict[str, Any], evaluator: str, workflow_version: str, scope: str) -> dict[str, Any]:
    today = str(date.today())
    cases = []
    for case in case_pack["cases"]:
        cases.append(
            {
                "id": case["id"],
                "category": case["category"],
                "source_type": case["source_type"],
                "topic": case["topic"],
                "source": case["source"],
                "expected": case["expected"],
                "evaluation": {
                    "outcome": None,
                    "critical_gate": {name: None for name in ALL_GATES},
                    "scores": {name: None for name in ALL_SCORES},
                    "findings": {
                        "captured_well": "",
                        "missed": "",
                        "misrouted": "",
                        "too_noisy": "",
                    },
                    "decision": {
                        "keep_as_is": "",
                        "fix_before_release": "",
                    },
                },
            }
        )
    return {
        "run_metadata": {
            "date": today,
            "evaluator": evaluator,
            "workflow_version": workflow_version,
            "scope": scope,
            "case_pack_version": case_pack["version"],
            "run_type": "authoritative",
            "evidence_level": "pending_human_approval",
            "approver": "",
            "approval_date": "",
        },
        "cases": cases,
    }


def write_prompts(bundle: dict[str, Any], prompts_dir: Path) -> None:
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for case in bundle["cases"]:
        prompt = (
            f"# Case: {case['id']}\n\n"
            f"- Category: {case['category']}\n"
            f"- Source type: {case['source_type']}\n"
            f"- Topic: {case['topic']}\n"
            f"- Recommended command: `xuunity extract this source`\n\n"
            "## Source\n"
            "```text\n"
            f"{case['source']}\n"
            "```\n\n"
            "## Evaluator Notes\n"
            "- Run the extraction workflow against the source above.\n"
            "- Do not reveal the expected answer to the extraction workflow.\n"
            "- Score the result in the corresponding run JSON file.\n"
        )
        (prompts_dir / f"{case['id']}.md").write_text(prompt)


def validate_bundle(bundle: dict[str, Any]) -> None:
    for case in bundle["cases"]:
        evaluation = case["evaluation"]
        for gate_name in ALL_GATES:
            value = evaluation["critical_gate"][gate_name]
            if value is None or not isinstance(value, int) or value < 0:
                raise ValueError(f"Case {case['id']} has invalid gate '{gate_name}': {value}")
        for score_name in ALL_SCORES:
            value = evaluation["scores"][score_name]
            if value is None or not isinstance(value, (int, float)) or value < 0 or value > 5:
                raise ValueError(f"Case {case['id']} has invalid score '{score_name}': {value}")


def compute_weighted_total(scores: dict[str, float]) -> float:
    total = 0.0
    for name, weight in WEIGHTS.items():
        total += scores[name] * weight
    return round(total, 2)


def classify_case(case: dict[str, Any]) -> tuple[str, float, bool]:
    gates = case["evaluation"]["critical_gate"]
    hard_fail = any(gates[name] > 0 for name in ALL_GATES)
    weighted_total = compute_weighted_total(case["evaluation"]["scores"])
    if hard_fail:
        return "fail", weighted_total, True
    if weighted_total >= 4.0:
        return "pass", weighted_total, False
    if weighted_total >= 3.5:
        return "warning", weighted_total, False
    return "fail", weighted_total, False


def summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    passed = 0
    failed = 0
    warnings = 0
    total_weighted = 0.0
    critical_omissions = 0
    wrong_critical_destinations = 0
    unsafe_shared_leaks = 0
    duplicate_proposals = 0
    for case in bundle["cases"]:
        outcome, weighted_total, _ = classify_case(case)
        case["evaluation"]["outcome"] = outcome
        case["evaluation"]["scores"]["weighted_total"] = weighted_total
        total_weighted += weighted_total
        gates = case["evaluation"]["critical_gate"]
        critical_omissions += gates["critical_omissions"]
        wrong_critical_destinations += gates["wrong_critical_destinations"]
        unsafe_shared_leaks += gates["unsafe_shared_leaks"]
        duplicate_proposals += max(case["evaluation"]["scores"]["duplication_safety"] < 3, 0)
        if outcome == "pass":
            passed += 1
        elif outcome == "warning":
            warnings += 1
        else:
            failed += 1
    case_count = len(bundle["cases"])
    average_weighted = round(total_weighted / case_count, 2) if case_count else 0.0
    blocking = critical_omissions > 0 or wrong_critical_destinations > 0 or unsafe_shared_leaks > 0
    return {
        "cases_run": case_count,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "average_weighted_score": average_weighted,
        "critical_omissions": critical_omissions,
        "wrong_critical_destinations": wrong_critical_destinations,
        "unsafe_shared_leaks": unsafe_shared_leaks,
        "duplicate_proposals": duplicate_proposals,
        "blocking_regressions": blocking,
    }


def build_health_summary(bundle: dict[str, Any], summary: dict[str, Any], baseline_exists: bool) -> dict[str, Any]:
    meta = bundle["run_metadata"]
    run_type = meta.get("run_type", "authoritative")
    evidence_level = meta.get("evidence_level", "unknown")
    authoritative = run_type == "authoritative" and evidence_level == "human_scored" and bool(meta.get("approver")) and bool(meta.get("approval_date"))
    if not authoritative:
        status = "non_authoritative"
    elif summary["blocking_regressions"]:
        status = "failing"
    elif baseline_exists:
        status = "current"
    else:
        status = "stale"
    return {
        "status": status,
        "run_type": run_type,
        "evidence_level": evidence_level,
        "authoritative": authoritative,
        "approver": meta.get("approver", ""),
        "approval_date": meta.get("approval_date", ""),
        "baseline_exists": baseline_exists,
        "last_run_date": meta["date"],
        "workflow_version": meta["workflow_version"],
        "scope": meta["scope"],
        "cases_run": summary["cases_run"],
        "passed": summary["passed"],
        "warnings": summary["warnings"],
        "failed": summary["failed"],
        "average_weighted_score": summary["average_weighted_score"],
        "critical_omissions": summary["critical_omissions"],
        "wrong_critical_destinations": summary["wrong_critical_destinations"],
        "unsafe_shared_leaks": summary["unsafe_shared_leaks"],
        "duplicate_proposals": summary["duplicate_proposals"],
        "blocking_regressions": summary["blocking_regressions"],
    }


def render_report(bundle: dict[str, Any], summary: dict[str, Any]) -> str:
    meta = bundle["run_metadata"]
    lines = [
        "# Knowledge Extraction Evaluation Report",
        "",
        "## Run Metadata",
        f"- Date: {meta['date']}",
        f"- Evaluator: {meta['evaluator']}",
        f"- Prompt or workflow version: {meta['workflow_version']}",
        f"- Scope: {meta['scope']}",
        f"- Evidence level: {meta.get('evidence_level', 'unknown')}",
        f"- Approver: {meta.get('approver') or 'pending'}",
        f"- Approval date: {meta.get('approval_date') or 'pending'}",
        "",
        "## Summary",
        f"- Cases run: {summary['cases_run']}",
        f"- Passed: {summary['passed']}",
        f"- Warnings: {summary['warnings']}",
        f"- Failed: {summary['failed']}",
        f"- Average weighted score: {summary['average_weighted_score']}",
        f"- Critical omissions: {summary['critical_omissions']}",
        f"- Wrong critical destinations: {summary['wrong_critical_destinations']}",
        f"- Unsafe shared leaks: {summary['unsafe_shared_leaks']}",
        f"- Duplicate proposals: {summary['duplicate_proposals']}",
        "",
        "## Hard-Fail Result",
        f"- Blocking regressions: {'yes' if summary['blocking_regressions'] else 'no'}",
        f"- Release recommendation: {'do not treat as safe until failures are resolved' if summary['blocking_regressions'] else 'no blocking regressions in this run'}",
        "",
        "## Case Results",
        "",
    ]
    for case in bundle["cases"]:
        evaluation = case["evaluation"]
        gates = evaluation["critical_gate"]
        scores = evaluation["scores"]
        findings = evaluation["findings"]
        decision = evaluation["decision"]
        lines.extend(
            [
                f"### Case: `{case['id']}`",
                f"- Category: {case['category']}",
                f"- Topic: {case['topic']}",
                f"- Outcome: `{evaluation['outcome']}`",
                "- Critical gate:",
                f"  - Critical omissions: {gates['critical_omissions']}",
                f"  - Wrong critical destinations: {gates['wrong_critical_destinations']}",
                f"  - Unsafe shared leaks: {gates['unsafe_shared_leaks']}",
                f"  - Conflict flattening: {gates['conflict_flattening']}",
                "- Scores:",
                f"  - Critical recall: {scores['critical_recall']}",
                f"  - Precision: {scores['precision']}",
                f"  - Routing accuracy: {scores['routing_accuracy']}",
                f"  - Semantic preservation: {scores['semantic_preservation']}",
                f"  - Duplication safety: {scores['duplication_safety']}",
                f"  - Boundary safety: {scores['boundary_safety']}",
                f"  - Actionability: {scores['actionability']}",
                f"  - Weighted total: {scores['weighted_total']}",
                "- Findings:",
                f"  - What was captured well: {findings['captured_well'] or 'n/a'}",
                f"  - What was missed: {findings['missed'] or 'n/a'}",
                f"  - What was routed incorrectly: {findings['misrouted'] or 'n/a'}",
                f"  - What was too noisy: {findings['too_noisy'] or 'n/a'}",
                "- Decision:",
                f"  - Keep as is: {decision['keep_as_is'] or 'n/a'}",
                f"  - Fix before release: {decision['fix_before_release'] or 'n/a'}",
                "",
            ]
        )
    return "\n".join(lines)


def cmd_init(args: argparse.Namespace) -> None:
    case_pack = load_json(Path(args.case_pack))
    output_dir = Path(args.output_dir) if args.output_dir else resolve_default_report_dir()
    paths = build_paths(args.run_name, output_dir)
    bundle = make_run_bundle(case_pack, args.evaluator, args.workflow_version, args.scope)
    bundle["run_metadata"]["run_type"] = args.run_type
    bundle["run_metadata"]["evidence_level"] = args.evidence_level
    write_json(paths.run_json, bundle)
    write_prompts(bundle, paths.prompts_dir)
    print(f"Created run bundle: {paths.run_json}")
    print(f"Created prompt pack: {paths.prompts_dir}")


def cmd_report(args: argparse.Namespace) -> None:
    run_json = Path(args.run_json)
    bundle = load_json(run_json)
    validate_bundle(bundle)
    summary = summarize_bundle(bundle)
    output_path = Path(args.output_md) if args.output_md else run_json.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(bundle, summary) + "\n")
    report_root = run_json.parent
    baseline_exists = (report_root / "knowledge_extraction_eval_baseline_v1.md").exists()
    summary_path = Path(args.output_summary) if args.output_summary else run_json.with_name(f"{run_json.stem}_summary.json")
    health_summary = build_health_summary(bundle, summary, baseline_exists)
    write_json(summary_path, health_summary)
    latest_summary_path = report_root / "knowledge_extraction_eval_latest_summary.json"
    if health_summary["authoritative"]:
        write_json(latest_summary_path, health_summary)
    if args.write_back:
        write_json(run_json, bundle)
    print(f"Wrote report: {output_path}")
    print(f"Wrote summary: {summary_path}")
    if health_summary["authoritative"]:
        print(f"Updated latest summary: {latest_summary_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge extraction evaluation harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a run bundle and prompt pack")
    init_parser.add_argument("--run-name", required=True)
    init_parser.add_argument("--evaluator", default="manual_evaluator")
    init_parser.add_argument("--workflow-version", default="extraction triage v1")
    init_parser.add_argument("--scope", default="golden regression pack")
    init_parser.add_argument("--case-pack", default=str(DEFAULT_CASE_PACK))
    init_parser.add_argument("--output-dir")
    init_parser.add_argument("--run-type", choices=["authoritative", "smoke", "demo"], default="authoritative")
    init_parser.add_argument("--evidence-level", choices=["human_scored", "synthetic", "demo"], default="human_scored")
    init_parser.set_defaults(func=cmd_init)

    report_parser = subparsers.add_parser("report", help="Score a completed run bundle and render markdown")
    report_parser.add_argument("--run-json", required=True)
    report_parser.add_argument("--output-md")
    report_parser.add_argument("--output-summary")
    report_parser.add_argument("--write-back", action="store_true")
    report_parser.set_defaults(func=cmd_report)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
