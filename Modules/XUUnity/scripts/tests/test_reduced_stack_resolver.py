from __future__ import annotations

import fnmatch
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reduced_stack_resolver as resolver  # noqa: E402
import reduced_stack_testkit as kit  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

ASYNC_TASK = (
    "TASK-1 Add async retry to the level loader: SwitchToThreadPool, await a "
    "UniTask, then continue on the main thread."
)
DOCS_TASK = "Fix a typo in the module readme documentation."
CS_TASK = "TASK-2 Rename the score field on the leaderboard view."


def derive(repo: Path, envelope: dict, **kwargs) -> dict:
    return resolver.derive_plan(
        repo, kit.ruleset_path(repo), envelope, **kwargs
    )


class RulesetDriftTests(unittest.TestCase):
    """Every machine path in the real public ruleset must exist in the real
    module, and every rule must point to a reachable human owner."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = json.loads(
            (MODULE_DIR / "knowledge" / "reduced_stack_rules.json").read_text(
                encoding="utf-8"
            )
        )

    def _module_relative(self, template: str) -> str | None:
        if not template.startswith("{module}/"):
            return None
        return template[len("{module}/"):]

    def test_ruleset_hash_is_current(self) -> None:
        self.assertEqual(
            resolver.compute_ruleset_hash(self.ruleset),
            self.ruleset["ruleset_hash"],
        )

    def test_every_module_path_exists(self) -> None:
        for rule in self.ruleset["rules"]:
            for requirement in rule["requirements"]:
                for template in requirement.get("paths") or []:
                    relative = self._module_relative(template)
                    if relative is None:
                        continue
                    with self.subTest(rule=rule["id"], path=template):
                        self.assertTrue(
                            (MODULE_DIR / relative).is_file(),
                            f"missing module file: {relative}",
                        )

    def test_every_module_glob_meets_its_minimum(self) -> None:
        for rule in self.ruleset["rules"]:
            for requirement in rule["requirements"]:
                pattern = requirement.get("from_glob")
                if not pattern:
                    continue
                relative = self._module_relative(pattern)
                if relative is None:
                    continue
                directory = MODULE_DIR / Path(relative).parent
                name_pattern = Path(relative).name
                matches = [
                    entry
                    for entry in (
                        sorted(p.name for p in directory.iterdir())
                        if directory.is_dir()
                        else []
                    )
                    if fnmatch.fnmatch(entry, name_pattern)
                ]
                with self.subTest(rule=rule["id"], glob=pattern):
                    self.assertGreaterEqual(
                        len(matches), int(requirement["min_count"]),
                        f"glob {pattern} matches too few files",
                    )

    def test_every_rule_has_reachable_human_owner(self) -> None:
        for rule in self.ruleset["rules"]:
            relative = self._module_relative(rule["human_owner"])
            with self.subTest(rule=rule["id"]):
                self.assertIsNotNone(
                    relative, "human_owner must live in the module"
                )
                self.assertTrue(
                    (MODULE_DIR / relative).is_file(),
                    f"unreachable human owner: {rule['human_owner']}",
                )

    def test_semantic_checkers_have_implementations(self) -> None:
        for rule in self.ruleset["rules"]:
            for requirement in rule["requirements"]:
                if requirement["mode"] != "semantic_checker":
                    continue
                checker = requirement["checker_id"]
                with self.subTest(rule=rule["id"], checker=checker):
                    self.assertTrue(
                        (SCRIPTS_DIR / f"{checker}.py").is_file(),
                        f"missing checker implementation: {checker}",
                    )


class ResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.repo = kit.build_fixture_repo(Path(self._temporary.name))

    def test_async_task_loads_family_and_project_override(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=ASYNC_TASK,
            risk_class="normal",
            referenced_paths=["DemoProject/Scripts/Foo.cs"],
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = derive(self.repo, envelope)
        paths = kit.artifact_paths(plan)
        module = kit.MODULE_PREFIX
        for expected in (
            f"{module}/skills/async/base_async_rules.md",
            f"{module}/skills/async/concurrency_classification.md",
            f"{module}/skills/async/main_thread.md",
            f"{module}/skills/async/dotnet_task.md",
            "DemoProject/Assets/AIOutput/ProjectMemory/SkillOverrides/async.md",
            f"{module}/codestyle/csharp.md",
            f"{module}/tasks/start_session.md",
            "Agents.md",
            "DemoProject/Agents.md",
        ):
            self.assertIn(expected, paths)
        override = next(
            artifact
            for artifact in plan["required_artifacts"]
            if artifact["path"].endswith("SkillOverrides/async.md")
        )
        self.assertEqual("project", override["effective_owner"])
        self.assertEqual("async", override["override_family"])
        public_owner = next(
            artifact
            for artifact in plan["required_artifacts"]
            if artifact["path"].endswith("base_async_rules.md")
        )
        self.assertEqual("public", public_owner["effective_owner"])
        self.assertIn("async_threading", plan["matched_rule_ids"])
        self.assertIn(
            "async_threading.project_override",
            {group["group_id"] for group in plan["requirement_groups"]},
        )

    def test_clean_docs_task_does_not_inherit_full_stack(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=DOCS_TASK,
            task_kind="docs_update",
            risk_class="baseline",
            planned_mutation_paths=["DemoProject/README_notes.md"],
        )
        plan = derive(self.repo, envelope)
        paths = kit.artifact_paths(plan)
        module = kit.MODULE_PREFIX
        for forbidden_fragment in (
            "skills/async/", "skills/sdk/", "codestyle/", "policy_packs/",
            "skills/core/",
        ):
            self.assertFalse(
                any(forbidden_fragment in path for path in paths),
                f"docs task inherited {forbidden_fragment}: {sorted(paths)}",
            )
        self.assertIn(f"{module}/tasks/start_session.md", paths)
        self.assertEqual([], plan["semantic_checks"])
        self.assertLessEqual(len(paths), 6)

    def test_cs_task_without_async_keywords_skips_async_family(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = derive(self.repo, envelope)
        paths = kit.artifact_paths(plan)
        self.assertTrue(
            any("codestyle/csharp.md" in path for path in paths)
        )
        self.assertFalse(any("skills/async/" in path for path in paths))

    def test_source_synchronization_types_route_concurrency_owner(self) -> None:
        source_path = self.repo / "DemoProject/Scripts/Coordination.cs"
        repo_path = "DemoProject/Scripts/Coordination.cs"
        snippets = {
            "lock": "lock (_gate) { }",
            "semaphore": "private Semaphore _gate;",
            "mutex": "private Mutex _gate;",
            "reader_writer": "private ReaderWriterLockSlim _gate;",
            "concurrent_stack": "private ConcurrentStack<int> _items;",
        }

        for label, snippet in snippets.items():
            with self.subTest(primitive=label):
                source_path.write_text(
                    f"internal sealed class Coordination {{ {snippet} }}\n",
                    encoding="utf-8",
                )
                envelope = kit.make_envelope(
                    self.repo,
                    task_text="Review the implementation for proportionality.",
                    task_kind="code_review",
                    referenced_paths=[repo_path],
                    planned_mutation_paths=[repo_path],
                )
                plan = derive(self.repo, envelope)
                self.assertIn(
                    "async_sync_primitives_source",
                    plan["matched_rule_ids"],
                )
                self.assertIn(
                    f"{kit.MODULE_PREFIX}/skills/async/"
                    "concurrency_classification.md",
                    kit.artifact_paths(plan),
                )

    def test_branch_review_loads_evidence_provenance_owner(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text="Review this branch diff against release.",
            task_kind="code_review",
            planned_mutation_paths=["review_result/result.json"],
        )
        plan = derive(self.repo, envelope)
        self.assertIn(
            "change_review_provenance", plan["matched_rule_ids"]
        )
        self.assertIn(
            f"{kit.MODULE_PREFIX}/knowledge/review_evidence_provenance.md",
            kit.artifact_paths(plan),
        )

    def test_missing_required_artifact_fails_the_plan(self) -> None:
        (self.repo / kit.MODULE_PREFIX / "skills/async/dotnet_task.md").unlink()
        envelope = kit.make_envelope(self.repo, task_text=ASYNC_TASK)
        with self.assertRaises(resolver.PlanError):
            derive(self.repo, envelope)

    def test_underfilled_required_glob_fails_the_plan(self) -> None:
        (
            self.repo / kit.MODULE_PREFIX / "skills/core/zero_crash_zero_anr.md"
        ).unlink()
        envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        with self.assertRaises(resolver.PlanError):
            derive(self.repo, envelope)

    def test_plan_hash_is_deterministic_and_key_order_independent(self) -> None:
        envelope = kit.make_envelope(self.repo, task_text=ASYNC_TASK)
        reordered = dict(reversed(list(envelope.items())))
        first = derive(self.repo, envelope)
        second = derive(self.repo, reordered)
        self.assertEqual(first["plan_hash"], second["plan_hash"])
        self.assertEqual(first, second)

    def test_tampered_ruleset_hash_is_rejected(self) -> None:
        path = kit.ruleset_path(self.repo)
        document = json.loads(path.read_text(encoding="utf-8"))
        document["rules"][0]["priority"] = 99
        path.write_text(json.dumps(document), encoding="utf-8")
        envelope = kit.make_envelope(self.repo, task_text=DOCS_TASK)
        with self.assertRaises(resolver.ResolverUsageError):
            derive(self.repo, envelope)

    def test_task_text_hash_mismatch_is_rejected(self) -> None:
        envelope = kit.make_envelope(self.repo, task_text=DOCS_TASK)
        envelope["task_text"] = "different text"
        with self.assertRaises(resolver.ResolverUsageError):
            derive(self.repo, envelope)

    def test_high_risk_task_gets_routing_semantic_check(self) -> None:
        contract_path, contract_sha = kit.write_contract(
            Path(self._temporary.name), kit.DEEP_CONTRACT
        )
        envelope = kit.make_envelope(
            self.repo,
            task_text=ASYNC_TASK,
            risk_class="high",
            execution_contract_ref=str(contract_path),
            execution_contract_sha256=contract_sha,
        )
        plan = derive(self.repo, envelope)
        checks = plan["semantic_checks"]
        self.assertEqual(1, len(checks))
        self.assertEqual("routing_gate_check", checks[0]["checker_id"])
        self.assertEqual(contract_sha, checks[0]["input_sha256"])
        self.assertIsNotNone(checks[0]["checker_sha256"])
        self.assertNotIn(
            "semantic_input_missing:routing_gate_check",
            [signal["signal"] for signal in plan["unresolved_signals"]],
        )

    def test_high_risk_without_contract_is_a_critical_signal(self) -> None:
        envelope = kit.make_envelope(
            self.repo, task_text=ASYNC_TASK, risk_class="high"
        )
        plan = derive(self.repo, envelope)
        self.assertIn(
            "semantic_input_missing:routing_gate_check",
            [signal["signal"] for signal in plan["unresolved_signals"]],
        )

    def test_extension_add_and_integrity(self) -> None:
        extra_doc = self.repo / "HostDocs" / "extra.md"
        extra_doc.parent.mkdir()
        extra_doc.write_text("host extra guidance\n", encoding="utf-8")
        extension = {
            "schema_version": "xuunity.reduced-stack-rules.v1",
            "ruleset_id": "host.extension",
            "ruleset_version": "1.0.0",
            "rules": [
                {
                    "id": "host_extra",
                    "description": "Host always requires an extra doc.",
                    "priority": 90,
                    "selectors": {"always": True},
                    "requirements": [
                        {
                            "id": "extra",
                            "mode": "all_of",
                            "paths": ["HostDocs/extra.md"],
                            "weight": 1,
                            "phase": "before_first_mutation",
                        }
                    ],
                    "risk": "baseline",
                    "human_owner": "HostDocs/extra.md",
                }
            ],
        }
        extension["ruleset_hash"] = resolver.compute_ruleset_hash(extension)
        extension_path = Path(self._temporary.name) / "host_extension.json"
        extension_bytes = json.dumps(extension).encode("utf-8")
        extension_path.write_bytes(extension_bytes)
        declaration = {
            "scope": "host",
            "ref": str(extension_path),
            "sha256": xc.sha256_bytes(extension_bytes),
            "parent_hash": kit.ruleset_hash(self.repo),
            "extension_id": "host.extension",
            "extension_version": "1.0.0",
        }
        envelope = kit.make_envelope(
            self.repo, task_text=DOCS_TASK,
            ruleset_extensions=[declaration],
        )
        plan = derive(
            self.repo, envelope, extension_paths=[extension_path]
        )
        self.assertIn("HostDocs/extra.md", kit.artifact_paths(plan))

        tampered = dict(declaration, sha256=xc.sha256_bytes(b"other"))
        envelope_bad = kit.make_envelope(
            self.repo, task_text=DOCS_TASK, ruleset_extensions=[tampered]
        )
        with self.assertRaises(resolver.ResolverUsageError):
            derive(self.repo, envelope_bad, extension_paths=[extension_path])

    def test_extension_duplicate_id_without_extends_fails(self) -> None:
        extension = {
            "schema_version": "xuunity.reduced-stack-rules.v1",
            "ruleset_id": "host.extension",
            "ruleset_version": "1.0.0",
            "rules": [
                {
                    "id": "entrypoint_kernel",
                    "description": "Illegal duplicate.",
                    "priority": 5,
                    "selectors": {"always": True},
                    "requirements": [
                        {
                            "id": "entrypoint",
                            "mode": "all_of",
                            "paths": ["Agents.md"],
                            "weight": 1,
                            "phase": "before_first_mutation",
                        }
                    ],
                    "risk": "baseline",
                    "human_owner": "Agents.md",
                }
            ],
        }
        extension["ruleset_hash"] = resolver.compute_ruleset_hash(extension)
        extension_path = Path(self._temporary.name) / "dup_extension.json"
        extension_bytes = json.dumps(extension).encode("utf-8")
        extension_path.write_bytes(extension_bytes)
        declaration = {
            "scope": "host",
            "ref": str(extension_path),
            "sha256": xc.sha256_bytes(extension_bytes),
            "parent_hash": kit.ruleset_hash(self.repo),
            "extension_id": "host.extension",
            "extension_version": "1.0.0",
        }
        envelope = kit.make_envelope(
            self.repo, task_text=DOCS_TASK, ruleset_extensions=[declaration]
        )
        with self.assertRaises(resolver.PlanError):
            derive(self.repo, envelope, extension_paths=[extension_path])

    def test_mutation_planned_without_project_is_critical(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=DOCS_TASK,
            task_kind="docs_update",
            risk_class="baseline",
            resolved_project=None,
            planned_mutation_paths=["SomeDir/file.md"],
        )
        plan = derive(self.repo, envelope)
        self.assertIn(
            "mutation_planned_without_resolved_project",
            [signal["signal"] for signal in plan["unresolved_signals"]],
        )

    def test_reconcile_additions_are_add_only(self) -> None:
        envelope = kit.make_envelope(
            self.repo,
            task_text=CS_TASK,
            planned_mutation_paths=["DemoProject/Scripts/Foo.cs"],
        )
        plan = derive(self.repo, envelope)
        diff = (
            "diff --git a/DemoProject/Scripts/Foo.cs b/DemoProject/Scripts/Foo.cs\n"
            "--- a/DemoProject/Scripts/Foo.cs\n"
            "+++ b/DemoProject/Scripts/Foo.cs\n"
            "@@ -1 +1,2 @@\n"
            " public class Foo { }\n"
            "+var id = AppsFlyer.getAppsFlyerId();\n"
        )
        result = resolver.reconcile_additions(
            self.repo, kit.ruleset_path(self.repo), envelope, plan, diff
        )
        additions = {
            addition["path"]: addition for addition in result["additions"]
        }
        pack = f"{kit.MODULE_PREFIX}/reviews/policy_packs/sdk_changes.md"
        self.assertIn(pack, additions)
        self.assertEqual("before_closeout", additions[pack]["phase"])
        self.assertFalse(additions[pack]["derivable_from_original_facts"])
        planned_paths = kit.artifact_paths(plan)
        self.assertTrue(planned_paths.issubset(planned_paths | set(additions)))


if __name__ == "__main__":
    unittest.main()
