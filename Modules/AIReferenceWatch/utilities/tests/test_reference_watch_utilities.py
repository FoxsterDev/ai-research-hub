#!/usr/bin/env python3
"""Regression tests for dependency-free AIReferenceWatch utilities."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


UTILITIES_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = UTILITIES_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))


def import_script(name: str):
    path = SCRIPTS_ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare_feature_bags = import_script("compare_feature_bags")
generate_reference_first_review = import_script("generate_reference_first_review")
run_seed_workflow = import_script("run_seed_workflow")
validate_examples = import_script("validate_examples")


def capability(
    status: str,
    focus: str,
    evidence_type: str = "docs_claim",
    direct_analog: bool | None = None,
) -> dict:
    detail = {
        "status": status,
        "confidence": "medium",
        "evidenceType": evidence_type,
        "focusAreas": [focus],
        "sourceFiles": [],
        "sourceLines": [],
        "extractionMethod": "test",
        "lastReviewedAtUtc": "2026-05-23T00:00:00Z",
        "reviewer": "test",
        "notes": ""
    }
    if direct_analog is not None:
        detail["directAnalog"] = direct_analog
    return detail


def feature_bag(tool_id: str, capabilities: dict, tier: str = "untracked") -> dict:
    return {
        "schemaVersion": "xuunity.reference-watch.feature-bag.v1",
        "toolId": tool_id,
        "displayName": tool_id,
        "sourceUrl": f"test:{tool_id}",
        "capturedAtUtc": "2026-05-23T00:00:00Z",
        "captureMethod": "manual_review",
        "tier": tier,
        "candidateStrength": "overall" if tier == "tier_1" else "unknown",
        "watchMode": "manual",
        "focusAreas": ["ui_primitives"],
        "capabilities": capabilities,
        "evidence": {
            "installedAndBenchmarked": True
        }
    }


class ReferenceWatchUtilityTests(unittest.TestCase):
    def write_bag(self, directory: Path, data: dict) -> str:
        path = directory / f"{data['toolId']}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def build_report(self, tmp: Path, reference_capability: dict) -> dict:
        local = feature_bag(
            "xuunity_light_unity_mcp",
            {
                "capability_probe_gating": capability(
                    "implemented",
                    "ui_primitives",
                    evidence_type="repo_verified",
                )
            },
        )
        reference = feature_bag(
            "reference_tool",
            {"generic_ui_read_primitives": reference_capability},
            tier="tier_1",
        )
        args = Namespace(
            focus="ui_primitives",
            xuunity_id="xuunity_light_unity_mcp",
            xuunity_current_state="test",
            bag=[self.write_bag(tmp, local), self.write_bag(tmp, reference)],
            out=None,
            notes="",
            generated_at_utc="2026-05-23T00:00:00Z",
        )
        return compare_feature_bags.build_report(args)

    def test_claimed_only_reference_does_not_create_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            report = self.build_report(Path(raw_tmp), capability("claimed", "ui_primitives"))

        self.assertEqual(report["backlogCandidates"], [])
        self.assertEqual(len(report["manualReviewRequired"]), 1)
        self.assertEqual(len(report["nonActionableClaims"]), 1)
        self.assertEqual(report["capabilityLeaders"][0]["status"], "provisional")

    def test_manual_review_claim_still_does_not_create_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            report = self.build_report(
                Path(raw_tmp),
                capability("claimed", "ui_primitives", evidence_type="manual_review"),
            )

        self.assertEqual(report["backlogCandidates"], [])
        self.assertEqual(len(report["manualReviewRequired"]), 1)
        self.assertEqual(len(report["nonActionableClaims"]), 1)
        self.assertEqual(report["capabilityLeaders"][0]["status"], "provisional")

    def test_implemented_reference_creates_actionable_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            report = self.build_report(
                Path(raw_tmp),
                capability(
                    "implemented",
                    "ui_primitives",
                    evidence_type="code_registry",
                    direct_analog=True,
                ),
            )

        self.assertEqual(len(report["backlogCandidates"]), 1)
        self.assertEqual(report["backlogCandidates"][0]["candidateId"], "generic_ui_read_primitives")
        self.assertEqual(report["manualReviewRequired"], [])
        self.assertEqual(report["capabilityLeaders"][0]["status"], "confirmed")

    def test_implemented_non_direct_reference_does_not_create_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            report = self.build_report(
                Path(raw_tmp),
                capability(
                    "implemented",
                    "ui_primitives",
                    evidence_type="code_registry",
                    direct_analog=False,
                ),
            )

        self.assertEqual(report["backlogCandidates"], [])
        self.assertEqual(len(report["manualReviewRequired"]), 1)
        self.assertEqual(report["manualReviewRequired"][0]["sourceIds"], ["reference_tool"])
        self.assertEqual(report["capabilityLeaders"], [])

    def test_contradicted_reference_does_not_create_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            report = self.build_report(
                Path(raw_tmp),
                capability(
                    "contradicted",
                    "ui_primitives",
                    evidence_type="manual_review",
                    direct_analog=False,
                ),
            )

        self.assertEqual(report["backlogCandidates"], [])
        self.assertEqual(report["manualReviewRequired"], [])
        self.assertEqual(len(report["contradictedClaims"]), 1)
        self.assertEqual(report["contradictedClaims"][0]["capability"], "generic_ui_read_primitives")
        self.assertEqual(report["capabilityLeaders"], [])

    def test_reference_first_review_uses_report_fields_and_fixed_timestamp(self) -> None:
        report_path = UTILITIES_ROOT / "examples" / "reports" / "ui_primitives.comparison.json"
        args = Namespace(
            report=str(report_path),
            feature_area=None,
            issue_theme=["selector ambiguity"],
            candidate_contract_option=None,
            borrow=["borrow taxonomy"],
            reject=["reject giant grouped tool"],
            differentiate=["keep evidence contracts"],
            recommended_direction="test direction",
            next_artifact="public_contract_design",
            reviewer="test",
            status="draft",
            notes="",
            out=None,
            generated_at_utc="2026-05-23T00:00:00Z",
        )

        review = generate_reference_first_review.build_review(args)

        self.assertEqual(review["featureArea"], "ui_primitives")
        self.assertEqual(review["generatedAtUtc"], "2026-05-23T00:00:00Z")
        self.assertEqual(review["overallLeaders"], ["unity_mcp_coplay", "unity_mcp_ivanmurzak"])

    def test_checked_in_examples_validate(self) -> None:
        count = validate_examples.validate_all(UTILITIES_ROOT)
        self.assertGreaterEqual(count, 15)

    def test_seed_workflow_generates_operational_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            out_root = Path(raw_tmp) / "ReferenceWatch"
            manifest = run_seed_workflow.run_workflow(
                Namespace(
                    utilities_root=str(UTILITIES_ROOT),
                    out_root=str(out_root),
                    generated_at_utc="2026-05-23T00:00:00Z",
                )
            )

            self.assertEqual(manifest["status"], "ready")
            self.assertEqual(len(manifest["normalizedFeatureBags"]), 4)
            self.assertEqual(len(manifest["comparisonReports"]), 3)
            self.assertEqual(len(manifest["referenceFirstReviews"]), 3)
            self.assertTrue((out_root / "workflow_manifest.json").exists())
            self.assertTrue((out_root / "reports" / "ui_primitives.comparison.json").exists())
            self.assertTrue((out_root / "reviews" / "transport.reference_first_review.json").exists())
            self.assertTrue((out_root / "reviews" / "build_profiles.reference_first_review.json").exists())


if __name__ == "__main__":
    unittest.main()
