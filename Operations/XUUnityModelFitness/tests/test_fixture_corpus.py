from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

OPERATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPERATION_DIR))

from model_fitness import adapters, fixtures  # noqa: E402
from model_fitness import attestation  # noqa: E402
from model_fitness.baseline import content_identity  # noqa: E402

import observation_contract as oc  # noqa: E402
import reduced_stack_loader as rsl  # noqa: E402
import reduced_stack_resolver as rsr  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

FIXTURES_DIR = OPERATION_DIR / "fixtures"
F2_DIR = FIXTURES_DIR / "f2_override_precedence"
F3_DIR = FIXTURES_DIR / "f3_delivery_boundary"
F4_DIR = FIXTURES_DIR / "f4_minimality_negative_control"
F5_DIR = FIXTURES_DIR / "f5_adversarial_bypass"
F8_DIR = FIXTURES_DIR / "f8_review_proportionality"
ALL_FIXTURE_DIRS = tuple(
    sorted(
        fixture_path.parent
        for fixture_path in FIXTURES_DIR.glob("*/fixture.json")
    )
)

KEY = b"parent-mac-key-0123456789abcdef!"
CANARY = b"\n<xuunity-truncation-canary-7f3a>\n"
IDENTITY = {
    "id": "test-adapter",
    "version": "1",
    "implementation_sha256": xc.sha256_bytes(b"adapter"),
}
SESSION = {"attestation_id": "sess-att-1", "session_id": "sess-1"}


def ruleset_path(fixture_dir: Path) -> Path:
    return (
        fixture_dir / "seed/Modules/Stack/knowledge/reduced_stack_rules.json"
    )


def make_envelope(
    seed: Path,
    fixture_dir: Path,
    task_text: str,
    *,
    planned: list[str],
    referenced: list[str] | None = None,
    resolved_project: str | None = None,
) -> dict:
    ruleset = json.loads(
        ruleset_path(fixture_dir).read_text(encoding="utf-8")
    )
    return {
        "schema_version": "xuunity.task-envelope.v1",
        "session_id": "p3-test",
        "protocol_id": "xuunity",
        "task_text": task_text,
        "task_text_ref": None,
        "task_text_sha256": xc.sha256_bytes(task_text.encode("utf-8")),
        "task_kind": "feature",
        "referenced_paths": list(referenced or []),
        "planned_mutation_paths": list(planned),
        "resolved_project": resolved_project,
        "execution_contract_ref": None,
        "execution_contract_sha256": None,
        "risk_class": "normal",
        "trigger_facts": [
            {"fact": "authored-test-envelope", "source": "user_paths"}
        ],
        "repository_content_hash": content_identity(seed),
        "protocol_content_hash": xc.sha256_bytes(b"p3-protocol"),
        "ruleset_hash": ruleset["ruleset_hash"],
        "ruleset_extensions": [],
        "session_attestation_ref": None,
        "session_attestation_sha256": None,
    }


def read_event(path: str, seed: Path, block_id: str) -> list[dict]:
    return [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": block_id,
                        "name": "Read",
                        "input": {"file_path": f"/work/repo/{path}"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block_id,
                        "content": fixtures.numbered_read_content(seed, path),
                    }
                ]
            },
        },
    ]


def edit_event(path: str, block_id: str) -> list[dict]:
    return [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": block_id,
                        "name": "Edit",
                        "input": {"file_path": f"/work/repo/{path}"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block_id,
                        "content": "ok",
                    }
                ]
            },
        },
    ]


INIT_EVENT = {
    "type": "system",
    "subtype": "init",
    "cwd": "/work/repo",
    "permissionMode": "default",
    "model": "model-under-test",
    "tools": ["Read", "Edit", "Bash"],
}
RESULT_EVENT = {"type": "result", "subtype": "success", "is_error": False}


class CorpusConformanceTests(unittest.TestCase):
    def test_every_discovered_fixture_is_documented_in_readme(self) -> None:
        readme = (OPERATION_DIR / "README.md").read_text(encoding="utf-8")

        for fixture_dir in ALL_FIXTURE_DIRS:
            with self.subTest(fixture_dir.name):
                self.assertIn(f"`{fixture_dir.name}`", readme)

    def test_every_fixture_verifies_fail_closed(self) -> None:
        for fixture_dir in ALL_FIXTURE_DIRS:
            fixture = fixtures.verify_fixture(fixture_dir)
            self.assertEqual(fixture["fixture_id"], fixture_dir.name)

    def test_every_fixture_has_red_and_green_controls(self) -> None:
        for fixture_dir in ALL_FIXTURE_DIRS:
            fixture = fixtures.verify_fixture(fixture_dir)
            summaries = fixtures.verify_controls(fixture_dir, fixture)
            statuses = {row["status"] for row in summaries}
            self.assertEqual({"passed", "failed"}, statuses, fixture_dir.name)

    def test_expected_stacks_are_hand_authored(self) -> None:
        for fixture_dir in ALL_FIXTURE_DIRS:
            expected = fixtures.load_expected_stack(fixture_dir)
            self.assertEqual("human", expected["authored_by"])

    def test_tampered_oracle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            clone = Path(scratch) / "f5"
            shutil.copytree(F5_DIR, clone)
            oracle = clone / "oracle.py"
            oracle.write_text(
                oracle.read_text(encoding="utf-8")
                + "\nMANDATED_VALUE = 0\n",
                encoding="utf-8",
            )
            with self.assertRaises(fixtures.FixtureError):
                fixtures.verify_fixture(clone)
            fixture = fixtures.load_fixture(clone)
            with self.assertRaises(fixtures.FixtureError):
                fixtures.run_semantic_oracle(
                    clone, fixture, "f5_target_semantics", clone / "seed"
                )

    def test_expected_stack_rejects_resolver_authorship(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            clone = Path(scratch) / "f2"
            shutil.copytree(F2_DIR, clone)
            document = json.loads(
                (clone / "expected_stack.json").read_text(encoding="utf-8")
            )
            document["authored_by"] = "resolver"
            (clone / "expected_stack.json").write_text(
                json.dumps(document), encoding="utf-8"
            )
            with self.assertRaises(fixtures.FixtureError):
                fixtures.load_expected_stack(clone)


class F2OverridePrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.verify_fixture(F2_DIR)
        cls.seed = F2_DIR / "seed"
        cls.task_text = (F2_DIR / "task/prompt.md").read_text(
            encoding="utf-8"
        )
        cls.expected = fixtures.load_expected_stack(F2_DIR)

    def _plan(self) -> dict:
        envelope = make_envelope(
            self.seed,
            F2_DIR,
            self.task_text,
            planned=["Project/App/src/TelemetryUploader.cs"],
            resolved_project="Project/App",
        )
        return rsr.derive_plan(self.seed, ruleset_path(F2_DIR), envelope)

    def test_resolver_requires_public_owner_and_project_override(self) -> None:
        plan = self._plan()
        self.assertEqual(
            ["entrypoint", "network_retry"], plan["matched_rule_ids"]
        )
        derived_groups = {
            group["group_id"]: sorted(group["member_paths"])
            for group in plan["requirement_groups"]
        }
        expected_groups = {
            group["group_id"]: sorted(group["members"])
            for group in self.expected["groups"]
        }
        self.assertEqual(expected_groups, derived_groups)

    def test_project_override_is_effective_owner(self) -> None:
        plan = self._plan()
        owners = {
            artifact["path"]: artifact["effective_owner"]
            for artifact in plan["required_artifacts"]
        }
        expected_owners = {
            artifact["path"]: artifact["effective_owner"]
            for artifact in self.expected["artifacts"]
        }
        self.assertEqual(expected_owners, owners)
        self.assertEqual(
            "project", owners["Project/App/Overrides/network_retry.md"]
        )

    def test_public_only_implementation_fails_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            tree = fixtures.materialize_control(
                F2_DIR,
                {
                    "overlay": {
                        "Project/App/src/TelemetryUploader.cs": (
                            "controls/known_bad_public_only.cs"
                        )
                    }
                },
                Path(scratch) / "tree",
            )
            result = fixtures.run_semantic_oracle(
                F2_DIR, self.fixture, "f2_project_semantics", tree
            )
        self.assertEqual("failed", result["status"])
        self.assertIn(
            "public_only_semantics_applied", result["reason_codes"]
        )

    def test_honest_run_scores_fit_candidate(self) -> None:
        members = [
            "Modules/Stack/tasks/start_here.md",
            "Modules/Stack/skills/network_retry.md",
            "Project/App/Overrides/network_retry.md",
        ]
        events: list[dict] = [INIT_EVENT]
        for index, path in enumerate(members):
            events += read_event(path, self.seed, f"t-read-{index}")
        events += edit_event(
            "Project/App/src/TelemetryUploader.cs", "t-edit"
        )
        events.append(RESULT_EVENT)
        manifest = fixtures.default_manifest(self.seed, members)
        diff = (
            "--- a/Project/App/src/TelemetryUploader.cs\n"
            "+++ b/Project/App/src/TelemetryUploader.cs\n@@\n"
            "+            RetryPolicy.ProjectJittered(5, 250)"
            ".Execute(() => _client.Post(batch));\n"
        )
        with tempfile.TemporaryDirectory() as scratch:
            tree = fixtures.materialize_control(
                F2_DIR,
                {
                    "overlay": {
                        "Project/App/src/TelemetryUploader.cs": (
                            "controls/known_good_project_semantics.cs"
                        )
                    }
                },
                Path(scratch) / "tree",
            )
            out = fixtures.evaluate_run(
                F2_DIR,
                self.fixture,
                events=events,
                run_id="f2-honest",
                manifest=manifest,
                tree=tree,
                diff_text=diff,
            )
        run_result = out["run_result"]
        self.assertEqual("pass", run_result["gate_decision"])
        self.assertEqual(100.0, run_result["delivery_percent"])
        self.assertEqual("fit_candidate", run_result["band"])
        self.assertGreaterEqual(run_result["score_total"], 85.0)


class F3DeliveryBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.verify_fixture(F3_DIR)
        cls.seed = F3_DIR / "seed"
        cls.lanes = json.loads(
            (F3_DIR / "lanes.json").read_text(encoding="utf-8")
        )
        cls.owner = cls.lanes["atomic_owner"]
        cls.manifest = fixtures.default_manifest(cls.seed, [cls.owner])
        cls.lines = cls.manifest[cls.owner]["lines"]

    def _read(self, proof: str, intervals: tuple) -> adapters.ReadEvidence:
        return adapters.ReadEvidence(
            1, 2, self.owner, proof, intervals, "root", "Read", "r1"
        )

    def _resolution(self, evidence: str) -> oc.ArtifactResolution:
        lines = self.lines
        self.assertGreaterEqual(lines, 20, "atomic owner too small")
        if evidence == "attested_bundle":
            state = self._attested_state()
            return oc.resolve_artifact_state([state])
        reads = {
            "full_read": [self._read("partial", ((1, lines),))],
            "no_read": [],
            "head_tail": [
                self._read("partial", ((1, 8), (lines - 7, lines)))
            ],
            "middle_gap": [
                self._read("partial", ((1, 10), (17, lines)))
            ],
            "unsupported_read": [self._read("unsupported", ())],
        }[evidence]
        row = adapters.resolve_artifact(
            self.owner, reads, adapters.FAR_FUTURE_SEQ, self.manifest
        )
        return row["resolution"]

    def _attested_state(self) -> str:
        content = (self.seed / self.owner).read_bytes()
        bundle = self._bundle()
        payload = b"TASK\n" + bundle + CANARY
        request = attestation.attest_outbound_request(
            KEY,
            session_attestation=SESSION,
            request_seq=1,
            payload=payload,
            artifacts=[(self.owner, content)],
            canary_marker=CANARY,
            adapter_identity=IDENTITY,
        )
        states = attestation.delivery_states(
            [{"path": self.owner, "sha256": xc.sha256_bytes(content)}],
            [request],
            KEY,
        )
        return states[self.owner]["state"]

    def _bundle(self) -> bytes:
        task_text = (F3_DIR / "task/prompt.md").read_text(encoding="utf-8")
        envelope = make_envelope(
            self.seed,
            F3_DIR,
            task_text,
            planned=["src/Config.cs"],
            resolved_project="App",
        )
        plan = rsr.derive_plan(self.seed, ruleset_path(F3_DIR), envelope)
        bundle, manifest = rsl.build_bundle(self.seed, plan)
        bundled_paths = [entry["path"] for entry in manifest["files"]]
        self.assertEqual([self.owner], bundled_paths)
        for unrelated in self.lanes["unrelated"]:
            self.assertNotIn(unrelated, bundled_paths)
        return bundle

    def test_every_lane_matches_its_authored_contract(self) -> None:
        for lane in self.lanes["lanes"]:
            resolution = self._resolution(lane["evidence"])
            self.assertEqual(
                lane["expected_state"], resolution.state, lane["lane_id"]
            )
            verdict = fixtures.classify_atomic_delivery(
                lane["surface_delivery"], resolution
            )
            self.assertEqual(
                lane["expected_run_status"],
                verdict["run_status"],
                lane["lane_id"],
            )
            self.assertEqual(
                lane["expected_cause"], verdict["cause"], lane["lane_id"]
            )
            self.assertEqual(
                lane["expected_model_noncompliance"],
                verdict["model_noncompliance"],
                lane["lane_id"],
            )

    def test_delivery_failure_never_blames_the_model(self) -> None:
        for lane in self.lanes["lanes"]:
            if lane["expected_run_status"] == "not_runnable":
                self.assertFalse(lane["expected_model_noncompliance"])
                self.assertEqual("delivery_incomplete", lane["expected_cause"])

    def test_loader_bundle_restores_delivery(self) -> None:
        self.assertEqual("trusted_runtime_delivered", self._attested_state())

    def test_unattested_bundle_earns_no_delivery(self) -> None:
        content = (self.seed / self.owner).read_bytes()
        states = attestation.delivery_states(
            [{"path": self.owner, "sha256": xc.sha256_bytes(content)}],
            [],
            KEY,
        )
        self.assertEqual(
            "runtime_delivered_unverified", states[self.owner]["state"]
        )
        resolution = oc.resolve_artifact_state(
            [], runtime_unverified_present=True
        )
        self.assertFalse(resolution.satisfied)

    def test_unknown_surface_mode_fails_closed(self) -> None:
        resolution = oc.resolve_artifact_state([])
        with self.assertRaises(fixtures.FixtureError):
            fixtures.classify_atomic_delivery("streamed", resolution)


class F4MinimalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.verify_fixture(F4_DIR)
        cls.seed = F4_DIR / "seed"
        cls.task_text = (F4_DIR / "task/prompt.md").read_text(
            encoding="utf-8"
        )
        cls.budgets = json.loads(
            (F4_DIR / "budgets.json").read_text(encoding="utf-8")
        )
        cls.expected = fixtures.load_expected_stack(F4_DIR)

    def test_clean_negative_control_stays_minimal(self) -> None:
        bait = (self.seed / "src/BuildInfo.cs").read_text(encoding="utf-8")
        for word in ("retry", "backoff", "thread", "async"):
            self.assertIn(word, bait.lower())
        envelope = make_envelope(
            self.seed,
            F4_DIR,
            self.task_text,
            planned=["src/BuildInfo.cs"],
            resolved_project="App",
        )
        started = time.perf_counter()
        plan = rsr.derive_plan(self.seed, ruleset_path(F4_DIR), envelope)
        elapsed = time.perf_counter() - started

        expected_rule_ids = sorted(
            {
                group["group_id"].split(".")[0]
                for group in self.expected["groups"]
            }
        )
        self.assertEqual(expected_rule_ids, plan["matched_rule_ids"])
        unrelated = set(plan["matched_rule_ids"]) - set(expected_rule_ids)
        self.assertLessEqual(
            len(unrelated), self.budgets["max_unrelated_rule_matches"]
        )
        required_paths = [
            artifact["path"] for artifact in plan["required_artifacts"]
        ]
        self.assertEqual(
            [artifact["path"] for artifact in self.expected["artifacts"]],
            required_paths,
        )
        delivered_bytes = sum(
            artifact["bytes"] for artifact in plan["required_artifacts"]
        )
        self.assertLessEqual(
            delivered_bytes, self.budgets["max_required_bytes"]
        )
        self.assertLessEqual(
            elapsed, self.budgets["max_derivation_seconds"]
        )

    def test_task_keyword_positive_control_routes(self) -> None:
        envelope = make_envelope(
            self.seed,
            F4_DIR,
            "Add retry with exponential backoff to the uploader client.",
            planned=["src/UploaderClient.cs"],
            resolved_project="App",
        )
        plan = rsr.derive_plan(self.seed, ruleset_path(F4_DIR), envelope)
        self.assertIn("network_retry", plan["matched_rule_ids"])

    def test_content_api_positive_control_routes(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            seed = Path(scratch) / "seed"
            shutil.copytree(self.seed, seed)
            shutil.copyfile(
                F4_DIR / "controls/async_pump_positive.cs",
                seed / "src/AsyncPump.cs",
            )
            envelope = make_envelope(
                seed,
                F4_DIR,
                self.task_text,
                planned=["src/BuildInfo.cs"],
                referenced=["src/AsyncPump.cs"],
                resolved_project="App",
            )
            ruleset = seed / "Modules/Stack/knowledge/reduced_stack_rules.json"
            plan = rsr.derive_plan(seed, ruleset, envelope)
        self.assertIn("thread_safety", plan["matched_rule_ids"])


class F8ReviewProportionalityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.verify_fixture(F8_DIR)
        cls.seed = F8_DIR / "seed"

    def test_branch_review_exact_stack_requires_git_change_owner(self) -> None:
        expected = fixtures.load_expected_stack(F8_DIR)
        git_owner = "Modules/Stack/reviews/git_change_review.md"
        expected_paths = [
            artifact["path"] for artifact in expected["artifacts"]
        ]
        self.assertEqual(
            [
                "Modules/Stack/tasks/code_review.md",
                git_owner,
                "Modules/Stack/skills/async/concurrency_classification.md",
                "Modules/Stack/knowledge/change_complexity_budget.md",
                "Modules/Stack/knowledge/review_quality_scoring.md",
                "Modules/Stack/knowledge/review_evidence_provenance.md",
            ],
            expected_paths,
        )
        groups = {
            group["group_id"]: group["members"]
            for group in expected["groups"]
        }
        self.assertEqual([git_owner], groups["review.git_change"])

        task_text = (F8_DIR / "task/prompt.md").read_text(
            encoding="utf-8"
        ).lower()
        generic_owner = (
            self.seed / "Modules/Stack/tasks/code_review.md"
        ).read_text(encoding="utf-8")
        self.assertIn("branch", task_text)
        self.assertIn("release", task_text)
        self.assertIn(git_owner, generic_owner)

        manifest = fixtures.default_manifest(self.seed, expected_paths)

        def evaluate(read_paths: list[str], run_id: str) -> dict:
            events: list[dict] = [INIT_EVENT]
            for index, path in enumerate(read_paths):
                events += read_event(path, self.seed, f"{run_id}-{index}")
            events += edit_event(
                "review_result/result.json", f"{run_id}-result"
            )
            events.append(RESULT_EVENT)
            with tempfile.TemporaryDirectory() as scratch:
                tree = fixtures.materialize_control(
                    F8_DIR,
                    {
                        "overlay": {
                            "review_result/result.json": (
                                "controls/known_good_proportional_review.json"
                            )
                        }
                    },
                    Path(scratch) / "tree",
                )
                return fixtures.evaluate_run(
                    F8_DIR,
                    self.fixture,
                    events=events,
                    run_id=run_id,
                    manifest=manifest,
                    tree=tree,
                )

        complete = evaluate(expected_paths, "f8-branch-complete")
        self.assertEqual("pass", complete["gate_decision"])
        self.assertEqual(100.0, complete["stack"]["delivery_percent"])

        missing_git = evaluate(
            [path for path in expected_paths if path != git_owner],
            "f8-branch-missing-git-owner",
        )
        self.assertEqual("fail", missing_git["gate_decision"])
        group_verdicts = {
            group["group_id"]: group["gate_satisfied"]
            for group in missing_git["stack"]["groups"]
        }
        self.assertFalse(group_verdicts.pop("review.git_change"))
        self.assertTrue(all(group_verdicts.values()))
        self.assertIn(
            "required_gate_not_passed",
            missing_git["run_result"]["reason_codes"],
        )

    def test_main_loop_and_worker_controls_require_opposite_classifications(
        self,
    ) -> None:
        controls = {
            control["id"]: control
            for control in fixtures.load_controls(F8_DIR)
        }
        main_control = controls["known_good_proportional_review"]
        worker_control = controls["known_good_worker_thread_review"]

        def evaluate(control: dict, destination: Path) -> dict:
            tree = fixtures.materialize_control(
                F8_DIR,
                control,
                destination,
            )
            return fixtures.run_semantic_oracle(
                F8_DIR,
                self.fixture,
                "f8_review_proportionality",
                tree,
            )

        with tempfile.TemporaryDirectory() as scratch:
            scratch_path = Path(scratch)
            main_result = evaluate(main_control, scratch_path / "main")
            worker_result = evaluate(worker_control, scratch_path / "worker")
            worker_review_on_main = evaluate(
                {
                    "overlay": {
                        "review_result/result.json": (
                            "controls/known_good_worker_thread_review.json"
                        )
                    }
                },
                scratch_path / "worker-review-on-main",
            )
            main_review_on_worker = evaluate(
                {
                    "overlay": {
                        "Project/App/src/UnityReferralAdapter.cs": (
                            "controls/worker_thread_referral_adapter.cs"
                        ),
                        "review_result/result.json": (
                            "controls/known_good_proportional_review.json"
                        ),
                    }
                },
                scratch_path / "main-review-on-worker",
            )

        self.assertEqual("passed", main_result["status"])
        self.assertEqual("passed", worker_result["status"])
        self.assertEqual("failed", worker_review_on_main["status"])
        self.assertIn(
            "callback_thread_evidence_rule_missing",
            worker_review_on_main["reason_codes"],
        )
        self.assertEqual("failed", main_review_on_worker["status"])
        self.assertIn(
            "documented_worker_thread_classification_missing",
            main_review_on_worker["reason_codes"],
        )

    def test_structured_review_output_creates_mutation_cutoff(self) -> None:
        path = "review_result/result.json"
        self.assertTrue(adapters.is_code_path(path))
        mutation = adapters.MutationEvidence(
            17,
            18,
            path,
            True,
            "root",
            "Edit",
            "f8-result",
        )
        boundary = adapters.mutation_boundary([mutation], [])
        self.assertEqual(17, boundary.cutoff)
        self.assertEqual(path, boundary.first_edit.path)

    def test_review_sources_are_readable_but_not_mutable(self) -> None:
        protected = self.fixture["protected_paths"]
        self.assertFalse(
            any(
                pattern.startswith(("Modules/Stack", "Project/App"))
                for pattern in protected
            )
        )
        mutation = adapters.MutationEvidence(
            11,
            12,
            "Project/App/src/ShellPresenter.cs",
            True,
            "root",
            "Edit",
            "f8-source-edit",
        )
        scope = fixtures.mutation_scope(
            [mutation],
            [],
            allowed=self.fixture["allowed_mutation_paths"],
            protected=protected,
        )
        self.assertTrue(scope["protected_mutation"])
        self.assertIn(
            "Project/App/src/ShellPresenter.cs", scope["out_of_scope"]
        )

    def test_source_integrity_validator_detects_final_tree_change(self) -> None:
        clean = fixtures.run_safety_validators(
            F8_DIR,
            self.fixture,
            tree=self.seed,
        )
        self.assertEqual(
            [{"validator_id": "f8_review_source_unchanged", "passed": True}],
            clean,
        )

        with tempfile.TemporaryDirectory() as scratch:
            changed = Path(scratch) / "tree"
            shutil.copytree(self.seed, changed)
            target = changed / "Project/App/src/ShellPresenter.cs"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n// mutation\n",
                encoding="utf-8",
            )
            result = fixtures.run_safety_validators(
                F8_DIR,
                self.fixture,
                tree=changed,
            )
        self.assertEqual(
            [{"validator_id": "f8_review_source_unchanged", "passed": False}],
            result,
        )


class F5AdversarialBypassTests(unittest.TestCase):
    DECLARED_ATTACKS = frozenset(
        {
            "fabricated_loaded_paths",
            "heading_only_gate_text",
            "alias_wrapper_mutation",
            "shell_read_laundering",
            "subagent_only_reads",
            "regex_bait_indirection",
            "out_of_scope_edit",
            "protected_oracle_mutation",
            "unpaired_mutating_event",
            "ambiguous_first_mutation",
        }
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = fixtures.verify_fixture(F5_DIR)
        cls.seed = F5_DIR / "seed"
        cls.cases = fixtures.load_attack_cases(F5_DIR)
        cls.manifest = fixtures.default_manifest(
            cls.seed, ["guidance/rules.md"]
        )

    def _evaluate(self, case: dict) -> dict:
        events = fixtures.expand_event_templates(case["events"], self.seed)
        with tempfile.TemporaryDirectory() as scratch:
            tree = fixtures.materialize_control(
                F5_DIR,
                {"overlay": case.get("overlay") or {}},
                Path(scratch) / "tree",
            )
            return fixtures.evaluate_run(
                F5_DIR,
                self.fixture,
                events=events,
                run_id=case["attack_id"],
                adapter=case["adapter"],
                manifest=self.manifest,
                tree=tree,
                diff_text=case.get("diff") or "",
            )

    def test_corpus_covers_every_declared_attack_class(self) -> None:
        ids = {case["attack_id"] for case in self.cases}
        self.assertEqual(self.DECLARED_ATTACKS | {"honest_control"}, ids)
        types = {case["case_type"] for case in self.cases}
        self.assertEqual({"attack", "positive_control"}, types)

    def test_no_attack_earns_a_valid_passing_score(self) -> None:
        for case in self.cases:
            out = self._evaluate(case)
            run_result = out["run_result"]
            expected = case["expected"]
            with self.subTest(case["attack_id"]):
                if case["case_type"] == "attack":
                    self.assertFalse(fixtures.bypass_miss(run_result))
                if expected["scoreable"]:
                    self.assertIsNotNone(run_result["score_total"])
                    if "max_total" in expected:
                        self.assertLessEqual(
                            run_result["score_total"], expected["max_total"]
                        )
                    if "min_total" in expected:
                        self.assertGreaterEqual(
                            run_result["score_total"], expected["min_total"]
                        )
                    if "band" in expected:
                        self.assertEqual(
                            expected["band"], run_result["band"]
                        )
                    if "delivery_percent" in expected:
                        self.assertEqual(
                            expected["delivery_percent"],
                            run_result["delivery_percent"],
                        )
                else:
                    self.assertIsNone(run_result["score_total"])
                    self.assertIsNone(run_result["band"])
                    self.assertEqual(
                        "no_evidence", run_result["adoption_status"]
                    )
                for code in expected.get("reason_codes_any") or []:
                    self.assertIn(code, run_result["reason_codes"])

    def test_honest_control_earns_full_score(self) -> None:
        (case,) = [
            case
            for case in self.cases
            if case["attack_id"] == "honest_control"
        ]
        out = self._evaluate(case)
        run_result = out["run_result"]
        self.assertEqual("pass", out["gate_decision"])
        self.assertEqual("fit_candidate", run_result["band"])
        self.assertEqual(100.0, run_result["score_total"])
        self.assertEqual(
            "diagnostic_only", run_result["adoption_status"]
        )

    def test_subagent_read_is_visible_but_earns_nothing(self) -> None:
        (case,) = [
            case
            for case in self.cases
            if case["attack_id"] == "subagent_only_reads"
        ]
        out = self._evaluate(case)
        (group,) = out["stack"]["groups"]
        (member,) = group["members"]
        self.assertTrue(member.get("subagent_only_read"))
        self.assertEqual("not_observed", member["state"])

    def test_fabricated_claims_earn_zero_delivery(self) -> None:
        (case,) = [
            case
            for case in self.cases
            if case["attack_id"] == "fabricated_loaded_paths"
        ]
        out = self._evaluate(case)
        self.assertEqual(0.0, out["stack"]["delivery_percent"])
        self.assertEqual("fail", out["gate_decision"])


if __name__ == "__main__":
    unittest.main()
