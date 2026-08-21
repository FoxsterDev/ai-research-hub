from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = SCRIPTS_DIR.parent / "schemas"

sys.path.insert(0, str(SCRIPTS_DIR))
import observation_contract as oc  # noqa: E402


def _validate(schema: dict, document: Any, root: dict, path: str = "$") -> list[str]:
    """Minimal structural validator for the subset of JSON Schema these
    contracts use: type, const, enum, required, properties,
    additionalProperties, items, minItems/maxItems, minLength,
    minimum/maximum, pattern, anyOf, and local $ref."""
    errors: list[str] = []
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        return _validate(target, document, root, path)
    if "anyOf" in schema:
        candidates = [
            _validate(option, document, root, path)
            for option in schema["anyOf"]
        ]
        if not any(not errs for errs in candidates):
            errors.append(f"{path}: no anyOf branch matched")
        return errors
    if "const" in schema and document != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and document not in schema["enum"]:
        errors.append(f"{path}: {document!r} not in enum")
    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }
        if not any(checks[name](document) for name in types):
            errors.append(f"{path}: type {types} expected")
            return errors
    if isinstance(document, str):
        if "minLength" in schema and len(document) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength")
        if "pattern" in schema and not re.search(schema["pattern"], document):
            errors.append(f"{path}: pattern mismatch")
    if isinstance(document, (int, float)) and not isinstance(document, bool):
        if "minimum" in schema and document < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and document > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(document, dict):
        for key in schema.get("required", []):
            if key not in document:
                errors.append(f"{path}: missing required {key}")
        properties = schema.get("properties", {})
        for key, value in document.items():
            if key in properties:
                errors.extend(_validate(properties[key], value, root, f"{path}.{key}"))
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(
                    _validate(
                        schema["additionalProperties"], value, root, f"{path}.{key}"
                    )
                )
    if isinstance(document, list):
        if "minItems" in schema and len(document) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(document) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems")
        if isinstance(schema.get("items"), dict):
            for index, value in enumerate(document):
                errors.extend(
                    _validate(schema["items"], value, root, f"{path}[{index}]")
                )
    return errors


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


SHA = "0" * 64


def golden_ledger() -> dict:
    return {
        "schema_version": "xuunity.observation-ledger.v1",
        "collector_identity": {
            "id": "host_compat_scorer",
            "version": "4",
            "implementation_sha256": SHA,
        },
        "adapter_contract": {
            "adapter": "codex",
            "surface": "codex_cli_headless",
            "adapter_cli_version": "codex-cli 0.146.0",
            "sandbox": "workspace-write",
            "expected_permission_mode": None,
            "tool_profile": "codex_default",
            "mutation_coverage": "audited",
            "observable_model_identity": False,
            "runtime_context_paths": ["AGENTS.md"],
            "request_boundary_attestation": False,
        },
        "requested_profile": {"model": "gpt-test", "effort": "max"},
        "observed_profile": {"model": None},
        "context_manifest": [
            {"path": "Agents.md", "trust": "unverified", "case_alias": True}
        ],
        "events": [
            {
                "event_id": "item_1",
                "invocation_id": "item_1",
                "actor": "root",
                "started_seq": 3,
                "completed_seq": 4,
                "kind": "read",
                "success": True,
                "targets": ["AIRoot/entry.md"],
                "expected_sha256": SHA,
                "observed_sha256": SHA,
                "line_intervals": [[1, 12]],
                "parser_result": "recognized",
                "evidence_source": "command_execution",
                "trust": "raw_tool_output",
            },
            {
                "event_id": "item_2",
                "invocation_id": "item_2",
                "actor": "root",
                "started_seq": 5,
                "completed_seq": 6,
                "kind": "ambiguous_command",
                "success": True,
                "targets": [],
                "parser_result": "ambiguous",
                "evidence_source": "command_execution",
                "command_sha256": SHA,
            },
        ],
        "claims": [
            {"seq": 7, "actor": "root", "claimed_paths": ["AIRoot/entry.md"]}
        ],
        "artifact_observations": [
            {
                "path": "AIRoot/entry.md",
                "state": "proven_delivered",
                "direct_state": "proven_delivered",
                "evidence_event_ids": ["item_1"],
                "unsupported_present": False,
                "runtime_unverified_present": False,
            },
            {
                "path": "Agents.md",
                "state": "runtime_delivered_unverified",
                "direct_state": "not_observed",
                "evidence_event_ids": [],
                "unsupported_present": False,
                "runtime_unverified_present": True,
                "case_alias": True,
            },
        ],
        "raw_artifact_hashes": {"transcript.jsonl": SHA},
        "ledger_hash": SHA,
    }


def golden_gate_result() -> dict:
    return {
        "schema_version": "xuunity.stack-gate-result.v1",
        "decision": "fail",
        "enforcement_mode": "audited",
        "plan_hash": SHA,
        "ledger_hash": SHA,
        "session_attestation_id": None,
        "mutation_cutoff": {
            "started_seq": 20,
            "completed_seq": 21,
            "event_id": "item_9",
            "mechanism": "file_change",
            "target": "Project/File.cs",
            "actor": "root",
        },
        "mutation_cutoff_confidence": "unambiguous",
        "group_results": [
            {
                "group_id": "entrypoints",
                "mode": "all_of",
                "weight": 2,
                "min_count": None,
                "gate_satisfied": False,
                "leaf_fraction": 0.5,
                "members": [
                    {
                        "path": "AIRoot/entry.md",
                        "state": "proven_delivered",
                        "evidence_event_ids": ["item_1"],
                    },
                    {
                        "path": "Agents.md",
                        "state": "runtime_delivered_unverified",
                        "evidence_event_ids": [],
                        "case_alias": True,
                    },
                ],
            }
        ],
        "semantic_check_results": [],
        "unsupported_events": [],
        "ambiguous_events": [
            {
                "event_id": "item_2",
                "started_seq": 5,
                "completed_seq": 6,
                "programs": ["python3"],
                "command_sha256": SHA,
                "required_paths_mentioned": [],
                "before_mutation_cutoff": True,
            }
        ],
        "post_diff_additions": [],
        "reason_codes": ["runtime_context_unverified:Agents.md"],
        "authorization": None,
    }


class SchemaValidationTests(unittest.TestCase):
    def test_golden_ledger_validates(self) -> None:
        schema = load_schema("xuunity.observation-ledger.schema.json")
        self.assertEqual([], _validate(schema, golden_ledger(), schema))

    def test_ledger_rejects_unknown_observation_state(self) -> None:
        schema = load_schema("xuunity.observation-ledger.schema.json")
        ledger = golden_ledger()
        ledger["artifact_observations"][0]["state"] = "loaded"
        self.assertTrue(_validate(schema, ledger, schema))

    def test_ledger_rejects_missing_required_top_level_field(self) -> None:
        schema = load_schema("xuunity.observation-ledger.schema.json")
        for field in (
            "collector_identity",
            "adapter_contract",
            "context_manifest",
            "claims",
            "ledger_hash",
        ):
            ledger = golden_ledger()
            del ledger[field]
            with self.subTest(field=field):
                self.assertTrue(_validate(schema, ledger, schema))

    def test_ledger_rejects_unknown_parser_result_and_actor(self) -> None:
        schema = load_schema("xuunity.observation-ledger.schema.json")
        ledger = golden_ledger()
        ledger["events"][0]["parser_result"] = "guessed"
        self.assertTrue(_validate(schema, ledger, schema))
        ledger = golden_ledger()
        ledger["events"][0]["actor"] = "model"
        self.assertTrue(_validate(schema, ledger, schema))

    def test_golden_gate_result_validates(self) -> None:
        schema = load_schema("xuunity.stack-gate-result.schema.json")
        self.assertEqual([], _validate(schema, golden_gate_result(), schema))

    def test_gate_result_rejects_unknown_decision_or_mode(self) -> None:
        schema = load_schema("xuunity.stack-gate-result.schema.json")
        document = golden_gate_result()
        document["decision"] = "mostly_pass"
        self.assertTrue(_validate(schema, document, schema))
        document = golden_gate_result()
        document["enforcement_mode"] = "advisory_plus"
        self.assertTrue(_validate(schema, document, schema))


class TaxonomyTests(unittest.TestCase):
    def test_only_proven_and_trusted_satisfy_delivery(self) -> None:
        satisfying = {
            state
            for state in oc.OBSERVATION_STATES
            if oc.state_satisfies_delivery(state)
        }
        self.assertEqual(
            {"proven_delivered", "trusted_runtime_delivered"}, satisfying
        )
        with self.assertRaises(ValueError):
            oc.state_satisfies_delivery("loaded")

    def test_unsupported_is_never_reported_as_absence(self) -> None:
        row = oc.resolve_artifact_state([], unsupported_present=True)
        self.assertEqual("unsupported_observation", row.state)
        self.assertNotEqual("not_observed", row.state)
        self.assertFalse(row.satisfied)
        self.assertTrue(row.blocks_observer)

    def test_runtime_unverified_blocks_observer_but_proven_wins(self) -> None:
        unverified = oc.resolve_artifact_state(
            [], runtime_unverified_present=True, case_alias=True
        )
        self.assertEqual("runtime_delivered_unverified", unverified.state)
        self.assertTrue(unverified.blocks_observer)

        proven = oc.resolve_artifact_state(
            ["proven_delivered"],
            unsupported_present=True,
            runtime_unverified_present=True,
        )
        self.assertEqual("proven_delivered", proven.state)
        self.assertTrue(proven.satisfied)
        self.assertFalse(proven.blocks_observer)

    def test_partial_and_failed_precedence(self) -> None:
        row = oc.resolve_artifact_state(["failed_read", "partial_read"])
        self.assertEqual("partial_read", row.state)
        self.assertFalse(row.satisfied)
        self.assertFalse(row.blocks_observer)

    def test_epistemic_states_rejected_as_direct_evidence(self) -> None:
        with self.assertRaises(ValueError):
            oc.resolve_artifact_state(["unsupported_observation"])

    def test_observer_axis_precedence(self) -> None:
        blocked = oc.resolve_artifact_state([], unsupported_present=True)
        clean = oc.resolve_artifact_state(["proven_delivered"])
        self.assertEqual(
            "observer_invalid",
            oc.observer_axis(
                profile_mismatch=True,
                boundary_ambiguous=True,
                artifact_resolutions=[blocked],
            ),
        )
        self.assertEqual(
            "observer_unsupported",
            oc.observer_axis(
                profile_mismatch=False,
                boundary_ambiguous=True,
                artifact_resolutions=[clean],
            ),
        )
        self.assertEqual(
            "observer_unsupported",
            oc.observer_axis(
                profile_mismatch=False,
                boundary_ambiguous=False,
                artifact_resolutions=[clean, blocked],
            ),
        )
        self.assertEqual(
            "valid",
            oc.observer_axis(
                profile_mismatch=False,
                boundary_ambiguous=False,
                artifact_resolutions=[clean],
            ),
        )

    def test_group_satisfaction_keeps_leaf_fraction_on_failure(self) -> None:
        policy = oc.GroupPolicy(
            group_id="g", mode="all_of", weight=4, members=("a", "b", "c", "d")
        )
        satisfied, fraction = oc.group_satisfaction(policy, {"a", "b", "c"})
        self.assertFalse(satisfied)
        self.assertEqual(0.75, fraction)

        any_policy = oc.GroupPolicy(
            group_id="g2", mode="any_of", weight=1, members=("a", "z")
        )
        self.assertEqual((True, 1.0), oc.group_satisfaction(any_policy, {"a"}))

        at_least = oc.GroupPolicy(
            group_id="g3",
            mode="at_least",
            weight=2,
            min_count=2,
            glob="skills/*.md",
            matched_paths=("skills/a.md", "skills/b.md", "skills/c.md"),
        )
        self.assertEqual(
            (False, 0.5), oc.group_satisfaction(at_least, {"skills/a.md"})
        )
        self.assertEqual(
            (True, 1.0),
            oc.group_satisfaction(at_least, {"skills/a.md", "skills/b.md"}),
        )

    def test_delivery_percent_is_leaf_weighted(self) -> None:
        full = oc.GroupPolicy("g1", "all_of", 2, ("a", "b"))
        half = oc.GroupPolicy("g2", "all_of", 2, ("c", "d"))
        percent = oc.delivery_percent(
            [
                (full, oc.group_satisfaction(full, {"a", "b"})[1]),
                (half, oc.group_satisfaction(half, {"c"})[1]),
            ]
        )
        self.assertEqual(75.0, percent)
        self.assertEqual(100.0, oc.delivery_percent([]))

    def test_runtime_context_channels_and_case_alias(self) -> None:
        self.assertEqual((True, True), oc.runtime_context_match("codex_cli", "Agents.md"))
        self.assertEqual(
            (True, True),
            oc.runtime_context_match("codex_cli", "ExampleProject/Agents.md"),
        )
        self.assertEqual((True, False), oc.runtime_context_match("codex_cli", "AGENTS.md"))
        self.assertEqual(
            (False, False),
            oc.runtime_context_match("codex_cli", "AIRoot/entry.md"),
        )
        self.assertEqual(
            (True, False), oc.runtime_context_match("claude_cli", "CLAUDE.md")
        )
        self.assertEqual(
            (False, False), oc.runtime_context_match("claude_cli", "Agents.md")
        )

    def test_profile_identity_check(self) -> None:
        match = oc.profile_identity_check("m1", "m1")
        self.assertFalse(match["mismatch"])
        mismatch = oc.profile_identity_check("m1", "m2")
        self.assertTrue(mismatch["mismatch"])
        unobserved = oc.profile_identity_check("m1", None)
        self.assertFalse(unobserved["mismatch"])
        self.assertEqual(
            "matched_content_noncontrolled", unobserved["comparison_status"]
        )

    def test_gate_result_semantic_rules(self) -> None:
        document = golden_gate_result()
        self.assertEqual([], oc.gate_result_semantic_errors(document))

        audited_with_authorization = golden_gate_result()
        audited_with_authorization["authorization"] = {
            "capability_id": "cap",
            "expires": "later",
            "mutation_generation": 0,
        }
        self.assertTrue(
            oc.gate_result_semantic_errors(audited_with_authorization)
        )

        authoritative_without = golden_gate_result()
        authoritative_without["enforcement_mode"] = "authoritative"
        self.assertTrue(oc.gate_result_semantic_errors(authoritative_without))

        pass_with_unsatisfied = golden_gate_result()
        pass_with_unsatisfied["decision"] = "pass"
        self.assertTrue(oc.gate_result_semantic_errors(pass_with_unsatisfied))

        ambiguous_pass = golden_gate_result()
        ambiguous_pass["decision"] = "pass"
        ambiguous_pass["group_results"] = []
        ambiguous_pass["mutation_cutoff_confidence"] = "ambiguous_prior_commands"
        self.assertTrue(oc.gate_result_semantic_errors(ambiguous_pass))


if __name__ == "__main__":
    unittest.main()
