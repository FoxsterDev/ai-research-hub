"""Owned process/evaluator tests. Scripted CLI output is never live evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPERATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION))

from model_fitness import baseline, calibration, causes, executor, processes, profiles, records, reporting, schedule
import xuunity_canonical as xc

SCRIPT = r'''
import json, pathlib, sys
if sys.argv[1:] == ["--version"]:
    print("scripted-test-cli 1.0")
    sys.exit(0)
if sys.argv[1:] == ["login", "status"]:
    print("Logged in using ChatGPT")
    sys.exit(0)
sys.stdin.read()
root = pathlib.Path(sys.argv[sys.argv.index("-C") + 1])
canary = (root / "Probe.cs").exists()
guidance = "guidance.md" if canary else "Modules/Stack/tasks/start_here.md"
target = "Probe.cs" if canary else "src/BuildInfo.cs"
def event(value):
    print(json.dumps(value), flush=True)
event({"type":"thread.started", "model":"scripted-model"})
command = ["bash", "-c", "cat " + guidance]
event({"type":"item.started", "item":{"id":"r1", "type":"command_execution", "command":command}})
event({"type":"item.completed", "item":{"id":"r1", "type":"command_execution", "command":command,
    "exit_code":0, "aggregated_output":(root/guidance).read_text()}})
path = root / target
path.write_text(path.read_text().replace("Value = 0", "Value = 7") if canary else path.read_text().replace("1.2.2", "1.2.3"))
event({"type":"item.completed", "item":{"id":"w1", "type":"file_change", "status":"completed", "changes":[{"path":target}]}})
event({"type":"turn.completed", "usage":{"input_tokens":20, "output_tokens":10}})
'''


def row(identity: str, *, order: int = 0, kind: str = "fixture", input_hash: str = "b" * 64) -> dict:
    return {"attempt_id": identity, "order": order, "kind": kind, "timeout_seconds": 30,
            "profile_record_hash": "a" * 64, "input_hash": input_hash,
            "seed_identity": "d" * 64, "fixture_id": "test-fixture", "replicate": 1,
            "block_id": "test-block"}


class JournalTests(unittest.TestCase):
    def test_workspace_cannot_inherit_parent_git_or_automatic_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profiles.verify_workspace_boundary(root / "fresh" / "attempt")
            for marker in (".git", "AGENTS.md", "CLAUDE.md", ".agents/skills"):
                path = root / marker
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("parent context must not enter the fixture")
                with self.assertRaisesRegex(ValueError, "workspace_inherits_parent"):
                    profiles.verify_workspace_boundary(root / "fresh" / "attempt")
                path.unlink()

    @unittest.skipUnless(os.name == "posix", "PID liveness recovery is explicitly unavailable on Windows")
    def test_dead_parent_before_input_publication_is_accounted_without_relaunch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = schedule.build([row("one"), row("two", order=1)], schedule_id="recovery",
                                  journal_root=root / "journal", max_wall_seconds=100)
            records.write(root / "plan.json", plan)
            code = ("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                    "from model_fitness import records,schedule; "
                    "schedule.claim(records.read(Path(sys.argv[2])), 'one', profile_hash='a'*64, input_hash='b'*64)")
            subprocess.run([sys.executable, "-c", code, str(OPERATION), str(root / "plan.json")], check=True)
            result = executor.recover(plan, "one")
            self.assertFalse(result["model_relaunched"])
            self.assertIsNone(result["score_total"])
            self.assertEqual(["finished", "censored"], [r["status"] for r in schedule.accounting(plan)])
            self.assertEqual(2, reporting.diagnostic_report(plan)["scheduled"])
            evidence = root / "journal/one"
            # Reproduce the crash window after finished.json, before lock removal.
            records.write(root / "journal/launch.lock", {"attempt_id": "one"}, exclusive=True)
            executor.recover(plan, "one")
            self.assertFalse((root / "journal/launch.lock").exists())
            records.write(evidence / "process-intent.json", {"owner_pid": 999999})
            with self.assertRaisesRegex(ValueError, "process_identity_unavailable"):
                schedule.assert_abandoned(plan, "one")

    def test_cause_classifier_keeps_mixed_and_unobserved_failures_separate(self):
        cases = [({}, ["provider_api_error"], False, "environment"),
                 ({}, [], True, "measurement_system"),
                 ({}, ["provider_api_error"], True, "unattributed"),
                 ({"timed_out": True}, [], False, "unattributed"),
                 ({"status": "failed"}, ["request_boundary_unavailable"], False, "unattributed"),
                 ({"status": "completed"}, [], False, None)]
        for meta, reasons, evaluator, expected in cases:
            with self.subTest(meta=meta, reasons=reasons, evaluator=evaluator):
                self.assertEqual(expected, causes.classify(meta, reasons, evaluator_error=evaluator)["owner"])

    def test_fixed_order_duplicate_and_censored_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = schedule.build([row("one"), row("two", order=1), row("three", order=2)],
                                  schedule_id="test", journal_root=root, max_wall_seconds=100)
            with self.assertRaisesRegex(ValueError, "predecessor"):
                schedule.claim(plan, "two", profile_hash="a" * 64, input_hash="b" * 64)
            _, evidence = schedule.claim(plan, "one", profile_hash="a" * 64, input_hash="b" * 64)
            with self.assertRaises(FileExistsError):
                schedule.claim(plan, "one", profile_hash="a" * 64, input_hash="b" * 64)
            schedule.finish(plan, evidence, result_hash="c" * 64, cause_owner="measurement_system")
            self.assertEqual(["finished", "censored", "censored"],
                             [r["status"] for r in schedule.accounting(plan)])
            with self.assertRaisesRegex(ValueError, "schedule_stopped"):
                schedule.claim(plan, "two", profile_hash="a" * 64, input_hash="b" * 64)

    def test_two_os_processes_cannot_claim_the_same_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = schedule.build([row("one")], schedule_id="race", journal_root=root / "journal", max_wall_seconds=100)
            records.write(root / "plan.json", plan)
            code = ("import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                    "from model_fitness import records,schedule; "
                    "schedule.claim(records.read(Path(sys.argv[2])), 'one', profile_hash='a'*64, input_hash='b'*64)")
            args = [sys.executable, "-c", code, str(OPERATION), str(root / "plan.json")]
            children = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            for child in children:
                child.communicate(timeout=30)
            self.assertEqual([0, 1], sorted(child.returncode for child in children))
            self.assertEqual("interrupted_or_running", schedule.accounting(plan)[0]["status"])


class ProcessTests(unittest.TestCase):
    def test_timeout_retains_output_and_exit_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = processes.capture([sys.executable, "-c", "import time; print('before-timeout',flush=True); time.sleep(30)"],
                                       cwd=root, environment=dict(os.environ), prompt=b"owned-input", output_dir=root,
                                       timeout_seconds=0.5)
            self.assertEqual("timeout", result["status"])
            self.assertIsNotNone(result["exit_code"])
            self.assertIn("before-timeout", (root / "transcript.jsonl").read_text())
            self.assertTrue((root / "process-start.json").exists())

    def test_fast_exit_still_checks_output_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = processes.capture([sys.executable, "-c", "print('x'*100000)"], cwd=root,
                                       environment=dict(os.environ), prompt=b"", output_dir=root,
                                       timeout_seconds=5, max_output_bytes=1024)
            self.assertEqual("output_limit", result["status"])


@unittest.skipIf(os.name == "nt", "scripted executable uses a POSIX shebang; portable process/journal tests run on Windows")
class WorkflowTests(unittest.TestCase):
    def test_calibrate_prepare_run_replay_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / "scripted-cli"
            cli.write_text("#!" + sys.executable + "\n" + SCRIPT)
            cli.chmod(0o755)
            installed = profiles.inspect("codex", cli, "scripted-model", "high")
            fixture = OPERATION / "fixtures/f4_minimality_negative_control"
            helper = root / "host-helper.py"
            helper.write_text("# owned test dependency\n")
            prepared = executor.prepare(fixture, output=root / "prepared",
                                        ruleset_relative="Modules/Stack/knowledge/reduced_stack_rules.json",
                                        planned_paths=["src/BuildInfo.cs"],
                                        implementation_dependencies={"test_helper": helper})
            attempts = [row("f0", kind="calibration", input_hash=calibration.input_hash()),
                        row("f4", order=1, input_hash=prepared["record_hash"])]
            for attempt in attempts:
                attempt["profile_record_hash"] = installed["record_hash"]
            attempts[0].update(seed_identity=calibration.input_hash(), fixture_id="f0_cli_canary")
            attempts[1].update(seed_identity=prepared["seed_identity"], fixture_id=prepared["fixture"]["fixture_id"])
            records.write(root / "profile.json", installed)
            for attempt in attempts:
                attempt.update(profile_ref=str(root / "profile.json"), workspace_ref=str(root / (attempt["attempt_id"] + "-workspace")))
            attempts[1].update(preparation_ref=str(root / "prepared/prepared.json"), calibration_ref=str(root / "journal/f0/calibration.json"))
            plan = schedule.build(attempts, schedule_id="workflow", journal_root=root / "journal", max_wall_seconds=100)
            broken = json.loads(json.dumps(plan))
            broken["attempts"][1]["input_hash"] = "c" * 64
            broken = records.seal(broken)
            with self.assertRaisesRegex(ValueError, "scheduled_preparation_changed"):
                executor.run_schedule(broken)
            self.assertFalse((root / "journal").exists(), "the whole roster must be checked before its first launch")
            calibrated_relative = calibration.run(installed, plan, "f0", workspace=Path(os.path.relpath(root / "f0-workspace")))
            self.assertTrue(calibrated_relative["diagnostic_compatible"], "relative cwd must be resolved before entering the workspace")
            self.assertEqual(["finished", "finished"], [r["status"] for r in executor.run_schedule(plan)])
            calibrated = records.read(root / "journal/f0/calibration.json")
            self.assertTrue(calibrated["diagnostic_compatible"], calibrated)
            self.assertFalse(calibrated["score_eligible"])
            evidence = root / "journal/f4"
            result = records.read(evidence / "result.json")
            completed_identity = baseline.content_identity(root / "journal")
            executor.run_schedule(plan)
            self.assertEqual(completed_identity, baseline.content_identity(root / "journal"))
            self.assertNotIn("evaluator_failure", result["reason_codes"],
                             (evidence / "evaluator-error.json").read_text() if (evidence / "evaluator-error.json").exists() else result)
            self.assertIsNone(result["score_total"])
            self.assertEqual("passed", records.read(evidence / "oracles.json")["results"][0]["status"])
            before = baseline.content_identity(evidence)
            self.assertEqual(result, executor.score(evidence))
            self.assertEqual(before, baseline.content_identity(evidence), "replay must be read-only")
            self.assertIn("source snapshot without Git metadata", (evidence / "stdin.txt").read_text())
            helper.write_text("# later host revision\n")
            with self.assertRaisesRegex(ValueError, "prepared_implementation_dependency_changed"):
                executor.verify_prepared(root / "prepared/prepared.json")
            self.assertEqual(result, executor.score(evidence), "replay uses the frozen helper without executing it")
            frozen = root / "prepared" / prepared["implementation_dependencies"]["test_helper"]["frozen_ref"]
            original_helper = frozen.read_bytes()
            frozen.write_text("# altered archive\n")
            with self.assertRaisesRegex(ValueError, "prepared_frozen_implementation_changed"):
                executor.score(evidence)
            frozen.write_bytes(original_helper)
            diagnostic = reporting.diagnostic_report(plan)
            self.assertEqual(2, diagnostic["scheduled"])
            self.assertEqual(0, diagnostic["model_fitness"]["numeric_results"])
            self.assertEqual(10, diagnostic["attempts"][1]["observed_token_usage"]["output_tokens"])
            self.assertIn("Task-oracle outcomes", reporting.render_diagnostic(diagnostic))
            original = (evidence / "transcript.jsonl").read_bytes()
            (evidence / "transcript.jsonl").write_bytes(original + b"{}\n")
            with self.assertRaisesRegex(ValueError, "captured_artifact_changed"):
                executor.score(evidence)
            (evidence / "transcript.jsonl").write_bytes(original)
            (evidence / "final-tree/src/BuildInfo.cs").write_text("changed-after-capture")
            with self.assertRaisesRegex(ValueError, "captured_final_tree_changed"):
                executor.score(evidence)
            installed["profile"]["requested_model"] = "different-model"
            installed["profile"] = records.seal(installed["profile"], "profile_hash")
            installed = records.seal(installed)
            with self.assertRaisesRegex(ValueError, "calibration_identity_stale"):
                calibration.verify(calibrated, installed, evidence_root=root / "journal/f0")


if __name__ == "__main__":
    unittest.main()
