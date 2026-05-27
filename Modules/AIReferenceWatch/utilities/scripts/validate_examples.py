#!/usr/bin/env python3
"""Dependency-free smoke validator for checked-in AIReferenceWatch examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compare_feature_bags import load_feature_bags


REQUIRED_REPORT_FIELDS = {
    "schemaVersion",
    "focus",
    "generatedAtUtc",
    "xuunityToolId",
    "inputs",
    "capabilityMatrix",
    "dataQuality",
    "manualReviewRequired",
    "backlogCandidates",
    "nonActionableClaims"
}

REQUIRED_REVIEW_FIELDS = {
    "schemaVersion",
    "featureArea",
    "generatedAtUtc",
    "xuunityCurrentState",
    "overallLeaders",
    "capabilityLeaders",
    "borrow",
    "reject",
    "differentiate",
    "recommendedDirection"
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def require_fields(data: dict[str, Any], required: set[str], path: Path) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"{path} is missing required fields: {', '.join(missing)}")


def validate_report(path: Path) -> None:
    report = load_json(path)
    require_fields(report, REQUIRED_REPORT_FIELDS, path)
    if report["schemaVersion"] != "xuunity.reference-watch.comparison-report.v1":
        raise ValueError(f"{path} has unsupported report schemaVersion")
    if not isinstance(report["capabilityMatrix"], list) or not report["capabilityMatrix"]:
        raise ValueError(f"{path} must include a non-empty capabilityMatrix")
    for entry in report["capabilityMatrix"]:
        require_fields(
            entry,
            {"capability", "xuunityStatus", "referenceStatuses", "outcome"},
            path,
        )
        if entry["outcome"] == "manual_review_required" and report["backlogCandidates"]:
            claimed_candidates = [
                candidate
                for candidate in report["backlogCandidates"]
                if candidate.get("candidateId") == entry["capability"]
            ]
            if claimed_candidates:
                raise ValueError(f"{path} turns manual-review-only capability into backlog")


def validate_review(path: Path) -> None:
    review = load_json(path)
    require_fields(review, REQUIRED_REVIEW_FIELDS, path)
    if review["schemaVersion"] != "xuunity.reference-watch.reference-first-review.v1":
        raise ValueError(f"{path} has unsupported review schemaVersion")


def validate_issue_summary(path: Path) -> None:
    summary = load_json(path)
    require_fields(summary, {"schemaVersion", "generatedAtUtc", "sources"}, path)
    if summary["schemaVersion"] != "xuunity.reference-watch.issue-watch-summary.v1":
        raise ValueError(f"{path} has unsupported issue-watch schemaVersion")


def validate_all(root: Path) -> int:
    examples_root = root / "examples"
    schema_files = sorted((root / "schemas").glob("*.json"))
    example_files = sorted(examples_root.rglob("*.json"))

    for path in schema_files + example_files:
        load_json(path)

    load_feature_bags([str(path) for path in sorted((examples_root / "feature_bags").glob("*.json"))])

    for path in sorted((examples_root / "reports").glob("*.json")):
        validate_report(path)

    for path in sorted((examples_root / "reviews").glob("*.json")):
        validate_review(path)

    validate_issue_summary(examples_root / "issue_watch_summary.example.json")
    return len(schema_files) + len(example_files)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate checked-in AIReferenceWatch utility examples")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Utilities root directory"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    count = validate_all(Path(args.root))
    print(f"validated {count} JSON files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
