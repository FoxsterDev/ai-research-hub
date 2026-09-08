"""Explicit-input audited CLI execution and artifact-only replay.

No installed hookless CLI can mint authoritative writes or outbound-request
delivery evidence. This path preserves useful diagnostics and independent
outcomes while leaving those measurements null.
"""

from __future__ import annotations

import difflib
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import reduced_stack_loader as loader
import reduced_stack_resolver as resolver
import xuunity_canonical as xc

from . import MODULE_SCRIPTS_DIR, OPERATION_DIR, adapters, attestation, baseline, calibration, causes
from . import fixtures, processes, profiles, records, schedule, scoring, suite as suites
from .contracts import require_valid


def validate_tree(root: Path) -> None:
    root = Path(root).resolve()
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            xc.normalize_repo_path(path.relative_to(root).as_posix())
            mode = path.lstat()
            if path.is_symlink():
                if Path(os.readlink(path)).is_absolute() or not path.resolve().is_relative_to(root):
                    raise ValueError("snapshot_symlink_escapes_namespace")
            elif stat.S_ISREG(mode.st_mode) and mode.st_nlink != 1:
                raise ValueError("snapshot_hardlink_unaccounted")
            elif not (stat.S_ISREG(mode.st_mode) or stat.S_ISDIR(mode.st_mode)):
                raise ValueError("snapshot_special_file")


def capture_tree(source: Path, destination: Path) -> str:
    validate_tree(source)
    before = baseline.content_identity(source)
    shutil.copytree(source, destination, symlinks=True)
    validate_tree(destination)
    captured = baseline.content_identity(destination)
    if before != captured or before != baseline.content_identity(source):
        raise ValueError("source_changed_during_capture")
    return captured


def tree_diff(seed: Path, final: Path) -> tuple[str, list[str]]:
    before = {row["path"]: row for row in baseline.content_entries(seed)}
    after = {row["path"]: row for row in baseline.content_entries(final)}
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    text = []

    def body(root: Path, path: str, exists: bool) -> list[str]:
        if not exists:
            return []
        target = root / path
        data = os.readlink(target).encode() if target.is_symlink() else target.read_bytes()
        return data.decode("utf-8").splitlines(keepends=True)

    for path in changed:
        text.append(f"diff --git {json.dumps('a/' + path)} {json.dumps('b/' + path)}\n")
        try:
            old = body(seed, path, path in before)
            new = body(final, path, path in after)
            text.extend(difflib.unified_diff(old, new,
                        fromfile=f"a/{path}" if path in before else "/dev/null",
                        tofile=f"b/{path}" if path in after else "/dev/null"))
        except UnicodeDecodeError:
            text.append("Binary files differ\n")
        if before.get(path, {}).get("mode") != after.get(path, {}).get("mode"):
            text.append(f"old mode {before.get(path, {}).get('mode', '000000')}\n")
            text.append(f"new mode {after.get(path, {}).get('mode', '000000')}\n")
    return "".join(text), changed


def prepare(
    fixture_dir: Path, *, output: Path, seed: Path | None = None,
    task_text: str | None = None, ruleset_relative: str,
    planned_paths: list[str], project: str | None = None,
    protocol_content_hash: str | None = None,
    semantic_input_manifest: Path | None = None,
    implementation_dependencies: dict[str, Path] | None = None,
    suite_document: dict | None = None,
    task_kind: str = "feature_development", risk_class: str = "normal",
    referenced_paths: list[str] | None = None, ruleset_extensions: list[Path] | None = None,
) -> dict[str, Any]:
    fixture_dir = Path(fixture_dir).resolve()
    output = Path(output).resolve()
    fixture = fixtures.verify_fixture(fixture_dir, require_local_payloads=seed is None)
    if suite_document is not None:
        suites.validate_suite(suite_document)
        if not any(row["fixture_id"] == fixture["fixture_id"] and row["fixture_sha256"] == fixture["fixture_hash"]
                   for row in suite_document["fixtures"]):
            raise ValueError("prepared_fixture_not_in_suite")
    seed = Path(seed).resolve() if seed else fixture_dir / fixture["seed"]["ref"]
    records.disjoint(seed, output)
    records.disjoint(fixture_dir, output)
    validate_tree(seed)
    if baseline.content_identity(seed) != fixture["seed"]["content_hash"]:
        raise ValueError("prepared_seed_identity_mismatch")
    task_text = task_text if task_text is not None else (fixture_dir / fixture["task"]["ref"]).read_text()
    if xc.sha256_bytes(task_text.encode()) != fixture["task"]["sha256"]:
        raise ValueError("prepared_task_identity_mismatch")
    if loader.scan_for_secrets("task.txt", task_text.encode()):
        raise ValueError("secret_bearing_task_payload")
    ruleset_relative = xc.normalize_repo_path(ruleset_relative)
    ruleset = xc.load_strict(seed / ruleset_relative)
    extensions = [Path(p).resolve() for p in ruleset_extensions or []]
    extension_rows = []
    for index, path in enumerate(extensions):
        document = records.read(path)
        extension_rows.append({"scope": "host", "ref": f"extension-{index}.json", "sha256": xc.sha256_file(path),
                               "parent_hash": ruleset["ruleset_hash"], "extension_id": document["ruleset_id"],
                               "extension_version": document["ruleset_version"]})
    semantic_inputs = records.read(semantic_input_manifest) if semantic_input_manifest else {"inputs": []}
    execution_contract = None
    contract_hash = None
    contract_ref = None
    for index, entry in enumerate(semantic_inputs["inputs"]):
        payload = records.read(Path(entry["ref"]))
        if entry["checker_id"] == "routing_gate_check":
            execution_contract, contract_hash = payload, xc.sha256_file(Path(entry["ref"]))
            contract_ref = f"semantic-payload-{index}.json"
    protocol_hash = protocol_content_hash or baseline.content_identity((seed / ruleset_relative).parent.parent)
    envelope = {
        "schema_version": "xuunity.task-envelope.v1", "session_id": "prepared",
        "protocol_id": "xuunity", "task_text": task_text, "task_text_ref": None,
        "task_text_sha256": fixture["task"]["sha256"], "task_kind": task_kind,
        "referenced_paths": list(referenced_paths or planned_paths), "planned_mutation_paths": list(planned_paths),
        "resolved_project": project, "execution_contract_ref": contract_ref,
        "execution_contract_sha256": contract_hash, "risk_class": risk_class,
        "trigger_facts": [{"fact": "fixture-authored-input", "source": "user_paths"}],
        "repository_content_hash": fixture["seed"]["content_hash"],
        "protocol_content_hash": protocol_hash, "ruleset_hash": ruleset["ruleset_hash"],
        "ruleset_extensions": extension_rows, "session_attestation_ref": None, "session_attestation_sha256": None,
    }
    require_valid("xuunity.task-envelope.schema.json", envelope, "prepared envelope")
    plan = resolver.derive_plan(seed, seed / ruleset_relative, envelope, extension_paths=extensions,
                                execution_contract=execution_contract)
    bundle, bundle_manifest = loader.build_bundle(seed, plan)
    expected = fixtures.load_expected_stack(fixture_dir)
    expected_paths = set()
    for group in expected["groups"]:
        members = list(group.get("members") or [])
        if group.get("glob"):
            members.extend(p.relative_to(seed).as_posix() for p in seed.glob(group["glob"]) if p.is_file())
        if any(not (seed / p).is_file() for p in members):
            raise ValueError("authored_fixture_obligation_missing")
        if group.get("min_count", 0) > len(set(members)):
            raise ValueError("authored_fixture_obligation_denominator_missing")
        expected_paths.update(members)
    derived_paths = {row["path"] for row in plan["required_artifacts"]}
    if not expected_paths.issubset(derived_paths):
        raise ValueError("resolver_missing_authored_fixture_obligations:" + ",".join(sorted(expected_paths - derived_paths)))
    manifest = fixtures.default_manifest(seed, sorted(expected_paths | derived_paths))
    output.mkdir(parents=True, exist_ok=False)
    identity, stored = baseline.materialize_seed(seed, output / "seeds")
    records.write(output / "envelope.json", envelope, exclusive=True)
    records.write(output / "stack-plan.json", plan, exclusive=True)
    records.write(output / "bundle-manifest.json", bundle_manifest, exclusive=True)
    (output / "task.txt").write_text(task_text)
    (output / "bundle.txt").write_bytes(bundle)
    for index, path in enumerate(extensions):
        shutil.copyfile(path, output / f"extension-{index}.json")
    if semantic_input_manifest:
        frozen_inputs = []
        for index, entry in enumerate(semantic_inputs["inputs"]):
            target = output / f"semantic-payload-{index}.json"
            shutil.copyfile(Path(entry["ref"]), target)
            frozen_inputs.append({**entry, "ref": str(target)})
        records.write(output / "semantic-inputs.json", {"inputs": frozen_inputs}, exclusive=True)
    if suite_document is not None:
        records.write(output / "suite.json", suite_document, exclusive=True)
    record = records.seal({
        "schema_version": "xuunity.prepared-attempt.v1", "fixture_dir": str(fixture_dir),
        "fixture": fixture, "seed_store": str(output / "seeds"), "seed_identity": identity,
        "ruleset_relative": ruleset_relative, "protocol_content_hash": protocol_hash,
        "ruleset_hash": ruleset["ruleset_hash"], "engine_identity": profiles.engine_identity(),
        "ruleset_extensions": extension_rows,
        "effective_ruleset_hash": xc.domain_digest("xuunity.effective-ruleset.v1", {
            "base": ruleset["ruleset_hash"], "extensions": extension_rows}) if extension_rows else ruleset["ruleset_hash"],
        "suite_identity": {"suite_id": suite_document["suite_id"], "suite_revision": suite_document["revision"],
                           "suite_hash": suites.suite_hash(suite_document)} if suite_document is not None else None,
        "implementation_dependencies": {name: {"path": str(Path(path).resolve()), "sha256": xc.sha256_file(Path(path))}
                                         for name, path in (implementation_dependencies or {}).items()},
        "manifest": manifest, "source_artifact_hashes": {
            p.name: xc.sha256_file(p) for p in output.iterdir() if p.is_file()
        },
    })
    records.write(output / "prepared.json", record, exclusive=True)
    return record


def verify_prepared(path: Path) -> dict[str, Any]:
    prepared = records.read(path)
    records.verify(prepared)
    if prepared["engine_identity"] != profiles.engine_identity():
        raise ValueError("prepared_engine_identity_stale")
    for dependency in prepared.get("implementation_dependencies", {}).values():
        if xc.sha256_file(Path(dependency["path"])) != dependency["sha256"]:
            raise ValueError("prepared_implementation_dependency_changed")
    fixture = fixtures.verify_fixture(Path(prepared["fixture_dir"]), require_local_payloads=False)
    if fixture != prepared["fixture"]:
        raise ValueError("prepared_fixture_changed")
    for name, digest in prepared["source_artifact_hashes"].items():
        if xc.normalize_repo_path(name) != name or "/" in name or xc.sha256_file(path.parent / name) != digest:
            raise ValueError("prepared_artifact_changed")
    if baseline.content_identity(Path(prepared["seed_store"]) / prepared["seed_identity"]) != prepared["seed_identity"]:
        raise ValueError("prepared_seed_changed")
    return prepared


def comparison_fields(prepared: dict[str, Any], installed: dict[str, Any], observed_model: str | None,
                      toolchain_versions: dict | None = None) -> tuple[dict, dict]:
    fixture = prepared["fixture"]
    profile = installed["profile"]
    task_fields = {
        "fixture_id": fixture["fixture_id"], "fixture_revision": fixture["revision"],
        "fixture_hash": fixture["fixture_hash"], "suite_id": "standalone",
        "suite_revision": "1", "suite_hash": xc.sha256_bytes(b"standalone"),
        "task_prompt_hash": fixture["task"]["sha256"], "base_content_hash": prepared["seed_identity"],
        "protocol_content_hash": prepared["protocol_content_hash"], "ruleset_hash": prepared.get("effective_ruleset_hash", prepared["ruleset_hash"]),
        "runner_hash": xc.domain_digest("xuunity.bound-executor.v1", {
            "engine": prepared["engine_identity"],
            "dependencies": {name: row["sha256"] for name, row in prepared.get("implementation_dependencies", {}).items()},
        }), "observer_hash": installed["parser_sha256"],
        "scorer_hash": xc.sha256_file(OPERATION_DIR / "model_fitness/scoring.py"),
        "cause_classifier_hash": xc.sha256_file(OPERATION_DIR / "model_fitness/causes.py"),
        "statistical_method_hash": xc.sha256_file(OPERATION_DIR / "model_fitness/stats.py"),
        "oracle_schema_versions": [row["implementation_sha256"] for row in fixture["semantic_oracles"]],
    }
    if prepared.get("suite_identity"):
        task_fields.update(prepared["suite_identity"])
    profile_fields = {
        "requested_model": profile["requested_model"], "observed_model": observed_model,
        "reasoning_effort": profile["inference_parameters"]["effort"], "surface": profile["surface"],
        "adapter_id": profile["adapter_id"], "adapter_version": profile["adapter_version"],
        "parser_capability_hash": installed["parser_sha256"], "sandbox": profile["sandbox"],
        "permission_mode": profile["permission_mode"], "approval_policy": profile["approval_policy"],
        "tool_contract": profile["tools"], "context_delivery_mode": "unattested_stdin_bundle",
        "enforcement_level": "audited", "os": installed["os"], "architecture": installed["architecture"],
        "toolchain_versions": toolchain_versions or {}, "cache_image": None, "clean_cache_policy": "fresh_oracle_materialization",
        "locale": os.environ.get("LANG"), "timezone": os.environ.get("TZ"),
        "network_policy_hash": profile["network_policy_hash"],
        "environment_allowlist_hash": profile["environment_allowlist_hash"],
        "read_namespace_policy_hash": profile["read_namespace_policy_hash"], "replay_corpus_hash": None,
        "inference_parameters": profile["inference_parameters"], "provider_backend_revision": None,
    }
    return task_fields, profile_fields


def observation_ledger(normalized: dict, installed: dict, manifest: dict, raw_hashes: dict) -> dict:
    rows = []
    for read in normalized["reads"]:
        rows.append({
            "event_id": read.event_id, "actor": read.actor, "started_seq": read.seq,
            "completed_seq": read.completed_seq, "kind": "read", "success": read.proof != "failed",
            "targets": [read.path], "parser_result": "unsupported",
            "evidence_source": read.mechanism, "trust": "raw_tool_output",
        })
    for mutation in normalized["mutations"]:
        rows.append({
            "event_id": mutation.event_id, "actor": mutation.actor, "started_seq": mutation.seq,
            "completed_seq": mutation.completed_seq, "kind": "mutation", "success": mutation.succeeded,
            "targets": [mutation.path], "parser_result": "recognized", "evidence_source": mutation.mechanism,
        })
    for flag in normalized["flags"]:
        rows.append({
            "event_id": flag.event_id, "actor": flag.actor, "started_seq": flag.seq,
            "completed_seq": flag.completed_seq,
            "kind": "ambiguous_command" if flag.parser_result == "ambiguous" else "unsupported_command",
            "parser_result": flag.parser_result, "evidence_source": "cli_event",
            "targets": list(flag.required_paths),
        })
    rows.sort(key=lambda row: row["started_seq"] if row["started_seq"] is not None else 0)
    profile = installed["profile"]
    _, contract = profiles.command(installed, Path("."))
    ledger = {
        "schema_version": "xuunity.observation-ledger.v1",
        "collector_identity": {"id": "fitness-cli-executor", "version": "1", "implementation_sha256": xc.sha256_file(Path(__file__))},
        "adapter_contract": contract, "requested_profile": {"model": profile["requested_model"]},
        "observed_profile": {"model": normalized.get("observed_model")},
        "context_manifest": [{"path": path, "sha256": value["sha256"], "trust": "unverified"}
                             for path, value in sorted(manifest.items())],
        "events": rows, "claims": [], "raw_artifact_hashes": raw_hashes,
    }
    ledger["ledger_hash"] = xc.document_hash(ledger, "ledger_hash")
    require_valid("xuunity.observation-ledger.schema.json", ledger, "executor ledger")
    return ledger


def gate(preparation: Path, evidence: Path, *, final: Path | None = None) -> dict:
    prepared = records.read(preparation / "prepared.json")
    output = evidence / ("reconcile.json" if final else "gate.json")
    argv = [sys.executable, str(MODULE_SCRIPTS_DIR / "reduced_stack_gate.py"),
            "reconcile" if final else "check", "--plan", str(preparation / "stack-plan.json"),
            "--ledger", str(evidence / "ledger.json"), "--output", str(output)]
    if (preparation / "semantic-inputs.json").exists():
        argv += ["--semantic-input-manifest", str(preparation / "semantic-inputs.json")]
    if final:
        argv += ["--repo-root", str(final), "--ruleset", str(final / prepared["ruleset_relative"]),
                 "--task-envelope", str(preparation / "envelope.json"),
                 "--parent-diff", str(evidence / "diff.patch")]
        for row in prepared.get("ruleset_extensions", []):
            argv += ["--ruleset-extension", str(preparation / row["ref"])]
    env, _ = profiles.environment()
    process = subprocess.run(argv, env=env, capture_output=True, timeout=60)
    if process.returncode not in {0, 1, 3, 4} or not output.is_file():
        (evidence / "gate-error.txt").write_bytes(process.stdout + process.stderr)
        raise ValueError("gate_execution_failed")
    return records.read(output)


def _manifest(evidence: Path, prepared: dict, installed: dict, session: dict,
              *, observed_model: str | None = None, end_state: dict | None = None,
              raw: dict | None = None, toolchain_versions: dict | None = None) -> dict:
    task, profile = comparison_fields(prepared, installed, observed_model, toolchain_versions)
    tree = end_state.get("final_tree_identity") if end_state else None
    return attestation.build_protected_run_manifest(
        attempt_id=evidence.name, session_attestation=session,
        inputs={"fixture_id": prepared["fixture"]["fixture_id"],
                "fixture_hash": prepared["fixture"]["fixture_hash"],
                "seed_identity": prepared["seed_identity"],
                "protocol_content_hash": prepared["protocol_content_hash"],
                "ruleset_hash": prepared["ruleset_hash"],
                "task_identity": prepared["fixture"]["task"]["sha256"]},
        task_measurement_key=baseline.task_measurement_key(task),
        strict_profile_key=baseline.strict_profile_key(task, profile),
        started=session["created"], raw_evidence_hashes=raw or {},
        end_state=end_state,
        oracle_materialization={"identity": tree, "ref": "final-tree"} if tree else None,
    )


def _start_session(evidence: Path, prepared: dict, installed: dict) -> None:
    key = secrets.token_bytes(32)
    key_path = evidence.parent / ".session-keys" / (evidence.name + ".key")
    key_path.parent.mkdir(exist_ok=True)
    descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(key)
        stream.flush()
        os.fsync(stream.fileno())
    component = {"id": "fitness-cli-executor", "version": "1",
                 "implementation_sha256": xc.sha256_file(Path(__file__))}
    now = datetime.now(timezone.utc)
    session = attestation.build_session_attestation(
        key, session_id=evidence.name, task_identity=prepared["fixture"]["task"]["sha256"],
        repository_content_hash=prepared["seed_identity"],
        protocol_content_hash=prepared["protocol_content_hash"], ruleset_hash=prepared["ruleset_hash"],
        adapter_profile_hash=installed["profile"]["profile_hash"],
        requested_profile={"model": installed["profile"]["requested_model"]},
        allowed_roots={"repository": ["."], "guidance": ["."], "evidence": ["evidence"],
                       "mutation": prepared["fixture"]["allowed_mutation_paths"]},
        policy_ids={"data_classification": "host_owned",
                    "outbound_delivery": "audited_unattested"},
        collector_identity=component, broker_identity=component,
        created=now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        expires=(now + timedelta(days=1)).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
    records.write(evidence / "session.json", session, exclusive=True)
    records.write(evidence / "start-manifest.json",
                  _manifest(evidence, prepared, installed, session), exclusive=True)


def _verify_session(evidence: Path) -> dict:
    session = records.read(evidence / "session.json")
    key = (evidence.parent / ".session-keys" / (evidence.name + ".key")).read_bytes()
    # Historical verification uses the persisted launch time, never an invented
    # current authorization. This MAC is integrity evidence, not OS isolation.
    errors = attestation.verify_session_attestation(session, key, now=session["created"])
    if errors:
        raise ValueError("captured_session_invalid:" + ",".join(errors))
    start = records.read(evidence / "start-manifest.json")
    if start["manifest_hash"] != xc.document_hash(start, "manifest_hash"):
        raise ValueError("captured_start_manifest_changed")
    if start["session_attestation_hash"] != session["attestation_hash"]:
        raise ValueError("captured_session_binding_changed")
    return session


def _failure(prepared: dict, installed: dict, evidence: Path, meta: dict,
             *, reason: str, evaluator_error: bool) -> dict:
    classification = causes.classify(meta, [reason], evaluator_error=evaluator_error)
    records.write(evidence / "cause.json", classification)
    task_fields, profile_fields = comparison_fields(prepared, installed, None)
    return scoring.score_run(
        prepared["fixture"], run_id=evidence.name,
        task_measurement_key=baseline.task_measurement_key(task_fields),
        strict_profile_key=baseline.strict_profile_key(task_fields, profile_fields),
        axes={"preflight": "setup_invalid" if evaluator_error else "ready",
              "execution": "execution_invalid", "observer": "observer_unsupported",
              "artifacts": "artifact_invalid"},
        enforcement_mode="audited", f0_calibration_passed=False, profile_identity_match=False,
        comparison_status="matched_content_noncontrolled", gate_decision=None,
        delivery_percent=None, oracle_result=None, cause=causes.result_cause(classification),
        extra_reason_codes=[reason],
    )


def run(
    preparation: Path, installed: dict, calibration_path: Path, plan: dict,
    attempt_id: str, *, workspace: Path,
    prepare_oracle: Callable[[dict, Path], dict | None] | None = None,
) -> dict:
    preparation, workspace = Path(preparation).resolve(), Path(workspace).resolve()
    prepared = verify_prepared(preparation)
    if prepared["fixture"]["family"] == "F6":
        raise ValueError("installed_cli_blinded_f6_unsupported")
    profiles.verify(installed)
    calibration_record = records.read(calibration_path)
    calibration.verify(calibration_record, installed, evidence_root=calibration_path.parent)
    records.disjoint(workspace, Path(plan["journal_root"]), preparation.parent)
    records.disjoint(workspace, Path(prepared["fixture_dir"]))
    if workspace.exists():
        raise ValueError("attempt_workspace_already_exists")
    auth = profiles.subscription_status(installed)
    if not auth["ready"]:
        raise ValueError(auth["reason"])
    claim, evidence = schedule.claim(plan, attempt_id, profile_hash=installed["record_hash"],
                                    input_hash=prepared["record_hash"], seed_identity=prepared["seed_identity"],
                                    fixture_id=prepared["fixture"]["fixture_id"], kind="fixture", workspace=workspace)
    meta = {"status": "failed", "started": processes.timestamp(), "exit_code": None}
    try:
        records.write(evidence / "installed-profile.json", installed, exclusive=True)
        records.write(evidence / "calibration.json", calibration_record, exclusive=True)
        records.write(evidence / "input.json",
                      {"preparation": str(preparation), "workspace": str(workspace)}, exclusive=True)
        _start_session(evidence, prepared, installed)
        baseline.clone_seed(Path(prepared["seed_store"]), prepared["seed_identity"], workspace)
        empty = adapters.normalize_transcript([], installed["profile"]["adapter_id"],
                                              prepared["manifest"], cwd=str(workspace))
        records.write(evidence / "ledger.json",
                      observation_ledger(empty, installed, prepared["manifest"], {}))
        gate(preparation.parent, evidence)
        argv, contract = profiles.command(installed, workspace)
        prompt = ((preparation.parent / "task.txt").read_bytes() +
                  b"\n\nThe following complete guidance bundle applies to this task.\n" +
                  (preparation.parent / "bundle.txt").read_bytes())
        env, _ = profiles.environment()
        meta = processes.capture(argv, cwd=workspace, environment=env, prompt=prompt,
                                 output_dir=evidence, timeout_seconds=schedule.remaining_timeout(claim))
        meta.update({"worktree": str(workspace), "adapter_contract": contract})
        records.write(evidence / "process.json", meta, exclusive=True)
        _verify_session(evidence)
        final_identity = capture_tree(workspace, evidence / "final-tree")
        diff, changed = tree_diff(Path(prepared["seed_store"]) / prepared["seed_identity"],
                                  evidence / "final-tree")
        (evidence / "diff.patch").write_text(diff)
        records.write(evidence / "tree.json",
                      {"identity": final_identity, "changed_paths": changed}, exclusive=True)
        result = _evaluate(evidence, prepared, installed, prepare_oracle=prepare_oracle, replay=False)
    except Exception as error:
        records.write(evidence / "evaluator-error.json",
                      {"error_type": type(error).__name__, "reason": str(error)})
        result = _failure(prepared, installed, evidence, meta,
                          reason="evaluator_failure", evaluator_error=True)
    # The result is the final publication, after every required evidence write.
    records.write(evidence / "result.json", result, exclusive=True)
    schedule.finish(plan, evidence, result_hash=xc.sha256_file(evidence / "result.json"),
                    cause_owner=(result.get("cause") or {}).get("owner"))
    return result


def _evaluate(evidence: Path, prepared: dict, installed: dict, *,
              prepare_oracle: Callable | None, replay: bool) -> dict:
    inputs = records.read(evidence / "input.json")
    prepared_path = Path(inputs["preparation"])
    meta = records.read(evidence / "process.json")
    events, invalid = adapters.load_jsonl_strict(evidence / "transcript.jsonl")
    normalized = adapters.normalize_transcript(events, installed["profile"]["adapter_id"],
                                              prepared["manifest"], cwd=inputs["workspace"])
    raw_names = ("transcript.jsonl", "stderr.txt", "stdin.txt", "process.json",
                 "process-start.json", "tree.json", "diff.patch")
    raw = {name: xc.sha256_file(evidence / name) for name in raw_names if (evidence / name).is_file()}
    ledger = observation_ledger(normalized, installed, prepared["manifest"], raw)
    if replay:
        if records.read(evidence / "ledger.json") != ledger:
            raise ValueError("replayed_observation_changed")
        reconciliation = records.read(evidence / "reconcile.json")
        classification = records.read(evidence / "cause.json")
        oracle_evidence = records.read(evidence / "oracles.json")
    else:
        records.write(evidence / "ledger.json", ledger)
        reconciliation = gate(prepared_path.parent, evidence, final=evidence / "final-tree")
        validity = adapters.inspect_run_validity(meta, normalized, invalid)
        classification = causes.classify(meta, installed["boundary_limitations"] + validity["reason_codes"])
        records.write(evidence / "cause.json", classification)
        oracle_evidence = {
            "results": [fixtures.run_semantic_oracle(
                Path(prepared["fixture_dir"]), prepared["fixture"], row["id"], evidence / "final-tree",
                prepare_oracle=prepare_oracle) for row in prepared["fixture"]["semantic_oracles"] if row["blocking"]],
            "safety_results": fixtures.run_safety_validators(
                Path(prepared["fixture_dir"]), prepared["fixture"], tree=evidence / "final-tree",
                diff_text=(evidence / "diff.patch").read_text()),
        }
    toolchain_versions = {}
    compile_receipt = evidence / "compile-evidence/receipt.json"
    if compile_receipt.exists():
        compile_evidence = records.read(compile_receipt)
        toolchain_versions = {"compiler": compile_evidence["toolchain"],
                              "matrix": compile_evidence["matrix"]}
    task_fields, profile_fields = comparison_fields(prepared, installed, normalized.get("observed_model"), toolchain_versions)
    outcome = fixtures.evaluate_run(
        Path(prepared["fixture_dir"]), prepared["fixture"], events=events, run_id=evidence.name,
        adapter=installed["profile"]["adapter_id"], manifest=prepared["manifest"],
        tree=evidence / "final-tree", diff_text=(evidence / "diff.patch").read_text(),
        requested_model=installed["profile"]["requested_model"], f0_calibration_passed=False,
        task_measurement_key=baseline.task_measurement_key(task_fields),
        strict_profile_key=baseline.strict_profile_key(task_fields, profile_fields),
        execution_meta=meta, invalid_json_lines=invalid,
        changed_paths=records.read(evidence / "tree.json")["changed_paths"],
        parent_gate_result=reconciliation, parent_reason_codes=installed["boundary_limitations"],
        cause=causes.result_cause(classification), prepare_oracle=prepare_oracle,
        recorded_oracles=oracle_evidence.get("results"),
        recorded_safety=oracle_evidence.get("safety_results"),
    )
    result = outcome["run_result"]
    if not replay:
        records.write(evidence / "oracles.json",
                      {"results": outcome["oracle_results"], "safety_results": outcome["safety_results"]},
                      exclusive=True)
        (evidence / "report.md").write_text(scoring.render_run_report(result))
        raw.update({name: xc.sha256_file(evidence / name) for name in
                    ("installed-profile.json", "calibration.json", "input.json", "launch.json",
                     "oracles.json", "cause.json", "reconcile.json", "ledger.json", "gate.json",
                     "start-manifest.json", "session.json", "report.md")})
        if compile_receipt.exists():
            raw.update({p.relative_to(evidence).as_posix(): xc.sha256_file(p)
                        for p in compile_receipt.parent.iterdir() if p.is_file()})
        terminal = ("completed" if meta["status"] == "completed" else
                    "timeout" if meta["timed_out"] else "aborted" if meta["interrupted"] else "failed")
        manifest = _manifest(
            evidence, prepared, installed, _verify_session(evidence),
            observed_model=normalized.get("observed_model"), raw=raw, toolchain_versions=toolchain_versions,
            end_state={"final_tree_identity": records.read(evidence / "tree.json")["identity"],
                       "ended": meta["ended"], "terminal_status": terminal},
        )
        records.write(evidence / "run-manifest.json", manifest, exclusive=True)
    return result


def score(evidence: Path, *, require_finished: bool = True) -> dict:
    """Recompute scores from verified captured facts; never launch or write."""
    evidence = Path(evidence).resolve()
    inputs = records.read(evidence / "input.json")
    prepared = verify_prepared(Path(inputs["preparation"]))
    installed = records.read(evidence / "installed-profile.json")
    profiles.verify(installed, check_executable=False, check_environment=False)
    _verify_session(evidence)
    manifest = records.read(evidence / "run-manifest.json")
    require_valid("xuunity.protected-run-manifest.schema.json", manifest, "replay manifest")
    if manifest["manifest_hash"] != xc.document_hash(manifest, "manifest_hash"):
        raise ValueError("run_manifest_changed")
    for name, digest in manifest["raw_evidence_hashes"].items():
        if xc.normalize_repo_path(name) != name or not (evidence / name).resolve().is_relative_to(evidence) or xc.sha256_file(evidence / name) != digest:
            raise ValueError("captured_artifact_changed")
    validate_tree(evidence / "final-tree")
    if baseline.content_identity(evidence / "final-tree") != manifest["end_state"]["final_tree_identity"]:
        raise ValueError("captured_final_tree_changed")
    result = _evaluate(evidence, prepared, installed, prepare_oracle=None, replay=True)
    if result != records.read(evidence / "result.json"):
        raise ValueError("replayed_result_changed")
    if require_finished:
        finished = records.read(evidence / "finished.json")
        if finished["result_hash"] != xc.sha256_file(evidence / "result.json"):
            raise ValueError("finished_result_changed")
    return result


def recover(plan: dict, attempt_id: str) -> dict:
    """Diagnose an abandoned launch once; this function has no provider call."""
    evidence = schedule.assert_abandoned(plan, attempt_id)
    if (evidence / "result.json").exists():
        # A crash between result publication and journal completion can safely
        # finalize the original result, after artifact-only verification.
        result = records.read(evidence / "result.json")
        require_valid("xuunity.run-result.schema.json", result, "interrupted result")
        if (evidence / "run-manifest.json").exists():
            score(evidence, require_finished=False)
        elif not (evidence / "evaluator-error.json").exists() or result["score_total"] is not None:
            raise ValueError("unfinished_result_evidence_missing")
        artifact = evidence / "result.json"
        owner = (result.get("cause") or {}).get("owner")
    elif (evidence / "calibration.json").exists() and not (evidence / "input.json").exists():
        result = records.read(evidence / "calibration.json")
        records.verify(result)
        for name, digest in result["raw_artifact_hashes"].items():
            if "/" in name or "\\" in name or xc.sha256_file(evidence / name) != digest:
                raise ValueError("f0_raw_evidence_changed")
        artifact = evidence / "calibration.json"
        owner = (result.get("cause") or {}).get("owner")
    else:
        # Even a crash before input publication remains in the denominator.
        # Do not depend on mutable preparation files to diagnose that crash.
        artifact = evidence / "recovery.json"
        if artifact.exists():
            result = records.read(artifact)
            records.verify(result)
        else:
            result = records.seal({
                "schema_version": "xuunity.interrupted-attempt.v1",
                "attempt_id": attempt_id, "schedule_hash": plan["record_hash"],
                "status": "interrupted", "recovered_at": processes.timestamp(),
                "recovered_by_engine": profiles.engine_identity(),
                "reason_codes": ["parent_interrupted_after_launch_claim"],
                "model_relaunched": False, "score_total": None,
            })
            records.write(artifact, result, exclusive=True)
        owner = "unattributed"
    digest = result["record_hash"] if artifact.name == "calibration.json" else xc.sha256_file(artifact)
    schedule.finish(plan, evidence, result_hash=digest, cause_owner=owner)
    return result


def validate_schedule_inputs(plan: dict) -> None:
    """Validate the whole roster before spending on its first attempt."""
    schedule.validate(plan)
    workspaces = []
    calibrations = {}
    for row in plan["attempts"]:
        installed = records.read(Path(row["profile_ref"]))
        profiles.verify(installed)
        if installed["record_hash"] != row["profile_record_hash"]:
            raise ValueError("scheduled_profile_changed")
        workspace = Path(row["workspace_ref"]).resolve()
        records.disjoint(workspace, Path(plan["journal_root"]), *workspaces)
        workspaces.append(workspace)
        if row["kind"] == "calibration":
            if (row["input_hash"], row["seed_identity"], row["fixture_id"]) != (calibration.input_hash(), calibration.input_hash(), "f0_cli_canary"):
                raise ValueError("scheduled_calibration_changed")
            calibrations[str((Path(plan["journal_root"]) / row["attempt_id"] / "calibration.json").resolve())] = installed["record_hash"]
        else:
            preparation = Path(row["preparation_ref"])
            prepared = verify_prepared(preparation)
            if (row["input_hash"], row["seed_identity"], row["fixture_id"]) != (prepared["record_hash"], prepared["seed_identity"], prepared["fixture"]["fixture_id"]):
                raise ValueError("scheduled_preparation_changed")
            records.disjoint(workspace, preparation.parent, Path(prepared["fixture_dir"]))
            path = Path(row["calibration_ref"]).resolve()
            if path.exists():
                calibration.verify(records.read(path), installed, evidence_root=path.parent)
            elif calibrations.get(str(path)) != installed["record_hash"]:
                raise ValueError("scheduled_calibration_predecessor_missing")


def run_schedule(plan: dict, *, prepare_oracle: Callable[[dict, Path], dict | None] | None = None) -> list[dict]:
    """Execute a frozen explicit roster. Completed attempts are verified, never retried.

    Each row supplies profile_ref/workspace_ref; fixture rows additionally
    supply preparation_ref/calibration_ref. Those inputs still have to match
    the preregistered hashes before any provider launch.
    """
    validate_schedule_inputs(plan)
    root = Path(plan["journal_root"])
    for row in plan["attempts"]:
        if (root / "stopped.json").exists():
            break
        evidence = root / row["attempt_id"]
        if (evidence / "finished.json").exists():
            if (evidence / "recovery.json").exists():
                recovery = records.read(evidence / "recovery.json")
                records.verify(recovery)
                if records.read(evidence / "finished.json")["result_hash"] != xc.sha256_file(evidence / "recovery.json"):
                    raise ValueError("recovery_artifact_changed")
            elif row["kind"] == "fixture":
                score(evidence)
            else:
                calibration.verify(records.read(evidence / "calibration.json"),
                                   records.read(Path(row["profile_ref"])), evidence_root=evidence)
            continue
        installed = records.read(Path(row["profile_ref"]))
        if row["kind"] == "calibration":
            result = calibration.run(installed, plan, row["attempt_id"], workspace=Path(row["workspace_ref"]))
            if not result["diagnostic_compatible"]:
                if not (root / "stopped.json").exists():
                    schedule.close(plan, "provider_unavailable")
                break
        else:
            run(Path(row["preparation_ref"]), installed, Path(row["calibration_ref"]), plan,
                row["attempt_id"], workspace=Path(row["workspace_ref"]), prepare_oracle=prepare_oracle)
    return schedule.accounting(plan)
