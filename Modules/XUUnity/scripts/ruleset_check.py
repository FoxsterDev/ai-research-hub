"""Mechanical conformance checker for a reduced-stack ruleset.

The knowledge-integration protocol requires every ruleset edit (new
skill family, new role trigger, changed selectors) to pass this gate in
the same approved change:

1. document conformance — schema, self-hash, duplicate ids, dependency
   cycles, unknown selector families (all fail closed);
2. authored routing probes — hand-written expectations replayed through
   the real resolver against the real repository, so a new rule cannot
   silently over-route an unrelated task (F4 minimality) or drop a
   family/override it was supposed to load (F2 precedence).

Probes are data (`reduced_stack_probes.json` next to the ruleset by
default); the expected answers are authored by humans, never derived by
the resolver under test.

Usage:
    python3 ruleset_check.py --repo-root <repo> [--ruleset <path>]
        [--probes <path>] [--fix-hash]

Exit codes: 0 = pass, 1 = findings, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import reduced_stack_resolver as rsr
import xuunity_canonical as xc

PROBES_BASENAME = "reduced_stack_probes.json"
PROBES_SCHEMA_VERSION = "xuunity.reduced-stack-probes.v1"


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_document(
    repo_root: Path, ruleset_path: Path, *, fix_hash: bool = False
) -> list[str]:
    findings: list[str] = []
    try:
        document = _load_json(ruleset_path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"ruleset unreadable: {error}"]

    computed = rsr.compute_ruleset_hash(document)
    if document.get("ruleset_hash") != computed:
        if fix_hash:
            document["ruleset_hash"] = computed
            Path(ruleset_path).write_text(
                json.dumps(document, indent=2) + "\n", encoding="utf-8"
            )
        else:
            findings.append(
                f"ruleset_hash mismatch: document says "
                f"{document.get('ruleset_hash')}, computed {computed} "
                f"(--fix-hash rewrites it)"
            )

    try:
        loaded = rsr.load_ruleset(Path(ruleset_path), Path(repo_root), [], [])
    except (rsr.ResolverUsageError, rsr.PlanError) as error:
        findings.append(f"ruleset does not load: {error}")
        return findings

    dummy = rsr.Facts(
        task_kind="ruleset-check-probe",
        task_text="",
        protocol_id="ruleset-check",
        risk_class="normal",
        resolved_project=None,
        referenced_paths=[],
        planned_paths=[],
        execution_contract=None,
    )
    for rule in loaded.rules:
        try:
            rsr.rule_matches(rule, dummy)
        except rsr.PlanError as error:
            findings.append(str(error))
    return findings


def probe_envelope(probe: dict[str, Any], ruleset_hash: str) -> dict[str, Any]:
    task_text = str(probe["task_text"])
    return {
        "schema_version": "xuunity.task-envelope.v1",
        "session_id": f"ruleset-check:{probe['id']}",
        "protocol_id": "ruleset-check",
        "task_text": task_text,
        "task_text_ref": None,
        "task_text_sha256": xc.sha256_bytes(task_text.encode("utf-8")),
        "task_kind": probe.get("task_kind") or "ruleset_check_probe",
        "referenced_paths": list(probe.get("referenced_paths") or []),
        "planned_mutation_paths": list(
            probe.get("planned_mutation_paths") or []
        ),
        "resolved_project": probe.get("resolved_project"),
        "execution_contract_ref": None,
        "execution_contract_sha256": None,
        "risk_class": probe.get("risk_class") or "normal",
        "trigger_facts": [
            {"fact": f"ruleset-check probe {probe['id']}", "source": "user_paths"}
        ],
        "repository_content_hash": xc.sha256_bytes(b"ruleset-check-repo"),
        "protocol_content_hash": xc.sha256_bytes(b"ruleset-check-protocol"),
        "ruleset_hash": ruleset_hash,
        "ruleset_extensions": [],
        "session_attestation_ref": None,
        "session_attestation_sha256": None,
    }


def run_probe(
    repo_root: Path, ruleset_path: Path, probe: dict[str, Any]
) -> list[str]:
    probe_id = str(probe.get("id") or "<unnamed>")
    document = _load_json(ruleset_path)
    envelope = probe_envelope(probe, document["ruleset_hash"])
    try:
        plan = rsr.derive_plan(Path(repo_root), Path(ruleset_path), envelope)
    except (rsr.ResolverUsageError, rsr.PlanError) as error:
        return [f"probe {probe_id}: derivation failed: {error}"]

    findings: list[str] = []
    matched = list(plan["matched_rule_ids"])
    exact = probe.get("expect_matched_rule_ids")
    if exact is not None and sorted(exact) != matched:
        findings.append(
            f"probe {probe_id}: matched rules {matched}, "
            f"expected exactly {sorted(exact)}"
        )
    for rule_id in probe.get("expect_rule_ids_include") or []:
        if rule_id not in matched:
            findings.append(
                f"probe {probe_id}: rule {rule_id} did not match"
            )
    for rule_id in probe.get("expect_rule_ids_exclude") or []:
        if rule_id in matched:
            findings.append(
                f"probe {probe_id}: unrelated rule {rule_id} matched"
            )

    artifacts = {
        artifact["path"]: artifact for artifact in plan["required_artifacts"]
    }
    for path in probe.get("expect_artifact_paths_include") or []:
        if path not in artifacts:
            findings.append(
                f"probe {probe_id}: required artifact missing: {path}"
            )
    for path, owner in (probe.get("expect_artifact_owner") or {}).items():
        actual = (artifacts.get(path) or {}).get("effective_owner")
        if actual != owner:
            findings.append(
                f"probe {probe_id}: artifact {path} effective owner "
                f"{actual}, expected {owner}"
            )
    max_bytes = probe.get("max_required_bytes")
    if max_bytes is not None:
        total = sum(
            int(artifact["bytes"]) for artifact in artifacts.values()
        )
        if total > int(max_bytes):
            findings.append(
                f"probe {probe_id}: required stack is {total} bytes, "
                f"budget {max_bytes}"
            )
    return findings


def run_probes(
    repo_root: Path, ruleset_path: Path, probes_path: Path
) -> list[str]:
    try:
        document = _load_json(probes_path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"probes unreadable: {error}"]
    if document.get("schema_version") != PROBES_SCHEMA_VERSION:
        return [
            f"probes schema_version must be {PROBES_SCHEMA_VERSION}"
        ]
    if document.get("authored_by") != "human":
        return [
            "probes must declare authored_by: human — expectations "
            "derived by the resolver under test prove nothing"
        ]
    probes = document.get("probes")
    if not isinstance(probes, list) or not probes:
        return ["probes document declares no probes"]
    findings: list[str] = []
    for probe in probes:
        findings.extend(run_probe(repo_root, ruleset_path, probe))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reduced-stack ruleset conformance checker"
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--ruleset",
        help="defaults to <scripts>/../knowledge/reduced_stack_rules.json",
    )
    parser.add_argument(
        "--probes",
        help=f"defaults to {PROBES_BASENAME} next to the ruleset "
        f"(skipped when absent)",
    )
    parser.add_argument("--fix-hash", action="store_true")
    arguments = parser.parse_args(argv)

    repo_root = Path(arguments.repo_root)
    if not repo_root.is_dir():
        print(f"repo root is not a directory: {repo_root}", file=sys.stderr)
        return 2
    ruleset_path = (
        Path(arguments.ruleset)
        if arguments.ruleset
        else Path(__file__).resolve().parent.parent
        / "knowledge/reduced_stack_rules.json"
    )
    if not ruleset_path.is_file():
        print(f"ruleset not found: {ruleset_path}", file=sys.stderr)
        return 2

    findings = check_document(
        repo_root, ruleset_path, fix_hash=arguments.fix_hash
    )
    probes_path = (
        Path(arguments.probes)
        if arguments.probes
        else ruleset_path.parent / PROBES_BASENAME
    )
    if probes_path.is_file():
        if not findings:
            findings.extend(run_probes(repo_root, ruleset_path, probes_path))
    elif arguments.probes:
        print(f"probes not found: {probes_path}", file=sys.stderr)
        return 2

    if findings:
        for finding in findings:
            print(f"FAIL: {finding}")
        return 1
    print("ruleset check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
