from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
GATE = SCRIPTS_DIR / "routing_gate_check.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "routing_fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))
import routing_gate_check  # noqa: E402


FIXTURE_FILES = sorted(FIXTURE_DIR.glob("*.json"))


class RoutingFixtureStructureTests(unittest.TestCase):
    def test_fixtures_present(self) -> None:
        self.assertTrue(FIXTURE_FILES, "no routing fixtures found in routing_fixtures/")

    def test_fixture_structure(self) -> None:
        for fixture in FIXTURE_FILES:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            with self.subTest(fixture=fixture.name):
                for key in ("id", "title", "signal", "scenario", "expected", "contracts"):
                    self.assertIn(key, data)
                for key in ("required_root_cause_chain", "allowed_patch_shapes"):
                    self.assertIn(key, data["expected"])
                self.assertTrue(data["contracts"], "fixture has no example contracts")
                for case in data["contracts"]:
                    self.assertIn(case.get("expect"), ("pass", "fail"))
                    self.assertIn("contract", case)


class RoutingGateBehaviorTests(unittest.TestCase):
    def test_gate_matches_fixture_expectations(self) -> None:
        for fixture in FIXTURE_FILES:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            for index, case in enumerate(data["contracts"]):
                with self.subTest(fixture=fixture.name, case=index, kind=case.get("kind")):
                    fired = sorted(v.rule for v in routing_gate_check.check_contract(case["contract"]))
                    if case["expect"] == "pass":
                        self.assertEqual(fired, [], f"expected gate to pass, got violations {fired}")
                    else:
                        self.assertTrue(fired, "expected gate to fail but it passed")
                        if "expected_violations" in case:
                            self.assertEqual(fired, sorted(case["expected_violations"]))

    def test_empty_contract_is_inert(self) -> None:
        self.assertEqual(routing_gate_check.check_contract({}), [])

    def test_unknown_bug_family_skips_chain_rule(self) -> None:
        fired = sorted(
            v.rule
            for v in routing_gate_check.check_contract(
                {"bug_family": "some_unknown_family", "root_cause_chain_checked": ["symptom"]}
            )
        )
        self.assertNotIn("incomplete_root_cause_chain", fired)


class RoutingGateCliTests(unittest.TestCase):
    def _run(self, contract: dict) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(contract, handle)
            path = handle.name
        try:
            return subprocess.run(
                [sys.executable, str(GATE), "--contract", path],
                capture_output=True,
                text=True,
            )
        finally:
            os.unlink(path)

    def test_pass_exits_zero(self) -> None:
        good = json.loads((FIXTURE_DIR / "popup_runtime_content_warning.json").read_text(encoding="utf-8"))
        good_contract = next(c["contract"] for c in good["contracts"] if c["kind"] == "good")
        result = self._run(good_contract)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_fail_exits_nonzero(self) -> None:
        data = json.loads((FIXTURE_DIR / "popup_runtime_content_warning.json").read_text(encoding="utf-8"))
        bad_contract = next(c["contract"] for c in data["contracts"] if c["kind"] == "bad")
        result = self._run(bad_contract)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)

    def test_invalid_json_is_usage_error(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{not valid json")
            path = handle.name
        try:
            result = subprocess.run(
                [sys.executable, str(GATE), "--contract", path],
                capture_output=True,
                text=True,
            )
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
