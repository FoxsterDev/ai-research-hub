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

from . import attestation, contracts

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
