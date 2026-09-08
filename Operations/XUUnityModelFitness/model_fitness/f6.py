"""Signed, parent-owned evidence for the blinded F6 holdout.

The suite must never accept a model-authored boolean as proof that F6 ran.
This module binds one immutable F6 attempt roster to the exact suite,
fixture, strict profile, and host-declared holdout rotation.  The artifact is
MAC-authenticated with a key selected by the preregistered issuer id; the key
itself stays outside the artifact and model-writable namespace.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Iterable
from pathlib import Path
import re

from . import attestation, contracts, records

import xuunity_canonical as xc

ARTIFACT_SCHEMA = "xuunity.f6-result-artifact.v1"
SIGNATURE_DOMAIN = "xuunity:f6-result-artifact:v1"
ATTEMPT_DIGEST_SCHEMA = "xuunity.f6-attempt.v1"


class F6EvidenceError(ValueError):
    pass


def _verification_key(
    verification_keys: Mapping[str, bytes], issuer_key_id: str
) -> bytes:
    key = verification_keys.get(issuer_key_id)
    if key is None:
        raise F6EvidenceError("F6 issuer verification key unavailable")
    if len(key) < 32:
        raise F6EvidenceError("F6 verification key must be at least 256 bits")
    return key


def attempt_sha256(attempt: dict[str, Any]) -> str:
    return xc.domain_digest(
        ATTEMPT_DIGEST_SCHEMA,
        contracts.hash_payload(attempt),
    )


def _attempt_entries(attempts: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    entries = [
        {
            "attempt_id": str(attempt["attempt_id"]),
            "attempt_sha256": attempt_sha256(attempt),
        }
        for attempt in attempts
    ]
    return sorted(entries, key=lambda row: row["attempt_id"])


def build_artifact(
    key: bytes,
    *,
    evidence_ref: str,
    issuer_key_id: str,
    holdout_ref: str,
    suite_id: str,
    suite_sha256: str,
    fixture_id: str,
    fixture_sha256: str,
    strict_profile_key: str,
    attempts: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Create the JSON artifact in the trusted parent process."""
    if len(key) < 32:
        raise F6EvidenceError("F6 signing key must be at least 256 bits")
    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA,
        "evidence_ref": evidence_ref,
        "issuer_key_id": issuer_key_id,
        "holdout_ref": holdout_ref,
        "suite_id": suite_id,
        "suite_sha256": suite_sha256,
        "fixture_id": fixture_id,
        "fixture_sha256": fixture_sha256,
        "strict_profile_key": strict_profile_key,
        "attempts": _attempt_entries(attempts),
        "artifact_hash": None,
        "signature": None,
    }
    artifact["artifact_hash"] = xc.document_hash(
        artifact,
        "artifact_hash",
        extra_excluded=("signature",),
    )
    artifact["signature"] = attestation.mac_hex(
        key,
        SIGNATURE_DOMAIN,
        artifact["artifact_hash"],
    )
    contracts.require_valid(
        "xuunity.f6-result-artifact.schema.json",
        artifact,
        "F6 result artifact",
    )
    return artifact


def authenticate_artifact(
    artifact: Any,
    *,
    verification_keys: Mapping[str, bytes],
    expected_issuer_key_id: str | None = None,
) -> dict[str, Any]:
    """Authenticate one artifact without trusting a suite-result summary."""
    if not isinstance(artifact, dict):
        raise F6EvidenceError("F6 evidence must be a structured artifact")
    errors = contracts.validate_against(
        "xuunity.f6-result-artifact.schema.json", artifact
    )
    if errors:
        raise F6EvidenceError(f"F6 artifact schema invalid: {errors[0]}")

    computed = xc.document_hash(
        artifact,
        "artifact_hash",
        extra_excluded=("signature",),
    )
    if computed != artifact["artifact_hash"]:
        raise F6EvidenceError("F6 artifact hash mismatch")

    issuer_key_id = str(artifact["issuer_key_id"])
    if (
        expected_issuer_key_id is not None
        and issuer_key_id != expected_issuer_key_id
    ):
        raise F6EvidenceError("F6 artifact issuer mismatch")
    key = _verification_key(verification_keys, issuer_key_id)
    if not attestation.mac_matches(
        key,
        SIGNATURE_DOMAIN,
        artifact["artifact_hash"],
        artifact["signature"],
    ):
        raise F6EvidenceError("F6 artifact signature invalid")
    return artifact


def verify_artifact_summary(
    artifact: Any,
    *,
    verification_keys: Mapping[str, bytes],
    expected_artifact_hash: str,
    expected_evidence_ref: str,
    expected_holdout_ref: str,
    expected_issuer_key_id: str,
    expected_suite_id: str,
    expected_suite_sha256: str,
    expected_fixture_id: str,
    expected_strict_profile_key: str,
) -> dict[str, Any]:
    """Authenticate an artifact and bind it to a sanitized suite summary."""
    verified = authenticate_artifact(
        artifact,
        verification_keys=verification_keys,
        expected_issuer_key_id=expected_issuer_key_id,
    )
    expected = {
        "artifact_hash": expected_artifact_hash,
        "evidence_ref": expected_evidence_ref,
        "holdout_ref": expected_holdout_ref,
        "suite_id": expected_suite_id,
        "suite_sha256": expected_suite_sha256,
        "fixture_id": expected_fixture_id,
        "strict_profile_key": expected_strict_profile_key,
    }
    for field, value in expected.items():
        if verified[field] != value:
            raise F6EvidenceError(f"F6 artifact {field} mismatch")
    return verified


def verify_artifact(
    artifact: Any,
    *,
    verification_keys: Mapping[str, bytes],
    expected_holdout_ref: str,
    expected_issuer_key_id: str,
    expected_suite_id: str,
    expected_suite_sha256: str,
    expected_fixture_id: str,
    expected_fixture_sha256: str,
    expected_strict_profile_key: str,
    expected_attempts: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Verify authenticity and every preregistered identity binding."""
    artifact = authenticate_artifact(
        artifact,
        verification_keys=verification_keys,
        expected_issuer_key_id=expected_issuer_key_id,
    )

    expected = {
        "holdout_ref": expected_holdout_ref,
        "suite_id": expected_suite_id,
        "suite_sha256": expected_suite_sha256,
        "fixture_id": expected_fixture_id,
        "fixture_sha256": expected_fixture_sha256,
        "strict_profile_key": expected_strict_profile_key,
    }
    for field, value in expected.items():
        if artifact[field] != value:
            raise F6EvidenceError(f"F6 artifact {field} mismatch")

    entries = artifact["attempts"]
    attempt_ids = [row["attempt_id"] for row in entries]
    if len(attempt_ids) != len(set(attempt_ids)):
        raise F6EvidenceError("F6 artifact attempt ids must be unique")
    if entries != _attempt_entries(expected_attempts):
        raise F6EvidenceError("F6 artifact attempt roster mismatch")
    return artifact


def register_holdout(root: Path, *, holdout_id: str, fixture_hash: str,
                     producer_contexts: list[str], max_exposures: int) -> dict:
    """Register an immutable rotation. Author/reference data stays host-owned."""
    records.slug(holdout_id)
    if (len(set(producer_contexts)) < 2 or type(max_exposures) is not int or max_exposures < 1
            or not re.fullmatch("[a-f0-9]{64}", fixture_hash)):
        raise F6EvidenceError("holdout_requires_two_producers_and_positive_budget")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "registration.lock"
    records.write(lock, {"holdout_id": holdout_id}, exclusive=True)
    record = records.seal({"schema_version": "xuunity.holdout-rotation.v1", "holdout_id": holdout_id,
                           "fixture_hash": fixture_hash, "producer_contexts": producer_contexts,
                           "max_exposures": max_exposures})
    try:
        for path in root.glob("*/rotation.json"):
            previous = records.read(path)
            records.verify(previous)
            if previous["fixture_hash"] == fixture_hash:
                raise F6EvidenceError("rotation_requires_new_fixture_identity")
        directory = root / holdout_id
        directory.mkdir(exist_ok=False)
        records.write(directory / "rotation.json", record, exclusive=True)
    finally:
        lock.unlink()
    return record


def reserve_exposure(root: Path, *, holdout_id: str, attempt_id: str, schedule_hash: str) -> dict:
    """Charge before evaluation, including failures and interrupted evaluations."""
    records.slug(holdout_id)
    records.slug(attempt_id)
    directory = Path(root) / holdout_id
    rotation = records.read(directory / "rotation.json")
    records.verify(rotation)
    lock = directory / "exposure.lock"
    records.write(lock, {"attempt_id": attempt_id}, exclusive=True)
    try:
        reservations = list(directory.glob("*.exposure.json"))
        for path in reservations:
            records.verify(records.read(path))
        if (directory / "quarantine.json").exists() or len(reservations) >= rotation["max_exposures"]:
            raise F6EvidenceError("holdout_exhausted_or_quarantined_rotate_required")
        row = records.seal({"schema_version": "xuunity.holdout-exposure.v1", "attempt_id": attempt_id,
                            "rotation_hash": rotation["record_hash"], "schedule_hash": schedule_hash})
        records.write(directory / (attempt_id + ".exposure.json"), row, exclusive=True)
        if len(reservations) + 1 == rotation["max_exposures"]:
            records.write(directory / "quarantine.json", {"reason": "exposure_budget_exhausted"}, exclusive=True)
        return row
    finally:
        lock.unlink()


def complete_exposure(root: Path, *, holdout_id: str, attempt_id: str,
                      artifact: dict, verification_keys: Mapping[str, bytes]) -> dict:
    """Authenticate once and reject artifact/attempt replay across rotations."""
    records.slug(holdout_id)
    records.slug(attempt_id)
    verified = authenticate_artifact(artifact, verification_keys=verification_keys)
    root = Path(root)
    rotation = records.read(root / holdout_id / "rotation.json")
    records.verify(rotation)
    reserved = records.read(root / holdout_id / (attempt_id + ".exposure.json"))
    records.verify(reserved)
    if (reserved["rotation_hash"] != rotation["record_hash"] or verified["holdout_ref"] != holdout_id
            or verified["fixture_sha256"] != rotation["fixture_hash"]
            or attempt_id not in {row["attempt_id"] for row in verified["attempts"]}):
        raise F6EvidenceError("holdout_exposure_binding_mismatch")
    # One exclusive content-addressed receipt is the cross-rotation replay guard.
    receipts = root / "receipts"
    receipts.mkdir(exist_ok=True)
    record = records.seal({"schema_version": "xuunity.holdout-consumption.v1",
                           "holdout_id": holdout_id, "attempt_id": attempt_id,
                           "exposure_hash": reserved["record_hash"], "artifact": verified})
    lock = receipts / "completion.lock"
    records.write(lock, {"attempt_id": attempt_id}, exclusive=True)
    try:
        for path in receipts.glob("*.json"):
            previous = records.read(path)
            records.verify(previous)
            if (previous["holdout_id"], previous["attempt_id"]) == (holdout_id, attempt_id):
                raise FileExistsError("holdout_attempt_already_consumed")
        records.write(receipts / (verified["artifact_hash"] + ".json"), record, exclusive=True)
    finally:
        lock.unlink()
    return record
