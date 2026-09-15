from __future__ import annotations

import importlib.util
import unittest
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[4] / "Operations" / "knowledge_extraction_eval.py"
SPEC = importlib.util.spec_from_file_location("knowledge_extraction_eval", SCRIPT)
assert SPEC and SPEC.loader
knowledge_extraction_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(knowledge_extraction_eval)


def bundle(run_date: str, fingerprint: str = "sha256:current") -> dict:
    return {
        "run_metadata": {
            "date": run_date,
            "run_type": "authoritative",
            "evidence_level": "human_scored",
            "approver": "reviewer",
            "approval_date": run_date,
            "workflow_version": "v1",
            "scope": "fixture",
            "protocol_fingerprint": fingerprint,
        }
    }


SUMMARY = {
    "cases_run": 1,
    "passed": 1,
    "warnings": 0,
    "failed": 0,
    "average_weighted_score": 5.0,
    "critical_omissions": 0,
    "wrong_critical_destinations": 0,
    "unsafe_shared_leaks": 0,
    "conflict_flattening": 0,
    "duplicate_proposals": 0,
    "blocking_regressions": False,
}


class KnowledgeExtractionFreshnessTests(unittest.TestCase):
    def test_init_defaults_to_pending_human_approval(self) -> None:
        parser = knowledge_extraction_eval.build_parser()

        args = parser.parse_args(["init", "--run-name", "candidate"])

        self.assertEqual("pending_human_approval", args.evidence_level)

    def test_current_requires_fresh_matching_fingerprint(self) -> None:
        result = knowledge_extraction_eval.build_health_summary(
            bundle(str(date.today())), SUMMARY, False,
            current_protocol_fingerprint="sha256:current",
        )
        self.assertEqual("current", result["status"])
        self.assertTrue(result["protocol_fingerprint_matches"])

    def test_age_and_fingerprint_drift_make_approved_run_stale(self) -> None:
        result = knowledge_extraction_eval.build_health_summary(
            bundle("2020-01-01", "sha256:old"), SUMMARY, True,
            current_protocol_fingerprint="sha256:current",
        )
        self.assertEqual("stale", result["status"])
        self.assertIn("age_limit_exceeded", result["freshness_reasons"])
        self.assertIn("protocol_fingerprint_changed", result["freshness_reasons"])
        self.assertEqual("legacy_presence_only", result["baseline_marker_role"])

    def test_conflict_flattening_is_a_blocking_regression(self) -> None:
        evaluation = {
            "critical_gate": {
                "critical_omissions": 0,
                "wrong_critical_destinations": 0,
                "unsafe_shared_leaks": 0,
                "conflict_flattening": 1,
            },
            "scores": {name: 5 for name in knowledge_extraction_eval.ALL_SCORES},
        }
        result = knowledge_extraction_eval.summarize_bundle(
            {"cases": [{"id": "conflict", "evaluation": evaluation}]}
        )

        self.assertEqual(1, result["conflict_flattening"])
        self.assertEqual(1, result["failed"])
        self.assertTrue(result["blocking_regressions"])


if __name__ == "__main__":
    unittest.main()
