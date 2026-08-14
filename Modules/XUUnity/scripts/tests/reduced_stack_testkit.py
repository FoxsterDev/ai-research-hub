"""Shared builders for the reduced-stack resolver/loader/gate tests.

Builds a synthetic installation fixture (module + one project) in a temp
directory, plus valid envelopes, ledgers, and attestations. Expected values
are authored here, independent of the resolver implementation."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import xuunity_canonical as xc  # noqa: E402

MODULE_PREFIX = "AIRoot/Modules/XUUnity"
PROJECT = "DemoProject"

MODULE_FILES = [
    "tasks/start_session.md",
    "tasks/feature_development.md",
    "tasks/bug_fixing.md",
    "tasks/refactoring.md",
    "role/base_role.md",
    "codestyle/csharp.md",
    "codestyle/unity.md",
    "skills/core/critical_flow_protection.md",
    "skills/core/mobile_runtime_safety.md",
    "skills/core/sensitive_data_handling.md",
    "skills/core/unity6000_baseline.md",
    "skills/core/zero_crash_zero_anr.md",
    "skills/core/README.md",
    "skills/async/base_async_rules.md",
    "skills/async/main_thread.md",
    "skills/async/dotnet_task.md",
    "skills/async/routing.md",
    "skills/sdk/privacy_compliance.md",
    "skills/sdk/README.md",
    "skills/tests/testing_doctrine.md",
    "skills/mobile/startup.md",
    "reviews/policy_packs/monetization_changes.md",
    "reviews/policy_packs/startup_changes.md",
    "reviews/policy_packs/sdk_changes.md",
    "knowledge/execution_contract.md",
    "knowledge/validation_contract.md",
    "knowledge/risk_classification.md",
    "knowledge/agent_source_of_truth.md",
    "knowledge/detached_callback_attribution.md",
    "utilities/module_session_routing.md",
]

PROJECT_FILES = [
    f"{PROJECT}/Agents.md",
    f"{PROJECT}/Assets/AIOutput/ProjectMemory/coding_constraints.md",
    f"{PROJECT}/Assets/AIOutput/ProjectMemory/SkillOverrides/async.md",
]

DUMMY_HASH = xc.sha256_bytes(b"snapshot")


def build_fixture_repo(root: Path) -> Path:
    repo = Path(root) / "repo"
    (repo / MODULE_PREFIX).mkdir(parents=True)
    (repo / "Agents.md").write_text(
        "# Repo router\nRoute to xuunity start_session.\n", encoding="utf-8"
    )
    for relative in MODULE_FILES:
        target = repo / MODULE_PREFIX / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# {Path(relative).stem}\nguidance body for {relative}\n",
            encoding="utf-8",
        )
    for relative in PROJECT_FILES:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# {Path(relative).stem}\nproject body for {relative}\n",
            encoding="utf-8",
        )
    (repo / PROJECT / "Scripts").mkdir(parents=True)
    (repo / PROJECT / "Scripts/Foo.cs").write_text(
        "public class Foo { public void Bar() { } }\n", encoding="utf-8"
    )
    shutil.copy(
        MODULE_DIR / "knowledge" / "reduced_stack_rules.json",
        repo / MODULE_PREFIX / "knowledge" / "reduced_stack_rules.json",
    )
    return repo


def ruleset_path(repo: Path) -> Path:
    return repo / MODULE_PREFIX / "knowledge" / "reduced_stack_rules.json"


def ruleset_hash(repo: Path) -> str:
    return json.loads(ruleset_path(repo).read_text(encoding="utf-8"))[
        "ruleset_hash"
    ]


def make_envelope(
    repo: Path,
    *,
    task_text: str,
    task_kind: str = "feature_development",
    risk_class: str = "normal",
    referenced_paths: list[str] | None = None,
    planned_mutation_paths: list[str] | None = None,
    resolved_project: str | None = PROJECT,
    execution_contract_ref: str | None = None,
    execution_contract_sha256: str | None = None,
    ruleset_extensions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "xuunity.task-envelope.v1",
        "session_id": "session-test",
        "protocol_id": "xuunity",
        "task_text": task_text,
        "task_text_sha256": xc.sha256_bytes(task_text.encode("utf-8")),
        "task_kind": task_kind,
        "referenced_paths": referenced_paths or [],
        "planned_mutation_paths": planned_mutation_paths or [],
        "resolved_project": resolved_project,
        "execution_contract_ref": execution_contract_ref,
        "execution_contract_sha256": execution_contract_sha256,
        "risk_class": risk_class,
        "trigger_facts": [],
        "repository_content_hash": DUMMY_HASH,
        "protocol_content_hash": DUMMY_HASH,
        "ruleset_hash": ruleset_hash(repo),
        "ruleset_extensions": ruleset_extensions or [],
        "session_attestation_ref": None,
        "session_attestation_sha256": None,
    }


DEEP_CONTRACT = {
    "bug_family": "feature_change",
    "signal": "feature",
    "patch_shape": "local_fix",
    "root_cause_chain_checked": [
        "symptom",
        "immediate caller",
        "service/wrapper",
        "initialization owner",
        "active config/profile",
        "content/manifest availability",
    ],
    "why_not_local_fix": "none",
}

SHALLOW_CONTRACT = {
    "bug_family": "popup_runtime_content_warning",
    "signal": "popup runtime-content warning",
    "patch_shape": "local_fix",
    "runtime_warning": True,
    "remote_content": True,
    "root_cause_chain_checked": ["symptom"],
    "why_not_local_fix": "",
}


def write_contract(root: Path, contract: dict[str, Any]) -> tuple[Path, str]:
    path = Path(root) / "execution_contract.json"
    data = json.dumps(contract, indent=1).encode("utf-8")
    path.write_bytes(data)
    return path, xc.sha256_bytes(data)


def read_event(
    event_id: str,
    path: str,
    sha256: str,
    started_seq: int,
    *,
    success: bool = True,
    actor: str = "root",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "invocation_id": event_id,
        "actor": actor,
        "started_seq": started_seq,
        "completed_seq": started_seq + 1,
        "kind": "read",
        "success": success,
        "targets": [path],
        "expected_sha256": sha256,
        "observed_sha256": sha256 if success else None,
        "parser_result": "recognized",
        "evidence_source": "command_execution",
        "trust": "raw_tool_output",
    }


def mutation_event(
    event_id: str, path: str, started_seq: int
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "invocation_id": event_id,
        "actor": "root",
        "started_seq": started_seq,
        "completed_seq": started_seq + 1,
        "kind": "mutation",
        "success": True,
        "targets": [path],
        "parser_result": "recognized",
        "evidence_source": "file_change",
    }


def ambiguous_event(event_id: str, started_seq: int) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "actor": "root",
        "started_seq": started_seq,
        "completed_seq": started_seq + 1,
        "kind": "ambiguous_command",
        "success": True,
        "targets": [],
        "parser_result": "ambiguous",
        "evidence_source": "command_execution",
    }


def make_ledger(
    events: list[dict[str, Any]],
    *,
    context_manifest: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    requested_model: str = "model-test",
    observed_model: str | None = "model-test",
) -> dict[str, Any]:
    ledger = {
        "schema_version": "xuunity.observation-ledger.v1",
        "collector_identity": {
            "id": "test_collector",
            "version": "1",
            "implementation_sha256": DUMMY_HASH,
        },
        "adapter_contract": {
            "adapter": "test",
            "surface": "test_cli",
            "mutation_coverage": "audited",
            "observable_model_identity": True,
            "runtime_context_paths": ["AGENTS.md"],
            "request_boundary_attestation": False,
        },
        "requested_profile": {"model": requested_model},
        "observed_profile": {"model": observed_model},
        "context_manifest": context_manifest or [],
        "events": events,
        "claims": claims or [],
        "raw_artifact_hashes": {},
    }
    ledger["ledger_hash"] = xc.document_hash(ledger, "ledger_hash")
    return ledger


def proven_events_for_plan(
    plan: dict[str, Any], start_seq: int = 10
) -> list[dict[str, Any]]:
    events = []
    seq = start_seq
    for artifact in plan["required_artifacts"]:
        if artifact["phase"] != "before_first_mutation":
            continue
        events.append(
            read_event(f"read-{seq}", artifact["path"], artifact["sha256"], seq)
        )
        seq += 2
    return events


def make_attestation(repo: Path) -> dict[str, Any]:
    attestation = {
        "schema_version": "xuunity.session-attestation.v1",
        "attestation_id": "att-test-1",
        "session_id": "session-test",
        "task_identity": DUMMY_HASH,
        "repository_content_hash": DUMMY_HASH,
        "protocol_content_hash": DUMMY_HASH,
        "ruleset_hash": ruleset_hash(repo),
        "adapter_profile_hash": DUMMY_HASH,
        "requested_profile": {"model": "model-test"},
        "allowed_roots": {
            "repository": ["."],
            "guidance": ["AIRoot/", "Agents.md", PROJECT],
            "evidence": ["_evidence/"],
            "mutation": [f"{PROJECT}/Scripts/"],
        },
        "policy_ids": {
            "data_classification": "public_synthetic",
            "outbound_delivery": "deny_all",
        },
        "collector_identity": {
            "id": "test_collector",
            "version": "1",
            "implementation_sha256": DUMMY_HASH,
        },
        "broker_identity": {
            "id": "test_broker",
            "version": "1",
            "implementation_sha256": DUMMY_HASH,
        },
        "capability_id": "cap-test-1",
        "created": "2026-07-29T00:00:00Z",
        "expires": "2026-07-30T00:00:00Z",
        "signature": None,
    }
    attestation["attestation_hash"] = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    return attestation


def write_json(root: Path, name: str, document: dict[str, Any]) -> Path:
    path = Path(root) / name
    path.write_text(json.dumps(document, indent=1), encoding="utf-8")
    return path


def artifact_paths(plan: dict[str, Any]) -> set[str]:
    return {artifact["path"] for artifact in plan["required_artifacts"]}
