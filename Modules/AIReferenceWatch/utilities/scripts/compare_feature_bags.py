#!/usr/bin/env python3
"""Generate an AIReferenceWatch comparison report from normalized feature bags.

The script is intentionally dependency-free. It expects JSON feature bags that
already follow the public schema well enough for comparison.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIONABLE_STATUSES = {"implemented"}
CLAIMED_STATUS = "claimed"


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


def require_string(data: dict[str, Any], key: str, path: Path) -> None:
    if not isinstance(data.get(key), str) or not data[key]:
        raise ValueError(f"{path} must define non-empty string field {key!r}")


def validate_feature_bag(data: dict[str, Any], path: Path) -> None:
    for key in ("schemaVersion", "toolId", "displayName", "capturedAtUtc", "captureMethod"):
        require_string(data, key, path)
    if data["schemaVersion"] != "xuunity.reference-watch.feature-bag.v1":
        raise ValueError(f"{path} has unsupported schemaVersion {data['schemaVersion']!r}")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError(f"{path} must define a non-empty capabilities object")
    for capability, detail in capabilities.items():
        if not isinstance(capability, str) or not capability:
            raise ValueError(f"{path} contains an invalid capability id")
        if not isinstance(detail, dict):
            raise ValueError(f"{path} capability {capability!r} must be an object")
        for key in ("status", "confidence", "evidenceType", "focusAreas"):
            if key not in detail:
                raise ValueError(f"{path} capability {capability!r} is missing {key!r}")
        if not isinstance(detail["focusAreas"], list) or not detail["focusAreas"]:
            raise ValueError(f"{path} capability {capability!r} must include at least one focus area")


def load_feature_bags(paths: list[str]) -> list[dict[str, Any]]:
    bags: list[dict[str, Any]] = []
    seen_tool_ids: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        bag = load_json(path)
        validate_feature_bag(bag, path)
        tool_id = bag["toolId"]
        if tool_id in seen_tool_ids:
            raise ValueError(f"Duplicate feature bag toolId {tool_id!r}")
        seen_tool_ids.add(tool_id)
        bags.append(bag)
    return bags


def write_json(data: dict[str, Any], path: Path | None) -> None:
    rendered = json.dumps(data, indent=2, sort_keys=False) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def capabilities_for_focus(bags: list[dict[str, Any]], focus: str) -> list[str]:
    capabilities: set[str] = set()
    for bag in bags:
        for capability, detail in bag.get("capabilities", {}).items():
            if focus in detail.get("focusAreas", []):
                capabilities.add(capability)
    return sorted(capabilities)


def detail_for(bag: dict[str, Any], capability: str) -> dict[str, Any] | None:
    detail = bag.get("capabilities", {}).get(capability)
    return detail if isinstance(detail, dict) else None


def status_for(detail: dict[str, Any] | None) -> str:
    if detail is None:
        return "missing"
    return str(detail.get("status", "unknown"))


def status_entry(tool_id: str, detail: dict[str, Any] | None) -> dict[str, Any]:
    if detail is None:
        return {
            "toolId": tool_id,
            "status": "missing",
            "confidence": "unknown",
            "evidenceType": "public_source_unknown",
            "notes": "Capability is absent from this normalized bag."
        }
    entry = {
        "toolId": tool_id,
        "status": status_for(detail),
        "confidence": str(detail.get("confidence", "unknown")),
        "evidenceType": str(detail.get("evidenceType", "public_source_unknown")),
        "notes": str(detail.get("notes", ""))
    }
    if "directAnalog" in detail:
        entry["directAnalog"] = bool(detail["directAnalog"])
    if detail.get("analogTarget"):
        entry["analogTarget"] = str(detail["analogTarget"])
    if detail.get("analogNotes"):
        entry["analogNotes"] = str(detail["analogNotes"])
    return entry


def is_direct_analog(detail: dict[str, Any] | None) -> bool:
    if detail is None:
        return False
    return detail.get("directAnalog") is not False


def is_actionable_reference(detail: dict[str, Any] | None) -> bool:
    if detail is None:
        return False
    status = status_for(detail)
    return status in ACTIONABLE_STATUSES and is_direct_analog(detail)


def is_related_non_direct_reference(detail: dict[str, Any] | None) -> bool:
    if detail is None:
        return False
    return status_for(detail) in ACTIONABLE_STATUSES and not is_direct_analog(detail)


def is_claimed_reference(detail: dict[str, Any] | None) -> bool:
    return detail is not None and status_for(detail) == CLAIMED_STATUS


def report_item(item_id: str, title: str, capability: str, source_ids: list[str], notes: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": title,
        "sourceIds": source_ids,
        "capability": capability,
        "notes": notes
    }


def classify_capability(
    capability: str,
    focus: str,
    xuunity_bag: dict[str, Any],
    reference_bags: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    x_detail = detail_for(xuunity_bag, capability)
    x_status = status_for(x_detail)
    reference_details = [(bag, detail_for(bag, capability)) for bag in reference_bags]
    reference_statuses = [status_entry(bag["toolId"], detail) for bag, detail in reference_details]

    actionable_refs = [bag["toolId"] for bag, detail in reference_details if is_actionable_reference(detail)]
    related_non_direct_refs = [
        bag["toolId"]
        for bag, detail in reference_details
        if is_related_non_direct_reference(detail)
    ]
    claimed_refs = [bag["toolId"] for bag, detail in reference_details if is_claimed_reference(detail)]
    contradicted_refs = [
        bag["toolId"]
        for bag, detail in reference_details
        if detail is not None and status_for(detail) == "contradicted"
    ]

    manual_reviews: list[dict[str, Any]] = []
    backlog_candidates: list[dict[str, Any]] = []
    non_actionable_claims: list[dict[str, Any]] = []
    xuunity_advantages: list[dict[str, Any]] = []

    if contradicted_refs:
        outcome = "contradicted_evidence"
    elif x_status == "implemented" and not actionable_refs and not related_non_direct_refs and not claimed_refs:
        outcome = "xuunity_ahead"
        xuunity_advantages.append(
            report_item(
                f"{capability}_xuunity_ahead",
                f"XUUnity has stronger normalized evidence for {capability}",
                capability,
                [],
                "Tracked references are missing or unknown for this capability in the current bags."
            )
        )
    elif x_status == "implemented":
        outcome = "no_gap"
    elif actionable_refs:
        outcome = "reference_gap"
        evidence = [
            entry for entry in reference_statuses
            if entry["toolId"] in actionable_refs
        ]
        backlog_candidates.append(
            {
                "candidateId": capability,
                "title": f"Review {capability} for {focus}",
                "focus": focus,
                "whyNow": "At least one reference has actionable normalized evidence while XUUnity is missing or weaker.",
                "xuunityCurrentState": x_status,
                "referenceEvidence": evidence,
                "requiredManualReview": False,
                "owner": "reference_watch_consumer",
                "nextArtifact": "public_contract_design"
            }
        )
    elif related_non_direct_refs:
        outcome = "manual_review_required"
        manual_reviews.append(
            report_item(
                f"{capability}_implemented_non_direct",
                f"Implemented related evidence is not a direct analog for {capability}",
                capability,
                related_non_direct_refs,
                "Reference code exists, but directAnalog=false; keep this as design input, not backlog."
            )
        )
    elif claimed_refs:
        outcome = "manual_review_required"
        item = report_item(
            f"{capability}_claimed_only",
            f"Manual review required for {capability}",
            capability,
            claimed_refs,
            "Only claimed evidence exists in the current reference bags; do not turn this into backlog work yet."
        )
        manual_reviews.append(item)
        non_actionable_claims.append(item)
    else:
        outcome = "non_actionable_claim"

    strongest = actionable_refs or ([] if x_status == "implemented" else claimed_refs)
    comparison = {
        "capability": capability,
        "focus": focus,
        "xuunityStatus": x_status,
        "referenceStatuses": reference_statuses,
        "strongestReferences": strongest,
        "outcome": outcome,
        "notes": ""
    }
    return comparison, manual_reviews, backlog_candidates, non_actionable_claims, xuunity_advantages


def build_capability_leaders(matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    leaders: list[dict[str, Any]] = []
    for entry in matrix:
        strongest = entry.get("strongestReferences", [])
        if not strongest:
            continue
        statuses = [
            reference_status
            for reference_status in entry.get("referenceStatuses", [])
            if reference_status.get("toolId") in strongest
        ]
        has_actionable_evidence = any(
            reference_status.get("status") == "implemented"
            and reference_status.get("directAnalog") is not False
            for reference_status in statuses
        )
        status = "confirmed" if has_actionable_evidence else "provisional"
        leaders.append(
            {
                "capability": entry["capability"],
                "sources": strongest,
                "status": status,
                "notes": "Generated from normalized feature-bag evidence."
            }
        )
    return leaders


def build_data_quality_items(bags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for bag in bags:
        evidence = bag.get("evidence", {})
        if not evidence.get("installedAndBenchmarked", False):
            items.append(
                {
                    "id": f"{bag['toolId']}_not_benchmarked",
                    "title": f"{bag.get('displayName', bag['toolId'])} not installed or benchmarked",
                    "sourceIds": [bag["toolId"]],
                    "notes": "This first slice uses normalized public/comparison evidence, not a live local benchmark."
                }
            )
        if bag.get("captureMethod") in {"primary_source_snapshot", "seed_from_comparison"}:
            items.append(
                {
                    "id": f"{bag['toolId']}_snapshot_evidence",
                    "title": f"{bag.get('displayName', bag['toolId'])} uses snapshot evidence",
                    "sourceIds": [bag["toolId"]],
                    "notes": "Treat claimed capabilities as review tasks unless backed by implemented evidence."
                }
            )
    return items


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    bags = load_feature_bags(args.bag)
    by_tool_id = {bag["toolId"]: bag for bag in bags}
    if args.xuunity_id not in by_tool_id:
        raise ValueError(f"Missing XUUnity/local bag: {args.xuunity_id}")

    xuunity_bag = by_tool_id[args.xuunity_id]
    reference_bags = [bag for bag in bags if bag["toolId"] != args.xuunity_id]
    if not reference_bags:
        raise ValueError("At least one reference feature bag is required")
    capabilities = capabilities_for_focus(bags, args.focus)
    if not capabilities:
        raise ValueError(f"No capabilities found for focus {args.focus!r}")

    matrix: list[dict[str, Any]] = []
    manual_reviews: list[dict[str, Any]] = []
    backlog_candidates: list[dict[str, Any]] = []
    non_actionable_claims: list[dict[str, Any]] = []
    xuunity_advantages: list[dict[str, Any]] = []

    for capability in capabilities:
        comparison, reviews, candidates, claims, advantages = classify_capability(
            capability,
            args.focus,
            xuunity_bag,
            reference_bags,
        )
        matrix.append(comparison)
        manual_reviews.extend(reviews)
        backlog_candidates.extend(candidates)
        non_actionable_claims.extend(claims)
        xuunity_advantages.extend(advantages)

    overall_leaders = [
        bag["toolId"]
        for bag in reference_bags
        if bag.get("tier") == "tier_1" and bag.get("candidateStrength") == "overall"
    ]

    return {
        "schemaVersion": "xuunity.reference-watch.comparison-report.v1",
        "focus": args.focus,
        "generatedAtUtc": generated_at(args),
        "xuunityToolId": args.xuunity_id,
        "xuunityCurrentState": args.xuunity_current_state,
        "inputs": [
            {
                "toolId": bag["toolId"],
                "displayName": bag.get("displayName", bag["toolId"]),
                "capturedAtUtc": bag.get("capturedAtUtc", ""),
                "captureMethod": bag.get("captureMethod", "unknown")
            }
            for bag in bags
        ],
        "overallLeaders": overall_leaders,
        "capabilityLeaders": build_capability_leaders(matrix),
        "comparedTools": [bag["toolId"] for bag in bags],
        "capabilityMatrix": matrix,
        "xuunityAdvantages": xuunity_advantages,
        "dataQuality": build_data_quality_items(bags),
        "staleSources": [],
        "manualReviewRequired": manual_reviews,
        "backlogCandidates": backlog_candidates,
        "nonActionableClaims": non_actionable_claims,
        "contradictedClaims": [
            report_item(
                f"{entry['capability']}_contradicted",
                f"Contradicted evidence for {entry['capability']}",
                entry["capability"],
                entry.get("strongestReferences", []),
                "Inspect this before using it for planning."
            )
            for entry in matrix
            if entry["outcome"] == "contradicted_evidence"
        ],
        "notes": args.notes
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare normalized AIReferenceWatch feature bags")
    parser.add_argument("--focus", required=True, help="Capability focus area, for example ui_primitives")
    parser.add_argument("--xuunity-id", default="xuunity_light_unity_mcp", help="Local/XUUnity feature bag id")
    parser.add_argument(
        "--xuunity-current-state",
        default="Derived from the normalized local feature bag.",
        help="Short current-state summary for the report"
    )
    parser.add_argument("--bag", action="append", required=True, help="Path to a JSON feature bag")
    parser.add_argument("--out", help="Write report to this path instead of stdout")
    parser.add_argument("--notes", default="", help="Optional report notes")
    parser.add_argument(
        "--generated-at-utc",
        help="Optional deterministic generatedAtUtc value for checked-in examples"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    report = build_report(args)
    write_json(report, Path(args.out) if args.out else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
