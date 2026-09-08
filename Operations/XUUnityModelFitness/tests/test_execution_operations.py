from pathlib import Path
import sys
import tempfile
import unittest

OPERATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION))
from model_fitness import f6, operations, records


class OperationsTests(unittest.TestCase):
    def test_exposure_is_charged_before_evaluation_and_rotation_does_not_revive_old_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = b"test-key-material-only" * 2
            f6.register_holdout(root, holdout_id="rotation-1", fixture_hash="a" * 64,
                                producer_contexts=["foreground", "background"], max_exposures=1)
            f6.reserve_exposure(root, holdout_id="rotation-1", attempt_id="run-1", schedule_hash="b" * 64)
            with self.assertRaisesRegex(ValueError, "rotate_required"):
                f6.reserve_exposure(root, holdout_id="rotation-1", attempt_id="run-2", schedule_hash="b" * 64)
            with self.assertRaisesRegex(ValueError, "new_fixture_identity"):
                f6.register_holdout(root, holdout_id="relabelled-old-holdout", fixture_hash="a" * 64,
                                    producer_contexts=["foreground", "background"], max_exposures=1)
            artifact = f6.build_artifact(key, evidence_ref="protected/result.json", issuer_key_id="test",
                                         holdout_ref="rotation-1", suite_id="test-suite", suite_sha256="c" * 64,
                                         fixture_id="f6-test", fixture_sha256="a" * 64, strict_profile_key="d" * 64,
                                         attempts=[{"attempt_id": "run-1"}])
            f6.complete_exposure(root, holdout_id="rotation-1", attempt_id="run-1", artifact=artifact,
                                 verification_keys={"test": key})
            with self.assertRaises(FileExistsError):
                f6.complete_exposure(root, holdout_id="rotation-1", attempt_id="run-1", artifact=artifact,
                                     verification_keys={"test": key})
            f6.register_holdout(root, holdout_id="rotation-2", fixture_hash="e" * 64,
                                producer_contexts=["foreground", "background"], max_exposures=1)
            f6.reserve_exposure(root, holdout_id="rotation-2", attempt_id="run-2", schedule_hash="f" * 64)
            with self.assertRaisesRegex(ValueError, "binding_mismatch"):
                f6.complete_exposure(root, holdout_id="rotation-2", attempt_id="run-2", artifact=artifact,
                                     verification_keys={"test": key})

    def test_stale_smoke_hook_preserves_baseline_and_rollout_stays_disabled_without_live_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.json"
            records.write(baseline, {"protocol_content_hash": "a" * 64, "score": None})
            before = baseline.read_bytes()
            pending = operations.protocol_changed(root, change_id="change-1", before="a" * 64, after="b" * 64,
                                                  baseline_refs=[baseline], smoke_fixture_ids=["incident-fixture"])
            self.assertEqual("pending", pending["status"])
            self.assertEqual("stale", pending["affected_baselines"][0]["status"])
            self.assertEqual(before, baseline.read_bytes())
            with self.assertRaises(FileExistsError):
                operations.protocol_changed(root, change_id="change-1", before="a" * 64, after="b" * 64,
                                            baseline_refs=[baseline], smoke_fixture_ids=["incident-fixture"])
            self.assertEqual("observe", operations.set_rollout(root, "observe")["mode"])
            for mode in ("advisory", "blocking"):
                with self.assertRaisesRegex(ValueError, "live_conformance"):
                    operations.set_rollout(root, mode)
            self.assertEqual("off", operations.set_rollout(root, "off")["mode"])


if __name__ == "__main__":
    unittest.main()
