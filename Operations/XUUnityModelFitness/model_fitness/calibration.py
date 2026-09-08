"""F0 capability evidence bound to a concrete installed parser and CLI profile."""

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import xuunity_canonical as xc

from . import OPERATION_DIR, MODULE_SCRIPTS_DIR, adapters, causes, fixtures, processes, profiles, records, schedule

CANARY_GUIDANCE = "# F0 calibration\nSet Probe.Value to 7 after reading this whole file.\n"
CANARY_SOURCE = "public static class Probe { public const int Value = 0; }\n"
CANARY_PROMPT = (
    "This is a bounded CLI compatibility canary. Read guidance.md completely using a native read "
    "or cat. Then edit only Probe.cs, setting Value from 0 to 7. Do not inspect paths outside "
    "this workspace, use network tools, create other files or run tests. Report completion."
)


def input_hash() -> str:
    return xc.domain_digest("xuunity.f0-input.v1", {
        "guidance": CANARY_GUIDANCE, "source": CANARY_SOURCE, "prompt": CANARY_PROMPT,
    })


def identity(installed: dict[str, Any]) -> dict[str, str]:
    return {
        "installed_profile_hash": installed["record_hash"],
        "calibration_code_hash": xc.sha256_file(Path(__file__)),
        "observer_code_hash": xc.sha256_file(MODULE_SCRIPTS_DIR / "observation_contract.py"),
        "shell_parser_hash": xc.sha256_file(MODULE_SCRIPTS_DIR / "shell_observer.py"),
        "canary_input_hash": input_hash(),
        "golden_suite_hash": xc.domain_digest("xuunity.f0-golden-suite.v1", {
            "adapter": xc.sha256_file(OPERATION_DIR / "tests/test_adapters.py"),
            "observer": xc.sha256_file(MODULE_SCRIPTS_DIR / "tests/test_observation_contract.py"),
            "shell": xc.sha256_file(MODULE_SCRIPTS_DIR / "tests/test_shell_observer.py"),
        }),
    }


def run(installed: dict[str, Any], plan: dict[str, Any], attempt_id: str, *, workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace).resolve()
    profiles.verify(installed)
    records.disjoint(workspace, Path(plan["journal_root"]))
    if Path(workspace).exists():
        raise ValueError("calibration_workspace_already_exists")
    auth = profiles.subscription_status(installed)
    if not auth["ready"]:
        raise ValueError(auth["reason"])
    claim, output = schedule.claim(plan, attempt_id, profile_hash=installed["record_hash"], input_hash=input_hash(),
                                   seed_identity=input_hash(), fixture_id="f0_cli_canary", kind="calibration", workspace=workspace)
    record: dict[str, Any] = {
        "schema_version": "xuunity.f0-calibration.v1", "attempt_id": attempt_id,
        "identity": identity(installed), "created": processes.timestamp(),
        "diagnostic_compatible": False, "score_eligible": False,
        "reason_codes": list(installed["boundary_limitations"]), "auth": auth,
        "raw_artifact_hashes": {},
    }
    try:
        commands = [
            [sys.executable, "-m", "unittest", "discover", "-s", str(OPERATION_DIR / "tests"), "-p", "test_adapters.py"],
            [sys.executable, "-m", "unittest", "discover", "-s", str(MODULE_SCRIPTS_DIR / "tests"), "-p", "test_observation_contract.py"],
            [sys.executable, "-m", "unittest", "discover", "-s", str(MODULE_SCRIPTS_DIR / "tests"), "-p", "test_shell_observer.py"],
        ]
        env, _ = profiles.environment()
        checks = []
        for index, command in enumerate(commands):
            result = subprocess.run(command, env=env, capture_output=True, timeout=60)
            (output / f"golden-{index}.log").write_bytes(result.stdout + result.stderr)
            checks.append({"command": command, "exit_code": result.returncode,
                           "log_sha256": xc.sha256_file(output / f"golden-{index}.log")})
        record["golden_checks"] = checks
        if any(check["exit_code"] != 0 for check in checks):
            raise ValueError("f0_golden_failed")
        workspace.mkdir(parents=True)
        (workspace / "guidance.md").write_text(CANARY_GUIDANCE)
        (workspace / "Probe.cs").write_text(CANARY_SOURCE)
        argv, contract = profiles.command(installed, workspace)
        meta = processes.capture(argv, cwd=workspace, environment=env,
                                 prompt=CANARY_PROMPT.encode(), output_dir=output,
                                 timeout_seconds=schedule.remaining_timeout(claim))
        meta["adapter_contract"] = contract
        record["process"] = meta
        events, invalid = adapters.load_jsonl_strict(output / "transcript.jsonl")
        manifest = {"guidance.md": {"lines": 2, "bytes": len(CANARY_GUIDANCE.encode()),
                                     "sha256": xc.sha256_bytes(CANARY_GUIDANCE.encode())}}
        normalized = adapters.normalize_transcript(events, installed["profile"]["adapter_id"], manifest, cwd=str(workspace))
        validity = adapters.inspect_run_validity(meta, normalized, invalid)
        boundary = adapters.mutation_boundary(normalized["mutations"], normalized["flags"], ["Probe.cs"])
        record["observed_model"] = normalized.get("observed_model")
        record["event_types"] = sorted({str(event.get("type")) for event in events})
        record["parser_flags"] = json.loads(json.dumps([dataclasses.asdict(flag) for flag in normalized["flags"]]))
        final_source = (workspace / "Probe.cs").read_text()
        (output / "Probe.final.cs").write_text(final_source)
        expected = (re.sub(r"\s+", "", final_source) == re.sub(r"\s+", "", CANARY_SOURCE.replace("Value = 0", "Value = 7"))
                    and (workspace / "guidance.md").read_text() == CANARY_GUIDANCE
                    and sorted(p.name for p in workspace.iterdir()) == ["Probe.cs", "guidance.md"])
        read_seen = any(read.path == "guidance.md" and read.proof == "proven"
                        and read.completed_seq is not None and read.completed_seq < boundary.cutoff
                        for read in normalized["reads"])
        compatible = validity["status"] == "valid" and expected and read_seen and not boundary.boundary_ambiguous and not boundary.diff_without_mutation
        record["diagnostic_compatible"] = compatible
        record["reason_codes"].extend(validity["reason_codes"])
        if not compatible:
            record["reason_codes"].append("live_canary_incompatible")
        if record["observed_model"] is None:
            record["reason_codes"].append("observed_model_unavailable")
        elif record["observed_model"] != installed["profile"]["requested_model"]:
            record["diagnostic_compatible"] = False
            record["reason_codes"].append("profile_identity_mismatch")
    except Exception as error:
        record["reason_codes"].append("calibration_local_failure")
        record["error_type"] = type(error).__name__
    record["raw_artifact_hashes"] = {p.name: xc.sha256_file(p) for p in output.iterdir() if p.is_file()}
    record["reason_codes"] = sorted(set(record["reason_codes"]))
    record["cause"] = causes.classify(record.get("process", {}), record["reason_codes"],
                                      evaluator_error="calibration_local_failure" in record["reason_codes"])
    record = records.seal(record)
    records.write(output / "calibration.json", record, exclusive=True)
    schedule.finish(plan, output, result_hash=record["record_hash"],
                    cause_owner=record["cause"]["owner"])
    return record


def verify(record: dict[str, Any], installed: dict[str, Any], *, evidence_root: Path) -> bool:
    records.verify(record)
    profiles.verify(installed)
    if record.get("identity") != identity(installed):
        raise ValueError("f0_calibration_identity_stale")
    if not record.get("diagnostic_compatible"):
        raise ValueError("f0_diagnostic_calibration_not_passed")
    for name, expected in record["raw_artifact_hashes"].items():
        if "/" in name or "\\" in name or xc.sha256_file(Path(evidence_root) / name) != expected:
            raise ValueError("f0_raw_evidence_changed")
    if record.get("score_eligible"):
        raise ValueError("cli_f0_cannot_claim_request_boundary_conformance")
    return False
