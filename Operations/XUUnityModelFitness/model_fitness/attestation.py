"""Parent-owned attestations (design P2.2).

Two boundaries are attested here and nowhere else:

- the **session attestation** binds the original task identity, repository
  snapshot, adapter profile, allowed roots, and broker capability before the
  model-writable environment exists; the MAC key stays outside the model
  process and the model cannot author or replace the record;
- the **request-boundary attestation** covers the exact post-truncation,
  post-summarization payload serialized into one provider request. A raw
  tool log or local stdout is never this boundary: an artifact counts as
  ``trusted_runtime_delivered`` only when its exact bytes are located inside
  the attested payload and the truncation canary survives after the last
  embedded segment; otherwise it stays ``runtime_delivered_unverified``.

All verification fails closed: tampered fields, wrong keys, wrong domains,
malformed timestamps, and expired windows are rejections, never warnings."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any

from . import MODULE_SCRIPTS_DIR  # noqa: F401  (bootstraps module imports)
from . import contracts

import contract_validator  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

SESSION_ATTESTATION_DOMAIN = "xuunity:session-attestation:v1"
REQUEST_ATTESTATION_DOMAIN = "xuunity:request-attestation:v1"

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AttestationError(ValueError):
    pass


def mac_hex(key: bytes, domain: str, payload_hash: str) -> str:
    if not key:
        raise AttestationError("empty MAC key")
    message = f"{domain}:\0{payload_hash}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def mac_matches(key: bytes, domain: str, payload_hash: str, signature: Any) -> bool:
    if not isinstance(signature, str) or not signature:
        return False
    return hmac.compare_digest(mac_hex(key, domain, payload_hash), signature)


def require_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        raise AttestationError(f"{label} is not a strict UTC timestamp: {value!r}")
    return value


def _opaque_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = xc.domain_digest("xuunity.opaque-id.v1", payload)
    return f"{prefix}-{digest[:32]}"


def build_session_attestation(
    key: bytes,
    *,
    session_id: str,
    task_identity: str,
    repository_content_hash: str,
    protocol_content_hash: str,
    ruleset_hash: str,
    adapter_profile_hash: str,
    requested_profile: dict[str, Any],
    allowed_roots: dict[str, list[str]],
    policy_ids: dict[str, str],
    collector_identity: dict[str, Any],
    broker_identity: dict[str, Any],
    created: str,
    expires: str,
) -> dict[str, Any]:
    require_timestamp(created, "created")
    require_timestamp(expires, "expires")
    if expires <= created:
        raise AttestationError("attestation expires before it is created")
    core = {
        "session_id": session_id,
        "task_identity": task_identity,
        "repository_content_hash": repository_content_hash,
        "adapter_profile_hash": adapter_profile_hash,
        "created": created,
    }
    attestation = {
        "schema_version": "xuunity.session-attestation.v1",
        "attestation_id": _opaque_id("att", core),
        "session_id": session_id,
        "task_identity": task_identity,
        "repository_content_hash": repository_content_hash,
        "protocol_content_hash": protocol_content_hash,
        "ruleset_hash": ruleset_hash,
        "adapter_profile_hash": adapter_profile_hash,
        "requested_profile": requested_profile,
        "allowed_roots": allowed_roots,
        "policy_ids": policy_ids,
        "collector_identity": collector_identity,
        "broker_identity": broker_identity,
        "capability_id": _opaque_id("cap", {"kind": "session", **core}),
        "created": created,
        "expires": expires,
        "signature": None,
    }
    attestation["attestation_hash"] = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    attestation["signature"] = mac_hex(
        key, SESSION_ATTESTATION_DOMAIN, attestation["attestation_hash"]
    )
    errors = contract_validator.validate_against(
        "xuunity.session-attestation.schema.json", attestation
    )
    if errors:
        raise AttestationError(f"built attestation invalid: {errors[:5]}")
    return attestation


def verify_session_attestation(
    attestation: dict[str, Any], key: bytes, *, now: str
) -> list[str]:
    reasons: list[str] = []
    errors = contract_validator.validate_against(
        "xuunity.session-attestation.schema.json", attestation
    )
    if errors:
        return [f"attestation_schema_invalid:{errors[0]}"]
    computed = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    if computed != attestation["attestation_hash"]:
        reasons.append("attestation_hash_mismatch")
    if not mac_matches(
        key,
        SESSION_ATTESTATION_DOMAIN,
        attestation["attestation_hash"],
        attestation.get("signature"),
    ):
        reasons.append("attestation_signature_invalid")
    try:
        require_timestamp(now, "now")
        created = require_timestamp(attestation["created"], "created")
        expires = require_timestamp(attestation["expires"], "expires")
        if now < created:
            reasons.append("attestation_not_yet_valid")
        if now >= expires:
            reasons.append("attestation_expired")
    except AttestationError as error:
        reasons.append(f"attestation_timestamp_invalid:{error}")
    return reasons


def sanitized_session_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(attestation)
    sanitized["signature"] = None
    return sanitized


def attest_outbound_request(
    key: bytes,
    *,
    session_attestation: dict[str, Any],
    request_seq: int,
    payload: bytes,
    artifacts: list[tuple[str, bytes]],
    canary_marker: bytes,
    adapter_identity: dict[str, Any],
) -> dict[str, Any]:
    if not canary_marker:
        raise AttestationError("empty truncation canary marker")
    segments: list[dict[str, Any]] = []
    last_segment_end = 0
    for path, content in artifacts:
        if not content:
            continue
        offset = payload.find(content)
        if offset < 0:
            continue
        segments.append(
            {
                "path": xc.normalize_repo_path(path),
                "sha256": xc.sha256_bytes(content),
                "byte_offset": offset,
                "byte_length": len(content),
            }
        )
        last_segment_end = max(last_segment_end, offset + len(content))
    segments.sort(key=lambda segment: (segment["byte_offset"], segment["path"]))
    canary_offset = payload.rfind(canary_marker)
    attestation = {
        "schema_version": "xuunity.request-attestation.v1",
        "attestation_id": _opaque_id(
            "req",
            {
                "session_attestation_id": session_attestation["attestation_id"],
                "request_seq": request_seq,
                "payload_sha256": xc.sha256_bytes(payload),
            },
        ),
        "session_attestation_id": session_attestation["attestation_id"],
        "session_id": session_attestation["session_id"],
        "request_seq": request_seq,
        "boundary": "provider_request",
        "payload_sha256": xc.sha256_bytes(payload),
        "payload_length": len(payload),
        "embedded_segments": segments,
        "truncation_canary": {
            "marker_sha256": xc.sha256_bytes(canary_marker),
            "present": canary_offset >= last_segment_end,
        },
        "adapter_identity": adapter_identity,
        "signature": None,
    }
    attestation["attestation_hash"] = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    attestation["signature"] = mac_hex(
        key, REQUEST_ATTESTATION_DOMAIN, attestation["attestation_hash"]
    )
    contracts.require_valid(
        "xuunity.request-attestation.schema.json",
        attestation,
        "request attestation",
    )
    return attestation


def verify_request_attestation(
    attestation: dict[str, Any], key: bytes
) -> list[str]:
    errors = contracts.validate_against(
        "xuunity.request-attestation.schema.json", attestation
    )
    if errors:
        return [f"request_attestation_schema_invalid:{errors[0]}"]
    reasons: list[str] = []
    computed = xc.document_hash(
        attestation, "attestation_hash", extra_excluded=("signature",)
    )
    if computed != attestation["attestation_hash"]:
        reasons.append("request_attestation_hash_mismatch")
    if not mac_matches(
        key,
        REQUEST_ATTESTATION_DOMAIN,
        attestation["attestation_hash"],
        attestation.get("signature"),
    ):
        reasons.append("request_attestation_signature_invalid")
    for segment in attestation["embedded_segments"]:
        if segment["byte_offset"] + segment["byte_length"] > attestation[
            "payload_length"
        ]:
            reasons.append(
                f"segment_outside_payload:{segment['path']}"
            )
    return reasons


def delivery_states(
    required_artifacts: list[dict[str, Any]],
    attestations: list[dict[str, Any]],
    key: bytes,
) -> dict[str, dict[str, Any]]:
    verified = [
        attestation
        for attestation in attestations
        if not verify_request_attestation(attestation, key)
    ]
    states: dict[str, dict[str, Any]] = {}
    for artifact in required_artifacts:
        path = artifact["path"]
        matched_seq: int | None = None
        for attestation in verified:
            if not attestation["truncation_canary"]["present"]:
                continue
            for segment in attestation["embedded_segments"]:
                if segment["path"] == path and segment["sha256"] == artifact[
                    "sha256"
                ]:
                    matched_seq = attestation["request_seq"]
                    break
            if matched_seq is not None:
                break
        if matched_seq is not None:
            states[path] = {
                "state": "trusted_runtime_delivered",
                "request_seq": matched_seq,
            }
        else:
            states[path] = {
                "state": "runtime_delivered_unverified",
                "request_seq": None,
            }
    return states


def context_manifest_entries(
    required_artifacts: list[dict[str, Any]],
    attestations: list[dict[str, Any]],
    key: bytes,
) -> list[dict[str, Any]]:
    states = delivery_states(required_artifacts, attestations, key)
    entries = []
    for artifact in required_artifacts:
        resolved = states[artifact["path"]]
        entries.append(
            {
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "trust": "attested"
                if resolved["state"] == "trusted_runtime_delivered"
                else "unverified",
            }
        )
    return entries


def build_protected_run_manifest(
    *,
    attempt_id: str,
    session_attestation: dict[str, Any],
    inputs: dict[str, Any],
    task_measurement_key: str,
    strict_profile_key: str,
    started: str,
    raw_evidence_hashes: dict[str, str],
    end_state: dict[str, Any] | None = None,
    oracle_materialization: dict[str, Any] | None = None,
    anchor_dir: Path | None = None,
) -> dict[str, Any]:
    require_timestamp(started, "started")
    manifest = {
        "schema_version": "xuunity.protected-run-manifest.v1",
        "attempt_id": attempt_id,
        "session_attestation_id": session_attestation["attestation_id"],
        "session_attestation_hash": session_attestation["attestation_hash"],
        "inputs": inputs,
        "task_measurement_key": task_measurement_key,
        "strict_profile_key": strict_profile_key,
        "start_state": {
            "seed_identity": inputs["seed_identity"],
            "started": started,
        },
        "end_state": end_state,
        "raw_evidence_hashes": raw_evidence_hashes,
        "oracle_materialization": oracle_materialization,
    }
    manifest["manifest_hash"] = xc.document_hash(manifest, "manifest_hash")
    contracts.require_valid(
        "xuunity.protected-run-manifest.schema.json",
        manifest,
        "protected run manifest",
    )
    if anchor_dir is not None:
        anchor_dir = Path(anchor_dir)
        anchor_dir.mkdir(parents=True, exist_ok=True)
        anchor_path = anchor_dir / f"run-manifest-{attempt_id}.json"
        anchor_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
    return manifest
