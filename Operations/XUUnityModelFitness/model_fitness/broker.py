"""Parent-owned write broker (design P2.2, contract 5).

The broker is the only component that can mint an ``authoritative`` gate
result, and only after it verifies the session attestation MAC, the P1 gate
decision over protected inputs, and an OS-enforced write boundary. A
voluntarily invoked script is never an authoritative gate: boundaries that
the model process could revoke (same-uid chmod) stay ``audited``.

Every mutation batch needs a fresh one-use capability in the MAC domain
``xuunity:mutation-capability:v1``, bound to the attestation id, session id,
repository content hash, plan/ledger/semantic-result hashes, mutation
generation, scope, and expiry. Issuance and consumption are stored
atomically (``O_CREAT|O_EXCL``) outside the model namespace; replay,
duplicate consumption, expiry, generation rollback, and cross-session use
fail closed. Authoritative mode reconciles after each brokered batch before
another batch can be authorized, and the per-batch journal captures
intermediate mutations so mutate-then-restore cannot disappear."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
from typing import Any, NamedTuple

from . import MODULE_SCRIPTS_DIR  # noqa: F401  (bootstraps module imports)
from . import attestation as att
from . import contracts

import reduced_stack_gate as gate  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

CAPABILITY_DOMAIN = "xuunity:mutation-capability:v1"
CAPABILITY_BINDING_SCHEMA = "xuunity.mutation-capability.v1"
SEMANTIC_RESULT_SCHEMA = "xuunity.semantic-check-results.v1"

AUTHORITATIVE_MECHANISMS = frozenset(
    {"os_readonly_mount", "posix_uid_separation", "sandbox_profile_probe"}
)

BINDING_FIELDS = frozenset(
    {
        "attestation_id",
        "session_id",
        "repository_content_hash",
        "plan_hash",
        "ledger_hash",
        "semantic_result_hash",
        "mutation_generation",
        "scope",
        "expires",
    }
)


class BrokerError(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}{': ' + detail if detail else ''}")
        self.reason = reason


class BoundaryReport(NamedTuple):
    authoritative: bool
    mechanism: str
    reasons: tuple[str, ...]


class DeclaredWriteBoundary:
    """Boundary the parent enforces itself (read-only mount, uid separation).

    Only mechanisms in AUTHORITATIVE_MECHANISMS can yield an authoritative
    report; anything else is recorded and stays audited."""

    def __init__(self, mechanism: str) -> None:
        self.mechanism = mechanism

    def verify(self, worktree: Path) -> BoundaryReport:
        if self.mechanism in AUTHORITATIVE_MECHANISMS:
            return BoundaryReport(True, self.mechanism, ())
        return BoundaryReport(
            False, self.mechanism, (f"mechanism_not_authoritative:{self.mechanism}",)
        )


class SameUidChmodBoundary:
    """chmod by the same uid is advisory: the model process can chmod back.

    Reports whether write bits are currently absent, but never authoritative."""

    def verify(self, worktree: Path) -> BoundaryReport:
        reasons = ["chmod_same_uid_revocable"]
        for current, dirnames, filenames in os.walk(worktree):
            for name in dirnames + filenames:
                path = Path(current) / name
                if path.is_symlink():
                    continue
                if path.stat().st_mode & 0o222:
                    reasons.append("writable_bits_present")
                    return BoundaryReport(False, "chmod_same_uid", tuple(reasons))
        return BoundaryReport(False, "chmod_same_uid", tuple(reasons))


def semantic_result_hash(semantic_rows: list[dict[str, Any]]) -> str:
    return xc.domain_digest(SEMANTIC_RESULT_SCHEMA, {"results": semantic_rows})


def _require_binding(binding: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(BINDING_FIELDS - set(binding))
    extra = sorted(set(binding) - BINDING_FIELDS)
    if missing or extra:
        raise BrokerError(
            "binding_fields_invalid", f"missing={missing} extra={extra}"
        )
    att.require_timestamp(binding["expires"], "binding expires")
    if not isinstance(binding["mutation_generation"], int) or isinstance(
        binding["mutation_generation"], bool
    ) or binding["mutation_generation"] < 0:
        raise BrokerError("binding_generation_invalid")
    normalized = dict(binding)
    normalized["scope"] = sorted(
        _normalize_scope_entry(path) for path in binding["scope"]
    )
    return normalized


def _normalize_scope_entry(entry: str) -> str:
    if entry.endswith("/"):
        return xc.normalize_repo_path(entry[:-1]) + "/"
    return xc.normalize_repo_path(entry)


def binding_hash(binding: dict[str, Any]) -> str:
    return xc.domain_digest(
        CAPABILITY_BINDING_SCHEMA, _require_binding(binding)
    )


def mint_capability(key: bytes, binding: dict[str, Any]) -> tuple[str, str]:
    digest = binding_hash(binding)
    token = att.mac_hex(key, CAPABILITY_DOMAIN, digest)
    return f"mcap-{digest[:32]}", token


def verify_capability(
    key: bytes, token: str, binding: dict[str, Any], *, now: str
) -> list[str]:
    reasons: list[str] = []
    try:
        digest = binding_hash(binding)
    except BrokerError as error:
        return [error.reason]
    if not att.mac_matches(key, CAPABILITY_DOMAIN, digest, token):
        reasons.append("capability_token_invalid")
    att.require_timestamp(now, "now")
    if now >= binding["expires"]:
        reasons.append("capability_expired")
    return reasons


class AuthorizationOutcome(NamedTuple):
    result: dict[str, Any]
    capability_id: str | None
    token: str | None


class Broker:
    """One broker instance per attested session, rooted outside the model
    namespace. The capability token is returned to the parent runner only and
    must never be written into any model-readable artifact."""

    def __init__(
        self,
        root: Path,
        key: bytes,
        session_attestation: dict[str, Any],
        worktree: Path,
        write_boundary: Any,
    ) -> None:
        if not key:
            raise BrokerError("broker_key_empty")
        self.root = Path(root)
        self.key = key
        self.attestation = session_attestation
        self.worktree = Path(worktree)
        self.write_boundary = write_boundary
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "issued").mkdir(exist_ok=True)
        (self.root / "spent").mkdir(exist_ok=True)
        (self.root / "journal").mkdir(exist_ok=True)
        (self.root / "gate").mkdir(exist_ok=True)
        self._attestation_path = self.root / "session_attestation.json"
        self._attestation_path.write_text(
            json.dumps(session_attestation, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self._state_path = self.root / "state.json"
        if not self._state_path.exists():
            self._write_state(
                {"mutation_generation": 0, "reconciled_generation": 0}
            )

    def _state(self) -> dict[str, int]:
        return json.loads(self._state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict[str, int]) -> None:
        staging = self._state_path.with_suffix(".tmp")
        staging.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        staging.replace(self._state_path)

    def _run_gate(
        self,
        plan_path: Path,
        ledger_path: Path,
        semantic_input_manifest: Path | None,
        output: Path,
        *,
        reconcile: bool,
        reconcile_args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        namespace = argparse.Namespace(
            plan=str(plan_path),
            ledger=str(ledger_path),
            semantic_input_manifest=str(semantic_input_manifest)
            if semantic_input_manifest
            else None,
            session_attestation=str(self._attestation_path),
            output=str(output),
        )
        for name, value in (reconcile_args or {}).items():
            setattr(namespace, name, value)
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = gate._check_or_reconcile(namespace, reconcile)
        if exit_code == gate.EXIT_USAGE:
            raise BrokerError("gate_usage_error")
        return json.loads(output.read_text(encoding="utf-8"))

    def authorize_batch(
        self,
        plan_path: Path,
        ledger_path: Path,
        *,
        now: str,
        expires: str,
        semantic_input_manifest: Path | None = None,
    ) -> AuthorizationOutcome:
        att.require_timestamp(now, "now")
        att.require_timestamp(expires, "expires")
        attestation_reasons = att.verify_session_attestation(
            self.attestation, self.key, now=now
        )
        if attestation_reasons:
            raise BrokerError(
                "session_attestation_rejected", ",".join(attestation_reasons)
            )
        state = self._state()
        if state["mutation_generation"] != state["reconciled_generation"]:
            raise BrokerError(
                "reconcile_required_before_next_batch",
                f"generation {state['mutation_generation']} not reconciled",
            )
        generation = state["mutation_generation"]
        output = self.root / "gate" / f"authorize-{generation}.json"
        result = self._run_gate(
            Path(plan_path), Path(ledger_path), semantic_input_manifest,
            output, reconcile=False,
        )
        if result["decision"] != "pass":
            return AuthorizationOutcome(result, None, None)

        report: BoundaryReport = self.write_boundary.verify(self.worktree)
        if not report.authoritative:
            result["reason_codes"] = sorted(
                set(result["reason_codes"])
                | {f"write_boundary_unverified:{report.mechanism}"}
                | set(report.reasons)
            )
            output.write_text(
                json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
            )
            return AuthorizationOutcome(result, None, None)

        plan = xc.load_strict(Path(plan_path))
        binding = {
            "attestation_id": self.attestation["attestation_id"],
            "session_id": self.attestation["session_id"],
            "repository_content_hash": self.attestation[
                "repository_content_hash"
            ],
            "plan_hash": result["plan_hash"],
            "ledger_hash": result["ledger_hash"],
            "semantic_result_hash": semantic_result_hash(
                result["semantic_check_results"]
            ),
            "mutation_generation": generation,
            "scope": sorted(plan["planned_mutation_scope"]),
            "expires": expires,
        }
        capability_id, token = mint_capability(self.key, binding)
        record = {
            "schema_version": "xuunity.mutation-capability.v1",
            "capability_id": capability_id,
            "binding": _require_binding(binding),
            "issued": now,
            "token_sha256": xc.sha256_bytes(token.encode("utf-8")),
            "consumption": None,
        }
        contracts.require_valid(
            "xuunity.mutation-capability.schema.json", record,
            "capability record",
        )
        record_path = self.root / "issued" / f"{capability_id}.json"
        try:
            descriptor = os.open(
                record_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError:
            raise BrokerError(
                "capability_already_issued", capability_id
            ) from None
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)

        result["enforcement_mode"] = "authoritative"
        result["authorization"] = {
            "capability_id": capability_id,
            "expires": expires,
            "mutation_generation": generation,
            "scope": record["binding"]["scope"],
        }
        errors = contracts.validate_against(
            "xuunity.stack-gate-result.schema.json", result
        )
        if errors:
            raise BrokerError("gate_result_invalid", str(errors[:3]))
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        return AuthorizationOutcome(result, capability_id, token)

    def _consume(self, capability_id: str, *, now: str) -> Path:
        spent_path = self.root / "spent" / capability_id
        try:
            descriptor = os.open(
                spent_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError:
            raise BrokerError("capability_replayed", capability_id) from None
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"consumed": now}))
        return spent_path

    def _record_consumption(
        self,
        capability_id: str,
        *,
        now: str,
        applied: bool,
        batch_paths: list[str],
        refusal_reason: str | None,
    ) -> None:
        record_path = self.root / "issued" / f"{capability_id}.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["consumption"] = {
            "consumed": now,
            "applied": applied,
            "batch_paths": sorted(batch_paths),
            "refusal_reason": refusal_reason,
        }
        record_path.write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )

    def _scope_violation(
        self, normalized: str, scope: list[str]
    ) -> str | None:
        roots = self.attestation["allowed_roots"]["mutation"]

        def matches(path: str, entries: list[str]) -> bool:
            for entry in entries:
                if entry.endswith("/"):
                    if path.startswith(entry):
                        return True
                elif path == entry or path.startswith(entry + "/"):
                    return True
            return False

        if not matches(normalized, scope):
            return f"path_outside_capability_scope:{normalized}"
        if not matches(normalized, roots):
            return f"path_outside_attested_mutation_roots:{normalized}"
        worktree_real = self.worktree.resolve()
        candidate = self.worktree / normalized
        probe = candidate
        while True:
            if probe.exists() or probe.is_symlink():
                if probe.is_symlink():
                    return f"symlink_in_mutation_path:{normalized}"
            if probe == self.worktree:
                break
            probe = probe.parent
        parent_real = candidate.parent.resolve()
        if not parent_real.is_relative_to(worktree_real):
            return f"path_escapes_worktree:{normalized}"
        return None

    def apply_batch(
        self,
        capability_id: str,
        token: str,
        batch: list[dict[str, Any]],
        *,
        now: str,
    ) -> dict[str, Any]:
        att.require_timestamp(now, "now")
        record_path = self.root / "issued" / f"{capability_id}.json"
        if not record_path.is_file():
            raise BrokerError("capability_unknown", capability_id)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        binding = record["binding"]
        reasons = verify_capability(self.key, token, binding, now=now)
        if reasons:
            raise BrokerError("capability_rejected", ",".join(reasons))
        if binding["session_id"] != self.attestation["session_id"] or binding[
            "attestation_id"
        ] != self.attestation["attestation_id"]:
            raise BrokerError("capability_cross_session", capability_id)
        if (self.root / "spent" / capability_id).exists():
            raise BrokerError("capability_replayed", capability_id)
        state = self._state()
        if binding["mutation_generation"] != state["mutation_generation"]:
            raise BrokerError(
                "capability_generation_stale",
                f"bound {binding['mutation_generation']}, "
                f"current {state['mutation_generation']}",
            )
        if not batch:
            raise BrokerError("empty_mutation_batch")

        normalized_batch: list[tuple[str, bytes]] = []
        refusal: str | None = None
        for entry in batch:
            try:
                normalized = xc.normalize_repo_path(entry["path"])
            except xc.CanonicalizationError as error:
                refusal = f"path_invalid:{entry['path']}:{error}"
                break
            violation = self._scope_violation(normalized, binding["scope"])
            if violation:
                refusal = violation
                break
            content = entry["content"]
            if isinstance(content, str):
                content = content.encode("utf-8")
            normalized_batch.append((normalized, content))

        self._consume(capability_id, now=now)
        batch_paths = [path for path, _ in normalized_batch] or [
            str(entry.get("path")) for entry in batch
        ]
        if refusal is not None:
            self._record_consumption(
                capability_id, now=now, applied=False,
                batch_paths=batch_paths, refusal_reason=refusal,
            )
            raise BrokerError("mutation_batch_refused", refusal)

        journal_entries = []
        for normalized, content in normalized_batch:
            target = self.worktree / normalized
            before = xc.sha256_file(target) if target.is_file() else None
            journal_entries.append(
                {
                    "path": normalized,
                    "before_sha256": before,
                    "after_sha256": xc.sha256_bytes(content),
                    "byte_length": len(content),
                }
            )
        generation = state["mutation_generation"]
        journal = {
            "capability_id": capability_id,
            "mutation_generation": generation,
            "applied": True,
            "consumed": now,
            "entries": journal_entries,
        }
        journal_path = self.root / "journal" / f"batch-{generation}.json"
        journal_path.write_text(
            json.dumps(journal, indent=2, sort_keys=True), encoding="utf-8"
        )
        for normalized, content in normalized_batch:
            target = self.worktree / normalized
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self._record_consumption(
            capability_id, now=now, applied=True,
            batch_paths=batch_paths, refusal_reason=None,
        )
        state["mutation_generation"] = generation + 1
        self._write_state(state)
        return journal

    def reconcile_batch(
        self,
        plan_path: Path,
        ledger_path: Path,
        parent_diff_path: Path,
        *,
        repo_root: Path,
        ruleset_path: Path,
        task_envelope_path: Path,
        task_text_file: Path | None = None,
        semantic_input_manifest: Path | None = None,
        ruleset_extensions: list[Path] | None = None,
    ) -> dict[str, Any]:
        state = self._state()
        generation = state["mutation_generation"]
        if generation == state["reconciled_generation"]:
            raise BrokerError("nothing_to_reconcile")
        output = self.root / "gate" / f"reconcile-{generation}.json"
        result = self._run_gate(
            Path(plan_path), Path(ledger_path), semantic_input_manifest,
            output, reconcile=True,
            reconcile_args={
                "parent_diff": str(parent_diff_path),
                "repo_root": str(repo_root),
                "ruleset": str(ruleset_path),
                "task_envelope": str(task_envelope_path),
                "task_text_file": str(task_text_file)
                if task_text_file
                else None,
                "ruleset_extension": [
                    str(path) for path in ruleset_extensions or []
                ],
            },
        )
        if result["decision"] == "pass":
            state["reconciled_generation"] = generation
            self._write_state(state)
        return result
