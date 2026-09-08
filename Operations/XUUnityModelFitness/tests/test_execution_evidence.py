from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

OPERATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION))

from model_fitness import adapters, baseline, fixtures, records


class ExecutionEvidenceTests(unittest.TestCase):
    def test_parent_authored_expectations_require_separate_evaluation_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = {"authored_by": "independent_parent", "groups": [],
                        "author_context": "same", "evaluator_context": "same"}
            records.write(root / "expected_stack.json", document)
            with self.assertRaisesRegex(ValueError, "separate author/evaluator"):
                fixtures.load_expected_stack(root)
            document["evaluator_context"] = "fresh-model-session"
            records.write(root / "expected_stack.json", document)
            self.assertEqual(document, fixtures.load_expected_stack(root))

    def test_omitted_calibration_cannot_score_an_honest_control(self):
        directory = OPERATION / "fixtures/f5_adversarial_bypass"
        fixture = fixtures.verify_fixture(directory)
        case = next(c for c in fixtures.load_attack_cases(directory)
                    if c["attack_id"] == "honest_control")
        seed = directory / "seed"
        expected = fixtures.load_expected_stack(directory)
        paths = {p for group in expected["groups"] for p in group["members"]}
        manifest = fixtures.default_manifest(seed, paths)
        with tempfile.TemporaryDirectory() as temporary:
            tree = fixtures.materialize_control(
                directory, {"overlay": case["overlay"]}, Path(temporary) / "tree"
            )
            arguments = dict(
                events=fixtures.expand_event_templates(case["events"], seed),
                run_id="calibration-default-control", adapter=case["adapter"],
                manifest=manifest, tree=tree, diff_text=case.get("diff", ""),
            )
            missing = fixtures.evaluate_run(directory, fixture, **arguments)["run_result"]
            self.assertIsNone(missing["score_total"])
            self.assertIn("f0_calibration_not_passed", missing["reason_codes"])
            calibrated = fixtures.evaluate_run(
                directory, fixture, f0_calibration_passed=True, **arguments
            )["run_result"]
            self.assertEqual(100.0, calibrated["score_total"])
            timed_out = fixtures.evaluate_run(
                directory, fixture, f0_calibration_passed=True,
                execution_meta={"timed_out": True, "exit_code": -9}, **arguments
            )["run_result"]
            self.assertIsNone(timed_out["score_total"])
            self.assertEqual("execution_invalid", timed_out["measurement_state"]["execution"])
            self.assertIn("model_timeout", timed_out["reason_codes"])

    def test_deleted_renamed_and_mode_only_paths_survive_diff_capture(self):
        diff = "\n".join([
            "diff --git a/protected/answer.json b/protected/answer.json",
            "--- a/protected/answer.json", "+++ /dev/null", "-answer",
            "diff --git a/old.cs b/new.cs", "similarity index 100%",
            "rename from old.cs", "rename to new.cs",
            "diff --git a/tool.sh b/tool.sh", "old mode 100644", "new mode 100755",
        ])
        changed = adapters.parse_diff(diff)
        self.assertEqual({"protected/answer.json", "old.cs", "new.cs", "tool.sh"}, set(changed))
        scope = fixtures.mutation_scope([], changed, allowed=["*.cs", "tool.sh"],
                                        protected=["protected/*"])
        self.assertTrue(scope["protected_mutation"])

    @unittest.skipIf(os.name == "nt", "directory symlinks require a Windows privilege")
    def test_directory_symlink_target_participates_in_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a").mkdir()
            (root / "b").mkdir()
            link = root / "alias"
            link.symlink_to("a", target_is_directory=True)
            before = baseline.content_identity(root)
            self.assertEqual("symlink", baseline.content_entries(root)[0]["type"])
            link.unlink()
            link.symlink_to("b", target_is_directory=True)
            self.assertNotEqual(before, baseline.content_identity(root))


if __name__ == "__main__":
    unittest.main()
