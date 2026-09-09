from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "workspace_cleanup.py"
SPEC = importlib.util.spec_from_file_location("workspace_cleanup", MODULE_PATH)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cleanup
SPEC.loader.exec_module(cleanup)


class WorkspaceCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.now = time.time()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _old(self, path: Path, hours: int = 200) -> None:
        stamp = self.now - hours * 3600
        os.utime(path, (stamp, stamp))

    def test_dry_run_finds_but_preserves_unity_library(self) -> None:
        project = self.root / "Game"
        (project / "ProjectSettings").mkdir(parents=True)
        (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000")
        (project / "Library").mkdir()
        (project / "Library" / "cache.bin").write_bytes(b"cache")
        config = {"unity": {"remove_libraries": True, "scan_roots": [str(self.root)]}}
        report = cleanup.run_cleanup(config, apply=False, now=self.now, commands=[])
        self.assertEqual(report["entries"][0]["state"], "candidate")
        self.assertTrue((project / "Library").exists())

    def test_apply_deletes_library_but_preserves_project(self) -> None:
        project = self.root / "Game"
        (project / "ProjectSettings").mkdir(parents=True)
        (project / "ProjectSettings" / "ProjectVersion.txt").write_text("version")
        (project / "Assets").mkdir()
        (project / "Library").mkdir()
        config = {"unity": {"remove_libraries": True, "scan_roots": [str(self.root)]}}
        report = cleanup.run_cleanup(config, apply=True, now=self.now, commands=[])
        self.assertEqual(report["entries"][0]["state"], "deleted")
        self.assertFalse((project / "Library").exists())
        self.assertTrue((project / "Assets").exists())

    def test_unity_process_blocks_library_deletion(self) -> None:
        project = self.root / "Game"
        (project / "ProjectSettings").mkdir(parents=True)
        (project / "ProjectSettings" / "ProjectVersion.txt").write_text("version")
        (project / "Library").mkdir()
        config = {"unity": {"remove_libraries": True, "scan_roots": [str(self.root)]}}
        report = cleanup.run_cleanup(
            config,
            apply=True,
            now=self.now,
            commands=["/Applications/Unity/Hub/Editor/6000/Unity.app/Contents/MacOS/Unity -projectPath x"],
        )
        self.assertEqual(report["entries"][0]["state"], "skipped_active_process")
        self.assertTrue((project / "Library").exists())

    def test_derived_data_children_are_deleted_without_removing_root(self) -> None:
        derived = self.root / "DerivedData"
        (derived / "One").mkdir(parents=True)
        (derived / "Two").mkdir()
        config = {"xcode": {"remove_derived_data": True, "derived_data_root": str(derived)}}
        report = cleanup.run_cleanup(config, apply=True, now=self.now, commands=[])
        self.assertEqual({entry["state"] for entry in report["entries"]}, {"deleted"})
        self.assertTrue(derived.is_dir())
        self.assertEqual(list(derived.iterdir()), [])

    def test_temp_prefix_age_and_protection(self) -> None:
        temp_root = self.root / "tmp"
        temp_root.mkdir()
        old = temp_root / "xuunity-old"
        new = temp_root / "xuunity-new"
        protected = temp_root / "xuunity-service"
        unrelated = temp_root / "notes"
        for path in (old, new, protected, unrelated):
            path.mkdir()
        self._old(old)
        self._old(protected)
        self._old(unrelated)
        config = {
            "temporary": {
                "root": str(temp_root),
                "prefixes": ["xuunity-"],
                "minimum_age_hours": 72,
                "protected_names": ["xuunity-service"],
            }
        }
        report = cleanup.run_cleanup(config, apply=True, now=self.now, commands=[])
        self.assertEqual([Path(entry["path"]).name for entry in report["entries"]], ["xuunity-old"])
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())
        self.assertTrue(protected.exists())
        self.assertTrue(unrelated.exists())

    def test_live_process_reference_blocks_temp_candidate(self) -> None:
        temp_root = self.root / "tmp"
        candidate = temp_root / "xuunity-live"
        candidate.mkdir(parents=True)
        self._old(candidate)
        config = {"temporary": {"root": str(temp_root), "prefixes": ["xuunity-"], "minimum_age_hours": 1}}
        report = cleanup.run_cleanup(config, apply=True, now=self.now, commands=[f"tool --root {candidate}"])
        self.assertEqual(report["entries"][0]["state"], "skipped_live_process_reference")
        self.assertTrue(candidate.exists())

    def test_model_fitness_prunes_named_tree_only(self) -> None:
        evidence = self.root / "evidence"
        heavy = evidence / "run" / "compile-tree"
        receipt = evidence / "run" / "receipt.json"
        heavy.mkdir(parents=True)
        (heavy / "cache").write_text("x")
        receipt.write_text("{}")
        self._old(heavy)
        config = {"model_fitness": {"roots": [str(evidence)], "minimum_age_hours": 1}}
        cleanup.run_cleanup(config, apply=True, now=self.now, commands=[])
        self.assertFalse(heavy.exists())
        self.assertTrue(receipt.exists())

    def test_tracked_scratch_child_is_preserved(self) -> None:
        repository = self.root / "repo"
        scratch = repository / "release" / "work"
        child = scratch / "tracked.txt"
        scratch.mkdir(parents=True)
        child.write_text("keep")
        subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repository), "add", str(child)], check=True)
        self._old(child)
        config = {"scratch": {"roots": [{"path": str(scratch), "minimum_age_hours": 1}]}}
        report = cleanup.run_cleanup(config, apply=True, now=self.now, commands=[])
        self.assertEqual(report["entries"][0]["state"], "skipped_tracked_path")
        self.assertTrue(child.exists())

    def test_simulator_apply_runs_shutdown_then_erase(self) -> None:
        calls = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

        report = cleanup.run_cleanup(
            {"simulator": {"mode": "erase_all"}},
            apply=True,
            now=self.now,
            commands=[],
            simulator_runner=runner,
        )
        self.assertEqual(calls, [["xcrun", "simctl", "shutdown", "all"], ["xcrun", "simctl", "erase", "all"]])
        self.assertEqual(report["simulator"]["state"], "completed")

    def test_simulator_dry_run_does_not_execute(self) -> None:
        def runner(*_args, **_kwargs):
            self.fail("runner must not be called")

        report = cleanup.run_cleanup(
            {"simulator": {"mode": "erase_all"}},
            apply=False,
            now=self.now,
            commands=[],
            simulator_runner=runner,
        )
        self.assertEqual(report["simulator"]["state"], "candidate")

    def test_config_requires_schema(self) -> None:
        path = self.root / "config.json"
        path.write_text(json.dumps({"schema_version": 2}))
        with self.assertRaises(ValueError):
            cleanup._load_config(path)


if __name__ == "__main__":
    unittest.main()
