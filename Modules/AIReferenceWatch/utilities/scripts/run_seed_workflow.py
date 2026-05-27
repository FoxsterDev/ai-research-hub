#!/usr/bin/env python3
"""Run the dependency-free AIReferenceWatch seed workflow end to end.

This workflow turns the checked-in seed feature bags into host-local normalized
bags, comparison reports, a reference-first review, and a workflow manifest.
It does not fetch the network and does not touch XUUnity MCP files.
"""

from __future__ import annotations

import argparse
import json
import shutil
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import compare_feature_bags
import generate_reference_first_review
import validate_examples


SCHEMA_VERSION = "xuunity.reference-watch.workflow-manifest.v1"
DEFAULT_GENERATED_AT_UTC = "2026-05-23T00:00:00Z"
LOCAL_TOOL_ID = "xuunity_light_unity_mcp"
FEATURE_BAG_IDS = [
    "xuunity_light_unity_mcp",
    "unity_mcp_coplay",
    "unity_mcp_ivanmurzak",
    "mcp_unity_codergamester",
]

FOCUS_RUNS = [
    {
        "focus": "ui_primitives",
        "xuunityCurrentState": (
            "Has reflection-gated Game View visual evidence and capability gating; "
            "lacks normalized generic UI hierarchy/query/action primitives in the "
            "current public comparison snapshot."
        ),
        "notes": (
            "Generated from manually code-reviewed feature bags with directAnalog "
            "metadata. Coplay get_visual_tree is direct evidence for a tree "
            "snapshot; direct query/exists/get_text/click/wait_for analogs are "
            "not confirmed."
        ),
    },
    {
        "focus": "transport",
        "xuunityCurrentState": (
            "Strong local same-host validation transport posture: capability "
            "probing, multi-client templates, same-host routing, final accounting, "
            "and low footprint."
        ),
        "notes": (
            "Generated from manually code-reviewed feature bags with directAnalog "
            "metadata. External MCP bridges are related evidence, but no reviewed "
            "reference directly matches XUUnity same-host routing plus "
            "final-accounting posture."
        ),
    },
    {
        "focus": "build_profiles",
        "xuunityCurrentState": (
            "XUUnity has repo-verified compile validation, active-target-free "
            "compile matrix support, build-config compile matrix support, and "
            "an EditMode validation lane; broad build execution is not a base "
            "goal."
        ),
        "notes": (
            "Generated from manually code-reviewed feature bags with directAnalog "
            "metadata. External build/test surfaces are decomposed from "
            "active-target-free compile matrix support."
        ),
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def module_root_from_utilities(utilities_root: Path) -> Path:
    return utilities_root.parents[0]


def parse_reference_source_ids(registry_path: Path) -> set[str]:
    source_ids: set[str] = set()
    if not registry_path.exists():
        raise FileNotFoundError(f"Reference source registry not found: {registry_path}")
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- id: "):
            source_ids.add(stripped.split(":", 1)[1].strip())
    if not source_ids:
        raise ValueError(f"No source ids found in {registry_path}")
    return source_ids


def seed_feature_bag_paths(utilities_root: Path) -> list[Path]:
    feature_bag_root = utilities_root / "examples" / "feature_bags"
    paths = [feature_bag_root / f"{tool_id}.json" for tool_id in FEATURE_BAG_IDS]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing seed feature bags: {', '.join(missing)}")
    return paths


def validate_seed_registry_alignment(utilities_root: Path, bag_paths: list[Path]) -> None:
    registry_path = module_root_from_utilities(utilities_root) / "reference_sources.yaml"
    source_ids = parse_reference_source_ids(registry_path)
    bags = compare_feature_bags.load_feature_bags([str(path) for path in bag_paths])
    missing = sorted(
        bag["toolId"]
        for bag in bags
        if bag["toolId"] != LOCAL_TOOL_ID and bag["toolId"] not in source_ids
    )
    if missing:
        raise ValueError(f"Seed bags are not present in reference_sources.yaml: {', '.join(missing)}")


def copy_normalized_bags(bag_paths: list[Path], normalized_root: Path) -> list[Path]:
    normalized_root.mkdir(parents=True, exist_ok=True)
    copied_paths: list[Path] = []
    for path in bag_paths:
        destination = normalized_root / path.name
        shutil.copyfile(path, destination)
        copied_paths.append(destination)
    return copied_paths


def generate_reports(
    bag_paths: list[Path],
    reports_root: Path,
    generated_at_utc: str,
) -> list[Path]:
    reports_root.mkdir(parents=True, exist_ok=True)
    report_paths: list[Path] = []
    for focus_run in FOCUS_RUNS:
        focus = focus_run["focus"]
        report = compare_feature_bags.build_report(
            Namespace(
                focus=focus,
                xuunity_id=LOCAL_TOOL_ID,
                xuunity_current_state=focus_run["xuunityCurrentState"],
                bag=[str(path) for path in bag_paths],
                out=None,
                notes=focus_run["notes"],
                generated_at_utc=generated_at_utc,
            )
        )
        report_path = reports_root / f"{focus}.comparison.json"
        write_json(report, report_path)
        report_paths.append(report_path)
    return report_paths


def generate_review(
    reports_root: Path,
    reviews_root: Path,
    generated_at_utc: str,
    focus: str,
    args: Namespace,
) -> Path:
    reviews_root.mkdir(parents=True, exist_ok=True)
    report_path = reports_root / f"{focus}.comparison.json"
    args.report = str(report_path)
    args.generated_at_utc = generated_at_utc
    review = generate_reference_first_review.build_review(args)
    review_path = reviews_root / f"{focus}.reference_first_review.json"
    write_json(review, review_path)
    return review_path


def generate_reference_reviews(reports_root: Path, reviews_root: Path, generated_at_utc: str) -> list[Path]:
    review_paths: list[Path] = []
    review_paths.append(generate_review(
        reports_root,
        reviews_root,
        generated_at_utc,
        "ui_primitives",
        Namespace(
            report="",
            feature_area=None,
            issue_theme=[
                "selector ambiguity: Coplay proves visual tree serialization, not a selector contract",
                "action semantics gap: no confirmed click or semantic wait_for analog in reviewed references",
                "visual evidence must stay separate from semantic UI state",
            ],
            candidate_contract_option=[
                "First XUUnity slice: read-only UI tree snapshot plus narrow query/exists/get_text derived from the tree",
                "Defer click and wait_for until selector stability, playmode lifecycle, and proof-class rules are designed locally",
            ],
            borrow=[
                (
                    "Borrow Coplay's get_visual_tree idea: target a UIDocument, "
                    "return type/name/classes/style/text/children, and make "
                    "depth/truncation explicit."
                ),
                (
                    "Borrow the taxonomy split between UI assets, UIDocument "
                    "attachment, visual-tree inspection, rendering, and live "
                    "element mutation."
                ),
            ],
            reject=[
                "Do not copy a giant manage_ui-style grouped surface as the first public XUUnity contract.",
                (
                    "Do not treat Coplay manage_ui as proof that "
                    "query/exists/get_text/click/wait_for primitives exist; "
                    "the code review contradicted that broad inference."
                ),
                "Do not bring live element mutation into the first XUUnity UI primitives slice.",
            ],
            differentiate=[
                (
                    "Keep XUUnity reference-first but evidence-oriented: narrow "
                    "typed read commands, capability gating, and explicit "
                    "proof-class downgrades."
                ),
                (
                    "Design query/exists/get_text as XUUnity-specific semantics "
                    "on top of a tree snapshot; treat click/wait_for as later "
                    "local design work, not copied reference behavior."
                ),
            ],
            recommended_direction=(
                "Use Coplay as evidence for a read-only visual-tree snapshot "
                "contract, not as a direct primitive API to copy. For XUUnity "
                "design, start with capability-gated tree/query/exists/get_text "
                "semantics, keep screenshots as visual evidence, and defer "
                "click/wait_for/action primitives until a stable selector and "
                "lifecycle model exists."
            ),
            next_artifact="public_contract_design",
            reviewer="ai_reference_watch",
            status="ready_for_design_review",
            notes=(
                "Manual external evidence review completed on 2026-05-23; no files "
                "under Operations/XUUnityLightUnityMcp were modified."
            ),
            out=None,
        )
    ))
    review_paths.append(generate_review(
        reports_root,
        reviews_root,
        generated_at_utc,
        "transport",
        Namespace(
            report="",
            feature_area=None,
            issue_theme=[
                "generic MCP bridge is not the same as XUUnity same-host routing plus final accounting",
                "client compatibility lists remain docs claims unless setup templates or registry evidence are reviewed",
                "custom tool extensibility is implemented in references but is not a current XUUnity base transport goal",
            ],
            candidate_contract_option=[
                (
                    "No new XUUnity transport backlog from current references; "
                    "keep implemented same-host routing, capability probes, and "
                    "final accounting as local advantages"
                ),
                "Use reference bridge registries only as setup/documentation taxonomy input",
            ],
            borrow=[
                (
                    "Borrow clear registry/tool-list discoverability patterns "
                    "from IvanMurzak and CoderGamester where they improve "
                    "operator understanding."
                ),
                (
                    "Borrow client setup taxonomy only after it is source-verified, "
                    "not from README positioning alone."
                ),
            ],
            reject=[
                "Do not treat generic MCP or IDE bridge support as a direct analog to XUUnity same-host routing.",
                "Do not add custom tool extensibility to the base transport contract from this evidence.",
                "Do not convert docs-only multi-client claims into backlog.",
            ],
            differentiate=[
                (
                    "Keep XUUnity transport small, same-host, capability-gated, "
                    "easy to disable, and explicit about request final accounting."
                ),
                (
                    "Use directAnalog=false for broad bridge patterns that are "
                    "useful context but not public-contract gaps."
                ),
            ],
            recommended_direction=(
                "Do not open transport backlog from the current external evidence. "
                "Preserve XUUnity's same-host routing, capability probe gating, "
                "low footprint, and final-accounting posture; use external "
                "registries only as documentation/setup input until a direct "
                "analog is proven."
            ),
            next_artifact="transport_design_watch",
            reviewer="ai_reference_watch",
            status="ready_for_design_review",
            notes=(
                "Transport report upgraded with directAnalog metadata on 2026-05-23. "
                "No files under Operations/XUUnityLightUnityMcp were modified."
            ),
            out=None,
        )
    ))
    review_paths.append(generate_review(
        reports_root,
        reviews_root,
        generated_at_utc,
        "build_profiles",
        Namespace(
            report="",
            feature_area=None,
            issue_theme=[
                "implemented build runner surfaces are not proof of active-target-free compile matrix support",
                "test execution surfaces need separate comparison from compile validation and build profiles",
                "broad build tools are useful taxonomy input but not automatically XUUnity base goals",
            ],
            candidate_contract_option=[
                "Keep XUUnity compile validation and active-target-free compile matrix as the core build_profiles direction",
                "Treat broad manage_build-style runners as optional future design input, not current backlog",
            ],
            borrow=[
                "Borrow Coplay manage_build taxonomy for naming build/profile/status/scenes concerns when useful.",
                (
                    "Borrow IvanMurzak tests-run filtering/log-output ideas as "
                    "comparison input for future test reporting polish."
                ),
            ],
            reject=[
                "Do not treat manage_build as direct evidence for compile_matrix_without_active_switch.",
                "Do not add a broad build runner to XUUnity's base module from this evidence.",
                "Do not merge test execution, build execution, and compile matrix into one capability.",
            ],
            differentiate=[
                (
                    "Keep XUUnity validation-first: compile checks, compile "
                    "matrices, build-config matrices, and narrow test execution."
                ),
                (
                    "Use directAnalog metadata to separate direct test-run "
                    "references from non-direct broad build surfaces."
                ),
            ],
            recommended_direction=(
                "No build_profiles backlog is opened from the current external "
                "evidence. Keep XUUnity's active-target-free compile matrix as "
                "an advantage; use Coplay/Ivan/CoderGamester build and test "
                "tools as taxonomy and future polish references only after "
                "direct capability decomposition."
            ),
            next_artifact="build_profiles_design_watch",
            reviewer="ai_reference_watch",
            status="ready_for_design_review",
            notes=(
                "Build profiles report upgraded with directAnalog metadata on 2026-05-23. "
                "No files under Operations/XUUnityLightUnityMcp were modified."
            ),
            out=None,
        )
    ))
    return review_paths


def copy_issue_watch_example(utilities_root: Path, issue_watch_root: Path) -> Path:
    issue_watch_root.mkdir(parents=True, exist_ok=True)
    source_path = utilities_root / "examples" / "issue_watch_summary.example.json"
    destination = issue_watch_root / "issue_watch_summary.seed.json"
    shutil.copyfile(source_path, destination)
    return destination


def build_manifest(
    out_root: Path,
    generated_at_utc: str,
    normalized_paths: list[Path],
    report_paths: list[Path],
    review_paths: list[Path],
    issue_watch_path: Path,
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAtUtc": generated_at_utc,
        "workflow": "seed_reference_watch",
        "status": "ready",
        "outputRoot": str(out_root),
        "normalizedFeatureBags": [str(path) for path in normalized_paths],
        "comparisonReports": [str(path) for path in report_paths],
        "referenceFirstReviews": [str(path) for path in review_paths],
        "issueWatchSummaries": [str(issue_watch_path)],
        "checks": [
            "validated checked-in examples",
            "validated reference_sources.yaml alignment for seed bags",
            "generated focus reports for ui_primitives, transport, and build_profiles",
            "generated reference-first reviews for ui_primitives, transport, and build_profiles",
        ],
        "nextActions": [
            "Turn ui_visual_tree_read into a public_contract_design draft for read-only tree/query/exists/get_text.",
            "Keep click and wait_for deferred until selector stability and playmode lifecycle fixtures exist.",
            "Run live benchmarks against Tier 1 references before treating performance or reliability claims as implemented.",
        ],
    }


def run_workflow(args: argparse.Namespace) -> dict[str, Any]:
    utilities_root = Path(args.utilities_root).resolve()
    out_root = Path(args.out_root).resolve()
    generated_at_utc = args.generated_at_utc or utc_now()

    validate_examples.validate_all(utilities_root)
    bag_paths = seed_feature_bag_paths(utilities_root)
    validate_seed_registry_alignment(utilities_root, bag_paths)

    normalized_paths = copy_normalized_bags(bag_paths, out_root / "normalized")
    report_paths = generate_reports(normalized_paths, out_root / "reports", generated_at_utc)
    review_paths = generate_reference_reviews(out_root / "reports", out_root / "reviews", generated_at_utc)
    issue_watch_path = copy_issue_watch_example(utilities_root, out_root / "issue_watch")

    manifest = build_manifest(
        out_root,
        generated_at_utc,
        normalized_paths,
        report_paths,
        review_paths,
        issue_watch_path,
    )
    manifest_path = out_root / "workflow_manifest.json"
    write_json(manifest, manifest_path)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    utilities_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run the AIReferenceWatch seed workflow")
    parser.add_argument(
        "--utilities-root",
        default=str(utilities_root),
        help="AIReferenceWatch utilities root"
    )
    parser.add_argument(
        "--out-root",
        default="AIOutput/Operations/ReferenceWatch",
        help="Host-local output root for normalized bags, reports, reviews, and manifest"
    )
    parser.add_argument(
        "--generated-at-utc",
        default=DEFAULT_GENERATED_AT_UTC,
        help="Deterministic generatedAtUtc value; pass an empty string for current time"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.generated_at_utc == "":
        args.generated_at_utc = None
    manifest = run_workflow(args)
    print(json.dumps(manifest, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
