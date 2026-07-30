from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reduced_stack_gate as gate  # noqa: E402
import reduced_stack_resolver as resolver  # noqa: E402
import reduced_stack_testkit as kit  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

ASYNC_TASK = (
    "PD-1 Add async retry to the level loader: SwitchToThreadPool, await a "
    "UniTask, then continue on the main thread."
)
CS_TASK = "PD-2 Rename the score field on the leaderboard view."
DOCS_TASK = "Fix a typo in the module readme documentation."


class GateHarness(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.work = Path(self._temporary.name)
        self.repo = kit.build_fixture_repo(self.work)

    def derive(self, envelope: dict) -> dict:
        return resolver.derive_plan(
            self.repo, kit.ruleset_path(self.repo), envelope
        )

    def run_check(
        self,
        plan: dict,
        ledger: dict,
        *,
        manifest: dict | None = None,
        attestation: dict | None = None,
        reconcile_with: tuple[dict, str] | None = None,
    ) -> tuple[int, dict]:
        plan_path = kit.write_json(self.work, "plan.json", plan)
        ledger_path = kit.write_json(self.work, "ledger.json", ledger)
        manifest_path = (
            kit.write_json(self.work, "semantic_inputs.json", manifest)
            if manifest
            else None
        )
        attestation_path = (
            kit.write_json(self.work, "attestation.json", attestation)
            if attestation
            else None
        )
        output_path = self.work / "gate_result.json"
        namespace = argparse.Namespace(
            plan=str(plan_path),
            ledger=str(ledger_path),
            semantic_input_manifest=(
                str(manifest_path) if manifest_path else None
            ),
            session_attestation=(
                str(attestation_path) if attestation_path else None
            ),
            output=str(output_path),
        )
        if reconcile_with is not None:
            envelope, diff_text = reconcile_with
            diff_path = self.work / "parent.diff"
            diff_path.write_text(diff_text, encoding="utf-8")
            namespace.parent_diff = str(diff_path)
            namespace.repo_root = str(self.repo)
            namespace.ruleset = str(kit.ruleset_path(self.repo))
            namespace.ruleset_extension = []
            namespace.task_envelope = str(
                kit.write_json(self.work, "envelope.json", envelope)
            )
            namespace.task_text_file = None
        exit_code = gate._check_or_reconcile(
            namespace, reconcile_with is not None
        )
        result = json.loads(output_path.read_text(encoding="utf-8"))
        return exit_code, result


class GateCheckTests(GateHarness):
    def _high_risk_setup(self, contract: dict) -> tuple[dict, dict, dict]:
        contract_path, contract_sha = kit.write_contract(self.work, contract)
        envelope = kit.make_envelope(
            self.repo,
            task_text=ASYNC_TASK,
            risk_class="high",
            referenced_paths=["DemoProject/Scripts/Foo.cs"],
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
            execution_contract_ref=str(contract_path),
            execution_contract_sha256=contract_sha,
        )
        plan = self.derive(envelope)
        manifest = {
            "inputs": [
                {"checker_id": "routing_gate_check", "ref": str(contract_path)}
            ]
        }
        return envelope, plan, manifest

    def test_full_delivery_and_deep_contract_pass(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(events)
        exit_code, result = self.run_check(
            plan, ledger, manifest=manifest,
            attestation=kit.make_attestation(self.repo),
        )
        self.assertEqual(gate.EXIT_PASS, exit_code)
        self.assertEqual("pass", result["decision"])
        self.assertEqual("audited", result["enforcement_mode"])
        self.assertIsNone(result["authorization"])
        self.assertEqual("att-test-1", result["session_attestation_id"])
        self.assertEqual("unambiguous", result["mutation_cutoff_confidence"])
        self.assertTrue(
            all(row["gate_satisfied"] for row in result["group_results"])
        )
        self.assertEqual(
            ["pass"],
            [row["status"] for row in result["semantic_check_results"]],
        )

    def test_claimed_read_arrays_alone_fail(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        claims = [
            {
                "seq": 5,
                "actor": "root",
                "claimed_paths": [
                    artifact["path"]
                    for artifact in plan["required_artifacts"]
                ],
            }
        ]
        ledger = kit.make_ledger(
            [kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)],
            claims=claims,
        )
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertEqual("fail", result["decision"])
        states = {
            member["state"]
            for row in result["group_results"]
            for member in row["members"]
        }
        self.assertEqual({"not_observed"}, states)
        self.assertTrue(
            any(
                code.startswith("required_group_unsatisfied:")
                for code in result["reason_codes"]
            )
        )

    def test_shallow_routing_contract_blocks_full_delivery(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.SHALLOW_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(events)
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertEqual("fail", result["decision"])
        self.assertTrue(
            all(row["gate_satisfied"] for row in result["group_results"])
        )
        semantic = result["semantic_check_results"][0]
        self.assertEqual("fail", semantic["status"])
        self.assertIn("incomplete_root_cause_chain", semantic["reason_codes"])
        self.assertIn(
            "semantic_check_blocking:routing_gate_check",
            result["reason_codes"],
        )

    def test_unrelated_task_does_not_invoke_routing_checker(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = self.derive(envelope)
        self.assertEqual([], plan["semantic_checks"])
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(plan, kit.make_ledger(events))
        self.assertEqual(gate.EXIT_PASS, exit_code)
        self.assertEqual([], result["semantic_check_results"])

    def test_empty_routing_input_cannot_become_a_pass(self) -> None:
        _, plan, _ = self._high_risk_setup(kit.DEEP_CONTRACT)
        empty_path = self.work / "empty_contract.json"
        empty_path.write_text("{}", encoding="utf-8")
        manifest = {
            "inputs": [
                {"checker_id": "routing_gate_check", "ref": str(empty_path)}
            ]
        }
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        semantic = result["semantic_check_results"][0]
        self.assertEqual("invalid_input", semantic["status"])

    def test_swapped_routing_payload_is_detected(self) -> None:
        _, plan, _ = self._high_risk_setup(kit.DEEP_CONTRACT)
        (self.work / "swap").mkdir()
        swapped_path, _ = kit.write_contract(
            self.work / "swap", kit.SHALLOW_CONTRACT
        )
        manifest = {
            "inputs": [
                {"checker_id": "routing_gate_check", "ref": str(swapped_path)}
            ]
        }
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        semantic = result["semantic_check_results"][0]
        self.assertEqual("invalid_input", semantic["status"])
        self.assertIn(
            "input_swapped_after_derivation", semantic["reason_codes"]
        )

    def test_missing_routing_manifest_fails_closed(self) -> None:
        _, plan, _ = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(plan, kit.make_ledger(events))
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertEqual(
            "invalid_input", result["semantic_check_results"][0]["status"]
        )

    def test_runtime_context_unverified_is_measurement_invalid(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = [
            event
            for event in kit.proven_events_for_plan(plan)
            if event["targets"] != ["Agents.md"]
        ]
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(
            events,
            context_manifest=[
                {"path": "Agents.md", "trust": "unverified", "case_alias": True}
            ],
        )
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_INVALID, exit_code)
        self.assertEqual("invalid", result["decision"])
        self.assertIn("runtime_context_unverified", result["reason_codes"])
        member = next(
            member
            for row in result["group_results"]
            for member in row["members"]
            if member["path"] == "Agents.md"
        )
        self.assertEqual("runtime_delivered_unverified", member["state"])

    def test_attested_context_manifest_satisfies_the_router(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        router_sha = next(
            artifact["sha256"]
            for artifact in plan["required_artifacts"]
            if artifact["path"] == "Agents.md"
        )
        events = [
            event
            for event in kit.proven_events_for_plan(plan)
            if event["targets"] != ["Agents.md"]
        ]
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(
            events,
            context_manifest=[
                {"path": "Agents.md", "trust": "attested", "sha256": router_sha}
            ],
        )
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_PASS, exit_code)
        member = next(
            member
            for row in result["group_results"]
            for member in row["members"]
            if member["path"] == "Agents.md"
        )
        self.assertEqual("trusted_runtime_delivered", member["state"])

    def test_ambiguous_command_before_first_edit_is_invalid(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(kit.ambiguous_event("amb-1", 400))
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_INVALID, exit_code)
        self.assertEqual(
            "ambiguous_prior_commands", result["mutation_cutoff_confidence"]
        )
        self.assertIn("mutation_boundary_ambiguous", result["reason_codes"])

    def test_subagent_only_read_earns_no_credit(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = []
        seq = 10
        for artifact in plan["required_artifacts"]:
            events.append(
                kit.read_event(
                    f"read-{seq}", artifact["path"], artifact["sha256"], seq,
                    actor="subagent",
                )
            )
            seq += 2
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertTrue(
            any(
                code.startswith("required_group_unsatisfied:")
                for code in result["reason_codes"]
            )
        )

    def test_read_after_mutation_start_earns_no_credit(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan, start_seq=600)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)

    def test_model_identity_mismatch_is_invalid(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(events, observed_model="other-model")
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_INVALID, exit_code)
        self.assertIn("model_identity_mismatch", result["reason_codes"])

    def test_tampered_ledger_hash_is_invalid(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger = kit.make_ledger(events)
        ledger["events"] = ledger["events"][1:]
        exit_code, result = self.run_check(plan, ledger, manifest=manifest)
        self.assertEqual(gate.EXIT_INVALID, exit_code)
        self.assertIn("ledger_hash_mismatch", result["reason_codes"])

    def test_checker_implementation_change_is_detected(self) -> None:
        _, plan, manifest = self._high_risk_setup(kit.DEEP_CONTRACT)
        for check in plan["semantic_checks"]:
            check["checker_sha256"] = xc.sha256_bytes(b"other implementation")
        plan["plan_hash"] = xc.document_hash(plan, "plan_hash")
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), manifest=manifest
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertIn(
            "checker_implementation_changed",
            result["semantic_check_results"][0]["reason_codes"],
        )


class GateReconcileTests(GateHarness):
    def _passing_setup(self) -> tuple[dict, dict, list]:
        envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = self.derive(envelope)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        return envelope, plan, events

    def test_clean_diff_reconciles_to_pass(self) -> None:
        envelope, plan, events = self._passing_setup()
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1 @@\n-old\n+var score = 1;\n"
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), reconcile_with=(envelope, diff)
        )
        self.assertEqual(gate.EXIT_PASS, exit_code)
        self.assertEqual("pass", result["decision"])
        self.assertEqual([], result["post_diff_additions"])

    def test_new_closeout_sdk_signal_reopens_the_gate(self) -> None:
        envelope, plan, events = self._passing_setup()
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1,2 @@\n public class Foo { }\n"
            "+var att = AppTrackingTransparency.Request();\n"
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), reconcile_with=(envelope, diff)
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertEqual("reopen_required", result["decision"])
        addition = result["post_diff_additions"][0]
        self.assertEqual("before_closeout", addition["phase"])
        self.assertTrue(addition["path"].endswith("sdk_changes.md"))

    def test_satisfied_closeout_signal_passes(self) -> None:
        envelope, plan, events = self._passing_setup()
        pack_path = f"{kit.MODULE_PREFIX}/reviews/policy_packs/sdk_changes.md"
        pack_sha = xc.sha256_file(self.repo / pack_path)
        events.append(kit.read_event("read-late", pack_path, pack_sha, 600))
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1,2 @@\n public class Foo { }\n"
            "+var att = AppTrackingTransparency.Request();\n"
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), reconcile_with=(envelope, diff)
        )
        self.assertEqual(gate.EXIT_PASS, exit_code)
        self.assertEqual("pass", result["decision"])

    def test_scope_drift_into_code_fails_and_cannot_be_cured(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=DOCS_TASK,
            task_kind="docs_update",
            risk_class="baseline",
            planned_mutation_paths=["DemoProject/notes.md"],
        )
        plan = self.derive(envelope)
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/notes.md", 500)
        )
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1 @@\n-old\n+var x = 1;\n"
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), reconcile_with=(envelope, diff)
        )
        self.assertEqual(gate.EXIT_FAIL, exit_code)
        self.assertEqual("fail", result["decision"])
        self.assertTrue(
            any(
                code.startswith("scope_drift_before_first_mutation:")
                for code in result["reason_codes"]
            )
        )

    def test_resolver_missed_obligation_is_invalid_not_model_fault(self) -> None:
        docs_envelope = kit.make_envelope(
            self.repo,
            task_text=DOCS_TASK,
            task_kind="docs_update",
            risk_class="baseline",
            planned_mutation_paths=["DemoProject/notes.md"],
        )
        plan = self.derive(docs_envelope)
        cs_envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1 @@\n-old\n+var x = 1;\n"
        )
        exit_code, result = self.run_check(
            plan, kit.make_ledger(events), reconcile_with=(cs_envelope, diff)
        )
        self.assertEqual(gate.EXIT_INVALID, exit_code)
        self.assertEqual("invalid", result["decision"])
        self.assertTrue(
            any(
                code.startswith("resolver_missed_obligation:")
                for code in result["reason_codes"]
            )
        )


class GateCliSmokeTests(GateHarness):
    def test_derive_check_cli_end_to_end(self) -> None:
        contract_path, contract_sha = kit.write_contract(
            self.work, kit.DEEP_CONTRACT
        )
        envelope = kit.make_envelope(
            self.repo,
            task_text=ASYNC_TASK,
            risk_class="high",
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
            execution_contract_ref=str(contract_path),
            execution_contract_sha256=contract_sha,
        )
        envelope_path = kit.write_json(self.work, "envelope.json", envelope)
        plan_path = self.work / "plan.json"
        derive_run = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "reduced_stack_gate.py"),
                "derive",
                "--repo-root", str(self.repo),
                "--ruleset", str(kit.ruleset_path(self.repo)),
                "--task-envelope", str(envelope_path),
                "--output", str(plan_path),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, derive_run.returncode, derive_run.stderr)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))

        loader_run = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "reduced_stack_loader.py"),
                "--repo-root", str(self.repo),
                "--plan", str(plan_path),
                "--manifest-output", str(self.work / "delivery_manifest.json"),
                "--bundle-output", str(self.work / "stack.bundle"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, loader_run.returncode, loader_run.stderr)

        events = kit.proven_events_for_plan(plan)
        events.append(
            kit.mutation_event("edit-1", "DemoProject/Scripts/Foo.cs", 500)
        )
        ledger_path = kit.write_json(
            self.work, "ledger.json", kit.make_ledger(events)
        )
        manifest_path = kit.write_json(
            self.work,
            "semantic_inputs.json",
            {
                "inputs": [
                    {
                        "checker_id": "routing_gate_check",
                        "ref": str(contract_path),
                    }
                ]
            },
        )
        check_run = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "reduced_stack_gate.py"),
                "check",
                "--plan", str(plan_path),
                "--ledger", str(ledger_path),
                "--semantic-input-manifest", str(manifest_path),
                "--output", str(self.work / "gate_result.json"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, check_run.returncode, check_run.stderr)
        self.assertIn("pass", check_run.stdout)


if __name__ == "__main__":
    unittest.main()
