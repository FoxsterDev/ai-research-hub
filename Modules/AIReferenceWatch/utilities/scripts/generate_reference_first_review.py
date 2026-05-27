#!/usr/bin/env python3
"""Generate a reference-first review skeleton from a comparison report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generated_at(args: argparse.Namespace) -> str:
    return args.generated_at_utc or utc_now()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(data: dict[str, Any], path: Path | None) -> None:
    rendered = json.dumps(data, indent=2, sort_keys=False) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def extend_many(values: list[str] | None) -> list[str]:
    return [value for value in values or [] if value]


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    report_path = Path(args.report)
    report = load_json(report_path)
    if report.get("schemaVersion") != "xuunity.reference-watch.comparison-report.v1":
        raise ValueError(f"{report_path} is not a comparison report")
    if "focus" not in report:
        raise ValueError(f"{report_path} is missing required field 'focus'")
    return {
        "schemaVersion": "xuunity.reference-watch.reference-first-review.v1",
        "featureArea": args.feature_area or report["focus"],
        "generatedAtUtc": generated_at(args),
        "sourceComparisonReport": str(report_path),
        "xuunityCurrentState": report.get("xuunityCurrentState", ""),
        "overallLeaders": report.get("overallLeaders", []),
        "capabilityLeaders": report.get("capabilityLeaders", []),
        "issueThemes": extend_many(args.issue_theme),
        "candidateContractOptions": extend_many(args.candidate_contract_option),
        "borrow": extend_many(args.borrow),
        "reject": extend_many(args.reject),
        "differentiate": extend_many(args.differentiate),
        "recommendedDirection": args.recommended_direction,
        "nextArtifact": args.next_artifact,
        "reviewer": args.reviewer,
        "status": args.status,
        "notes": args.notes
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a reference-first review skeleton")
    parser.add_argument("--report", required=True, help="Comparison report JSON path")
    parser.add_argument("--feature-area", help="Override feature area; defaults to report focus")
    parser.add_argument("--issue-theme", action="append", help="Issue theme to include")
    parser.add_argument("--candidate-contract-option", action="append", help="Candidate contract option")
    parser.add_argument("--borrow", action="append", help="Reference idea to borrow")
    parser.add_argument("--reject", action="append", help="Reference idea to reject")
    parser.add_argument("--differentiate", action="append", help="Local differentiation point")
    parser.add_argument(
        "--recommended-direction",
        required=True,
        help="Recommended design direction after reference review"
    )
    parser.add_argument("--next-artifact", default="public_contract_design")
    parser.add_argument("--reviewer", default="ai_reference_watch")
    parser.add_argument(
        "--status",
        choices=["draft", "ready_for_design_review", "accepted", "parked"],
        default="draft"
    )
    parser.add_argument("--notes", default="")
    parser.add_argument("--out", help="Write review to this path instead of stdout")
    parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic generatedAtUtc value for checked-in examples"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    review = build_review(args)
    write_json(review, Path(args.out) if args.out else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
