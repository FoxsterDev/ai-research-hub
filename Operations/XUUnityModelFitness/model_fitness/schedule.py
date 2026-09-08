"""Fixed launch roster and durable accounting, separate from statistical aggregation."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from . import records
from . import suite as suites
from .processes import timestamp


def validate(plan: dict[str, Any]) -> None:
    records.verify(plan)
    if plan.get("schema_version") != "xuunity.execution-schedule.v1":
        raise ValueError("unknown_schedule_schema")
    records.slug(plan["schedule_id"])
    rows = plan["attempts"]
    if not rows or plan["max_model_launches"] != len(rows):
        raise ValueError("schedule_denominator_mismatch")
    if not 0 < plan["max_wall_seconds"] <= 86400 or plan["stop_rule"] not in {"fixed", "stop_on_evaluator_or_budget"}:
        raise ValueError("invalid_schedule_policy")
    ids = set()
    for order, row in enumerate(rows):
        records.slug(row["attempt_id"])
        if row["attempt_id"] in ids or row["order"] != order:
            raise ValueError("duplicate_or_reordered_schedule")
        ids.add(row["attempt_id"])
        if row["kind"] not in {"calibration", "fixture"} or not 0 < row["timeout_seconds"] <= 3600:
            raise ValueError("invalid_attempt_kind_or_timeout")
        for field in ("profile_record_hash", "input_hash", "seed_identity"):
            if not re.fullmatch("[0-9a-f]{64}", row.get(field, "")):
                raise ValueError("attempt_identity_missing:" + field)
        if not row.get("fixture_id") or not row.get("block_id") or type(row.get("replicate")) is not int or row["replicate"] < 1:
            raise ValueError("attempt_allocation_missing")
    contracts = plan.get("comparison_contracts", []) + ([plan["comparison_contract"]] if plan.get("comparison_contract") else [])
    if len({c["suite_hash"] for c in contracts}) != len(contracts):
        raise ValueError("duplicate_schedule_comparison_contract")
    for contract in contracts:
        if contract["strict_profile_key"] != suites.suite_profile_key(contract["fixture_profile_keys"]):
            raise ValueError("schedule_comparison_key_changed")


def build(
    attempts: list[dict[str, Any]], *, schedule_id: str, journal_root: Path,
    max_wall_seconds: int, stop_rule: str = "stop_on_evaluator_or_budget",
    suite_document: dict | None = None, fixture_profile_keys: dict | None = None,
    comparison_contracts: list[dict] | None = None,
) -> dict[str, Any]:
    records.slug(schedule_id)
    if not attempts or not 0 < max_wall_seconds <= 86400:
        raise ValueError("invalid schedule bounds")
    if stop_rule not in {"fixed", "stop_on_evaluator_or_budget"}:
        raise ValueError("unknown_stop_rule")
    ids = set()
    for order, row in enumerate(attempts):
        records.slug(row["attempt_id"])
        if row["attempt_id"] in ids or row["order"] != order:
            raise ValueError("duplicate_or_reordered_schedule")
        ids.add(row["attempt_id"])
        if row["kind"] not in {"calibration", "fixture"}:
            raise ValueError("unknown_attempt_kind")
        if not 0 < row["timeout_seconds"] <= 3600:
            raise ValueError("invalid_attempt_timeout")
        if not row.get("profile_record_hash") or not row.get("input_hash"):
            raise ValueError("attempt_input_identity_missing")
    contract = None
    if suite_document is not None:
        suites.validate_suite(suite_document)
        if set(fixture_profile_keys or {}) != {row["fixture_id"] for row in suite_document["fixtures"]}:
            raise ValueError("schedule_comparison_keys_incomplete")
        contract = {"suite_hash": suites.suite_hash(suite_document), "fixture_profile_keys": fixture_profile_keys,
                    "strict_profile_key": suites.suite_profile_key(fixture_profile_keys)}
    elif fixture_profile_keys is not None:
        raise ValueError("comparison_keys_without_suite")
    plan = records.seal({
        "schema_version": "xuunity.execution-schedule.v1", "schedule_id": schedule_id,
        "created": timestamp(), "journal_root": str(Path(journal_root).resolve()),
        "attempts": attempts, "max_model_launches": len(attempts),
        "max_wall_seconds": max_wall_seconds, "stop_rule": stop_rule,
        "comparison_contract": contract,
        "comparison_contracts": comparison_contracts or [],
    })
    validate(plan)
    return plan


def comparison_contract(plan: dict, suite_document: dict) -> dict:
    validate(plan)
    digest = suites.suite_hash(suite_document)
    contracts = plan.get("comparison_contracts", []) + ([plan["comparison_contract"]] if plan.get("comparison_contract") else [])
    matches = [c for c in contracts if c["suite_hash"] == digest]
    if len(matches) != 1 or set(matches[0]["fixture_profile_keys"]) != {f["fixture_id"] for f in suite_document["fixtures"]}:
        raise ValueError("suite_was_not_preregistered_in_execution_schedule")
    return matches[0]


def claim(plan: dict[str, Any], attempt_id: str, *, profile_hash: str, input_hash: str,
          seed_identity: str | None = None, fixture_id: str | None = None,
          kind: str | None = None) -> tuple[dict[str, Any], Path]:
    validate(plan)
    rows = plan["attempts"]
    if plan["max_model_launches"] != len(rows):
        raise ValueError("schedule_denominator_mismatch")
    row = next((row for row in rows if row["attempt_id"] == attempt_id), None)
    if row is None or row["profile_record_hash"] != profile_hash or row["input_hash"] != input_hash:
        raise ValueError("launch_not_in_frozen_schedule")
    if any(value is not None and row[key] != value for key, value in
           (("seed_identity", seed_identity), ("fixture_id", fixture_id), ("kind", kind))):
        raise ValueError("launch_allocation_mismatch")
    root = Path(plan["journal_root"])
    root.mkdir(parents=True, exist_ok=True)
    anchor = root / "schedule.json"
    try:
        records.write(anchor, plan, exclusive=True)
    except FileExistsError:
        if records.read(anchor) != plan:
            raise ValueError("schedule_changed_after_registration") from None
    lock = root / "launch.lock"
    records.write(lock, {"attempt_id": attempt_id, "owner_pid": os.getpid()}, exclusive=True)
    try:
        for previous in rows[:row["order"]]:
            if not (root / previous["attempt_id"] / "finished.json").is_file():
                raise ValueError("schedule_order_or_interrupted_predecessor")
        if (root / "stopped.json").exists():
            raise ValueError("schedule_stopped")
        first = root / "first-launch.json"
        try:
            records.write(first, {"epoch_seconds": time.time(), "started": timestamp()}, exclusive=True)
        except FileExistsError:
            pass
        elapsed = time.time() - records.read(first)["epoch_seconds"]
        remaining = plan["max_wall_seconds"] - elapsed
        if remaining <= 0:
            records.write(root / "stopped.json", {"reason": "schedule_wall_budget_exhausted"}, exclusive=True)
            raise ValueError("schedule_wall_budget_exhausted")
        attempt_root = root / attempt_id
        attempt_root.mkdir(exist_ok=False)
        launched = {
            "schema_version": "xuunity.launch-claim.v1", "schedule_hash": plan["record_hash"],
            "attempt": row, "started": timestamp(), "owner_pid": os.getpid(),
            "deadline_epoch_seconds": time.time() + remaining,
            "effective_timeout_seconds": min(row["timeout_seconds"], remaining),
        }
        records.write(attempt_root / "launch.json", records.seal(launched), exclusive=True)
        return launched, attempt_root
    except BaseException:
        lock.unlink(missing_ok=True)
        raise


def finish(plan: dict[str, Any], attempt_root: Path, *, result_hash: str, cause_owner: str | None = None) -> None:
    validate(plan)
    root = Path(plan["journal_root"])
    launch = records.read(attempt_root / "launch.json")
    records.verify(launch)
    if launch["schedule_hash"] != plan["record_hash"] or attempt_root.parent.resolve() != root.resolve():
        raise ValueError("launch_schedule_mismatch")
    lock = records.read(root / "launch.lock")
    if lock["attempt_id"] != attempt_root.name:
        raise ValueError("launch_lock_owner_mismatch")
    completed = attempt_root / "finished.json"
    if completed.exists():
        previous = records.read(completed)
        if previous["result_hash"] != result_hash or previous["cause_owner"] != cause_owner:
            raise ValueError("conflicting_attempt_completion")
    else:
        records.write(completed, {
            "result_hash": result_hash, "finished": timestamp(), "cause_owner": cause_owner,
        }, exclusive=True)
    if cause_owner in {"measurement_system", "unattributed"} and plan["stop_rule"] == "stop_on_evaluator_or_budget":
        if not (root / "stopped.json").exists():
            records.write(root / "stopped.json", {"reason": cause_owner, "attempt_id": attempt_root.name}, exclusive=True)
    (root / "launch.lock").unlink()


def accounting(plan: dict[str, Any]) -> list[dict[str, Any]]:
    validate(plan)
    root = Path(plan["journal_root"])
    rows = []
    for attempt in plan["attempts"]:
        directory = root / attempt["attempt_id"]
        status = ("finished" if (directory / "finished.json").exists()
                  else "interrupted_or_running" if (directory / "launch.json").exists()
                  else "censored" if (root / "stopped.json").exists() else "unlaunched")
        rows.append({"attempt_id": attempt["attempt_id"], "order": attempt["order"], "status": status})
    return rows


def assert_abandoned(plan: dict[str, Any], attempt_id: str) -> Path:
    """Never kill a potentially reused PID or relaunch an ambiguous attempt."""
    validate(plan)
    records.slug(attempt_id)
    root = Path(plan["journal_root"])
    launch = records.read(root / attempt_id / "launch.json")
    records.verify(launch)
    if launch["schedule_hash"] != plan["record_hash"] or launch["attempt"]["attempt_id"] != attempt_id:
        raise ValueError("recovery_schedule_mismatch")
    pids = [launch["owner_pid"]]
    process_start = root / attempt_id / "process-start.json"
    if (root / attempt_id / "process-intent.json").exists() and not process_start.exists():
        raise ValueError("recovery_process_identity_unavailable")
    if process_start.exists():
        pids.append(records.read(process_start)["pid"])
    if os.name != "posix":
        raise ValueError("automatic_pid_recovery_unsupported_on_this_os")
    for pid in pids:
        if type(pid) is not int or pid <= 1:
            raise ValueError("recovery_pid_invalid")
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        raise ValueError("recovery_process_still_present")
    return root / attempt_id


def remaining_timeout(claim: dict) -> float:
    """Preparation and golden checks consume the same registered wall budget."""
    remaining = min(claim["effective_timeout_seconds"], claim["deadline_epoch_seconds"] - time.time())
    if remaining <= 0:
        raise ValueError("schedule_wall_budget_exhausted_before_provider")
    return remaining


def close(plan: dict[str, Any], reason: str) -> None:
    validate(plan)
    if reason not in {"no_new_information", "quota_ceiling", "provider_unavailable", "measurement_system", "operator_cancelled"}:
        raise ValueError("unknown_schedule_stop_reason")
    root = Path(plan["journal_root"])
    if (root / "launch.lock").exists():
        raise ValueError("recover_active_attempt_before_closing")
    records.write(root / "stopped.json", {"reason": reason, "stopped": timestamp()}, exclusive=True)
