from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

OPERATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION))

from model_fitness import experiment_journal, records, scoring, suite
from test_experiment import cohort, manifest_for
from test_scoring import fixture_doc
from test_suite import attempt, eligible_score, suite_doc


class ComparisonTests(unittest.TestCase):
    def test_distinct_fixture_keys_are_compared_against_their_own_preregistration(self):
        fixtures = [fixture_doc(), fixture_doc(fixture_id="f2-demo")]
        specs = [{"fixture_id": f["fixture_id"], "fixture_sha256": scoring.fixture_sha256(f),
                  "required": True, "stratum": "core", "safety_critical": False} for f in fixtures]
        definition = suite_doc(fixtures=specs, attempts_per_fixture=3)
        keys = {fixtures[0]["fixture_id"]: "b" * 64, fixtures[1]["fixture_id"]: "c" * 64}
        rows = [attempt(i, eligible_score(f, run_id=f["fixture_id"] + str(i), strict_profile_key=keys[f["fixture_id"]]), fixture_id=f["fixture_id"])
                for i in range(3) for f in fixtures]
        result = suite.aggregate_suite(definition, rows, strict_profile_key=suite.suite_profile_key(keys), fixture_profile_keys=keys)
        self.assertEqual("exact", result["comparison_status"])
        wrong = dict(keys)
        wrong[fixtures[1]["fixture_id"]] = "e" * 64
        mixed = suite.aggregate_suite(definition, rows, strict_profile_key=suite.suite_profile_key(wrong), fixture_profile_keys=wrong)
        self.assertEqual("mixed", mixed["comparison_status"])
        with self.assertRaisesRegex(ValueError, "does not bind"):
            suite.aggregate_suite(definition, rows, strict_profile_key="d" * 64, fixture_profile_keys=keys)

    def test_experiment_reprocessing_does_not_spend_alpha_again(self):
        control = cohort(3, gate_decision="fail")
        treatment = cohort(3)
        manifest = manifest_for(control, treatment, attempts_per_cell=3)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kwargs = dict(root=root, alpha_charge=0.05, control_ref="control.json", treatment_ref="treatment.json")
            first = experiment_journal.evaluate(manifest, control, treatment, **kwargs)
            self.assertEqual("inconclusive", first["status"])
            self.assertEqual(first, experiment_journal.evaluate(manifest, control, treatment, **kwargs))
            self.assertEqual(1, len(list(root.glob("*.reservation.json"))))
            other = deepcopy(manifest)
            other["experiment_id"] = "experiment-2"
            other["manifest_hash"] = None
            with self.assertRaisesRegex(ValueError, "alpha_exhausted"):
                experiment_journal.evaluate(other, control, treatment, **kwargs)
            result_path = root / (manifest["experiment_id"] + ".result.json")
            modified = records.read(result_path)
            modified["status"] = "accepted"
            records.write(result_path, modified)
            with self.assertRaisesRegex(ValueError, "experiment_result_changed"):
                experiment_journal.evaluate(manifest, control, treatment, **kwargs)


if __name__ == "__main__":
    unittest.main()
