"""Small host-owned rollout telemetry and protocol-change smoke inbox.

These files do not schedule models, apply candidates, or grant conformance.
Every mutation has an explicit destination and retains previous evidence.
"""

from datetime import datetime, timezone
from pathlib import Path

import xuunity_canonical as xc

from . import calibration, executor, profiles, records
from .processes import timestamp


def record_session(root: Path, evidence: Path, *, expected_block: bool | None = None) -> dict:
    result = executor.score(evidence)
    prepared_path = Path(records.read(evidence / "input.json")["preparation"])
    plan = records.read(prepared_path.parent / "stack-plan.json")
    gate = records.read(evidence / "gate.json")
    reconcile = records.read(evidence / "reconcile.json")
    blocked = reconcile["decision"] != "pass"
    row = records.seal({
        "schema_version": "xuunity.rollout-session.v1", "session_id": result["run_id"],
        "observed_at": records.read(evidence / "process.json")["ended"],
        "evidence_ref": str(evidence.resolve()), "result_sha256": xc.sha256_file(evidence / "result.json"),
        "plan_hash": xc.sha256_file(prepared_path.parent / "stack-plan.json"),
        "required_artifacts": len(plan["required_artifacts"]),
        "constructed_bundle_bytes": (prepared_path.parent / "bundle.txt").stat().st_size,
        "verified_delivered_bytes": None, "delivery_reason": "request_boundary_unavailable",
        "gate": gate["decision"], "reconcile": reconcile["decision"],
        "false_block": (blocked and not expected_block) if expected_block is not None else None,
        "false_block_review": "operator_labeled" if expected_block is not None else "unreviewed",
        "enforcement": result["enforcement_mode"],
    })
    records.slug(row["session_id"])
    records.write(Path(root) / "sessions" / (row["session_id"] + ".json"), row, exclusive=True)
    return row


def set_rollout(root: Path, mode: str, *, installed: dict | None = None,
                calibration_path: Path | None = None) -> dict:
    if mode not in {"off", "observe", "advisory", "blocking"}:
        raise ValueError("unknown_rollout_mode")
    root = Path(root)
    previous = records.read(root / "rollout.json") if (root / "rollout.json").exists() else None
    if previous:
        records.verify(previous)
    if mode in {"advisory", "blocking"}:
        if installed is None or calibration_path is None:
            raise ValueError("live_conformance_evidence_required")
        profiles.verify(installed)
        record = records.read(calibration_path)
        if not calibration.verify(record, installed, evidence_root=calibration_path.parent):
            raise ValueError("live_request_boundary_conformance_unavailable")
        if mode == "blocking":
            if not previous or previous["mode"] != "advisory":
                raise ValueError("advisory_observation_required")
            start = datetime.fromisoformat(previous["changed"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - start).total_seconds() < 14 * 86400:
                raise ValueError("two_week_observation_window_incomplete")
            sessions = [records.read(path) for path in (root / "sessions").glob("*.json")]
            for session in sessions:
                records.verify(session)
            observed = [s for s in sessions if s["observed_at"] >= previous["changed"]]
            if len(observed) < 3 or any(s["false_block"] is not False for s in observed):
                raise ValueError("reviewed_false_block_telemetry_required")
    record = records.seal({"schema_version": "xuunity.rollout-state.v1", "mode": mode,
                           "changed": timestamp(), "previous_hash": previous["record_hash"] if previous else None})
    records.write(root / "history" / (record["record_hash"] + ".json"), record, exclusive=True)
    records.write(root / "rollout.json", record)
    return record


def protocol_changed(root: Path, *, change_id: str, before: str, after: str,
                     baseline_refs: list[Path], smoke_fixture_ids: list[str]) -> dict:
    """Persist stale status and pending re-evaluation without rewriting a score."""
    records.slug(change_id)
    if before == after or not smoke_fixture_ids:
        raise ValueError("protocol_change_and_smoke_roster_required")
    affected = []
    for path in baseline_refs:
        record = records.read(path)
        if record.get("protocol_content_hash") != before:
            raise ValueError("baseline_protocol_identity_mismatch")
        affected.append({"ref": str(path.resolve()), "sha256": xc.sha256_file(path), "status": "stale"})
    result = records.seal({"schema_version": "xuunity.pending-protocol-smoke.v1", "change_id": change_id,
                           "before": before, "after": after, "created": timestamp(),
                           "affected_baselines": affected, "fixture_ids": sorted(set(smoke_fixture_ids)),
                           "status": "pending", "model_launched": False})
    records.write(Path(root) / "pending-smoke" / (change_id + ".json"), result, exclusive=True)
    return result
