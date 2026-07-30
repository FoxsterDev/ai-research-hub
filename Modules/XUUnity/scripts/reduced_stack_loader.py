#!/usr/bin/env python3
"""Deterministic stack loader for a validated XUUnity stack plan.

Emits the plan's required artifacts as one length-prefixed bundle in
canonical path order, plus a construction manifest. Per the design:

- reads only the exact repository snapshot named by the plan and fails on any
  fingerprint drift instead of silently truncating an atomic artifact;
- denies credentials, key material, environment files, credential-bearing
  URLs, and secret-detector matches — a secret-bearing required artifact
  fails the plan, it is never redacted after hashing;
- the local delivery manifest proves bundle construction only. Without an
  adapter attestation of the exact serialized outbound request, delivery
  state remains ``runtime_delivered_unverified``.

Exit codes: 0 bundle written; 1 policy/secret/drift failure; 2 usage or
schema error; 4 not runnable within the declared surface budget.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract_validator  # noqa: E402
import xuunity_canonical as xc  # noqa: E402

BUNDLE_MAGIC = "XUUNITY-STACK-BUNDLE v1"
MANIFEST_SCHEMA_VERSION = "xuunity.delivery-manifest.v1"

EXIT_OK = 0
EXIT_POLICY = 1
EXIT_USAGE = 2
EXIT_NOT_RUNNABLE = 4

DENIED_NAME_PATTERNS = (
    re.compile(r"(^|/)\.env(\.|$)"),
    re.compile(r"(^|/)id_(rsa|ed25519|ecdsa)(\.|$)"),
    re.compile(r"\.(pem|p12|pfx|keystore|jks)$", re.IGNORECASE),
    re.compile(r"(^|/)credentials(\.|$)", re.IGNORECASE),
)

SECRET_CONTENT_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    re.compile(r"://[^/\s:@]+:[^/\s:@]+@"),
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9_\-/+]{16,}['\"]"
    ),
)


class LoaderError(Exception):
    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


def scan_for_secrets(path: str, data: bytes) -> list[str]:
    findings: list[str] = []
    for pattern in DENIED_NAME_PATTERNS:
        if pattern.search(path):
            findings.append(f"denied_artifact_name:{path}")
            break
    text = data.decode("utf-8", errors="replace")
    for pattern in SECRET_CONTENT_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret_content_match:{pattern.pattern[:40]}")
    return findings


def _allowed_by_roots(path: str, allowed_roots: list[str] | None) -> bool:
    if not allowed_roots:
        return True
    return any(
        path == root or path.startswith(root.rstrip("/") + "/")
        for root in allowed_roots
    )


def build_bundle(
    repo_root: Path,
    plan: dict[str, Any],
    *,
    allowed_guidance_roots: list[str] | None = None,
    max_bundle_bytes: int | None = None,
) -> tuple[bytes, dict[str, Any]]:
    errors = contract_validator.validate_against(
        "xuunity.stack-plan.schema.json", plan
    )
    if errors:
        raise LoaderError(f"plan schema errors: {errors[:5]}", EXIT_USAGE)

    artifacts = sorted(plan["required_artifacts"], key=lambda a: a["path"])
    buffer = io.BytesIO()
    buffer.write(f"{BUNDLE_MAGIC}\n".encode("utf-8"))
    buffer.write(f"plan {plan['plan_hash']}\n".encode("utf-8"))
    buffer.write(f"files {len(artifacts)}\n".encode("utf-8"))
    manifest_files: list[dict[str, Any]] = []
    total_bytes = 0
    for artifact in artifacts:
        path = artifact["path"]
        if not _allowed_by_roots(path, allowed_guidance_roots):
            raise LoaderError(
                f"artifact outside attested guidance roots: {path}",
                EXIT_POLICY,
            )
        full = Path(repo_root) / path
        if not xc.exact_case_path_exists(repo_root, path):
            raise LoaderError(
                f"required artifact missing from snapshot: {path}", EXIT_POLICY
            )
        data = full.read_bytes()
        digest = xc.sha256_bytes(data)
        if digest != artifact["sha256"] or len(data) != artifact["bytes"]:
            raise LoaderError(
                f"snapshot drift for {path}: plan fingerprint does not match "
                f"the working tree; refusing to load a different file",
                EXIT_POLICY,
            )
        findings = scan_for_secrets(path, data)
        if findings:
            raise LoaderError(
                f"secret-bearing required artifact fails the plan: {path} "
                f"({findings[0]})",
                EXIT_POLICY,
            )
        buffer.write(
            f"file {len(data)} {digest} {path}\n".encode("utf-8")
        )
        buffer.write(data)
        buffer.write(b"\n")
        total_bytes += len(data)
        manifest_files.append(
            {"path": path, "bytes": len(data), "sha256": digest}
        )
    buffer.write(b"end\n")
    bundle = buffer.getvalue()
    if max_bundle_bytes is not None and len(bundle) > max_bundle_bytes:
        raise LoaderError(
            f"selected atomic stack ({len(bundle)} bytes) does not fit the "
            f"declared surface budget ({max_bundle_bytes} bytes); the loader "
            f"never truncates selected files",
            EXIT_NOT_RUNNABLE,
        )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "plan_hash": plan["plan_hash"],
        "bundle_sha256": xc.sha256_bytes(bundle),
        "bundle_bytes": len(bundle),
        "content_bytes": total_bytes,
        "files": manifest_files,
        "delivery_state": "constructed_only",
        "note": (
            "This manifest proves bundle construction only. Delivery becomes "
            "trusted_runtime_delivered only with an adapter attestation over "
            "the exact serialized outbound request that precedes the model "
            "inference; otherwise it is runtime_delivered_unverified."
        ),
    }
    return bundle, manifest


def parse_bundle(bundle: bytes) -> list[dict[str, Any]]:
    """Parse and verify a bundle; returns the file entries. Used by tests and
    consumers to prove the framing is collision-free."""
    stream = io.BytesIO(bundle)

    def read_line() -> str:
        line = stream.readline()
        if not line.endswith(b"\n"):
            raise LoaderError("truncated bundle", EXIT_POLICY)
        return line[:-1].decode("utf-8")

    if read_line() != BUNDLE_MAGIC:
        raise LoaderError("bad bundle magic", EXIT_POLICY)
    plan_line = read_line()
    if not plan_line.startswith("plan "):
        raise LoaderError("missing plan hash line", EXIT_POLICY)
    count_line = read_line()
    if not count_line.startswith("files "):
        raise LoaderError("missing files count line", EXIT_POLICY)
    count = int(count_line.split(" ", 1)[1])
    entries: list[dict[str, Any]] = []
    for _ in range(count):
        header = read_line()
        if not header.startswith("file "):
            raise LoaderError("missing file header", EXIT_POLICY)
        _, length_text, digest, path = header.split(" ", 3)
        data = stream.read(int(length_text))
        if len(data) != int(length_text):
            raise LoaderError("truncated file payload", EXIT_POLICY)
        if stream.read(1) != b"\n":
            raise LoaderError("missing payload terminator", EXIT_POLICY)
        if xc.sha256_bytes(data) != digest:
            raise LoaderError(f"payload hash mismatch for {path}", EXIT_POLICY)
        entries.append({"path": path, "bytes": len(data), "sha256": digest})
    if read_line() != "end":
        raise LoaderError("missing bundle terminator", EXIT_POLICY)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--bundle-output")
    parser.add_argument(
        "--allowed-guidance-root",
        action="append",
        help="restrict artifacts to these repo-relative roots (repeatable); "
        "supplied by the host from its session attestation",
    )
    parser.add_argument("--max-bundle-bytes", type=int)
    args = parser.parse_args()

    try:
        plan = xc.load_strict(Path(args.plan))
        bundle, manifest = build_bundle(
            Path(args.repo_root),
            plan,
            allowed_guidance_roots=args.allowed_guidance_root,
            max_bundle_bytes=args.max_bundle_bytes,
        )
    except (xc.CanonicalizationError, OSError) as error:
        print(f"loader error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except LoaderError as error:
        print(f"loader error: {error}", file=sys.stderr)
        return error.exit_code

    manifest_path = Path(args.manifest_output)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    if args.bundle_output:
        Path(args.bundle_output).write_bytes(bundle)
    print(
        f"bundle: {manifest['bundle_bytes']} bytes, "
        f"{len(manifest['files'])} files, sha256 {manifest['bundle_sha256']}"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
