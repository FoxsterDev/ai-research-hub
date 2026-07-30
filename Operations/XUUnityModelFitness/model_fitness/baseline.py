"""Content-addressed deterministic baseline (design P2.1).

One immutable seed per fixture/protocol snapshot, identified by a
Merkle-style hash over sorted entries of repo-relative path, entry type,
outcome-relevant mode, byte length, and content sha256 (symlink target for
symlinks, attested nested content hash for gitlink boundaries). Timestamps,
absolute paths, temporary refs, worktree names, and generated commit ids
never enter the identity; mtimes are normalized in the materialized seed
rather than merely ignored. Two parallel preparations from the same inputs
produce identical identities, and every clone is verified after copy."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import MODULE_SCRIPTS_DIR  # noqa: F401  (bootstraps module imports)

import xuunity_canonical as xc  # noqa: E402

SEED_IDENTITY_SCHEMA = "xuunity.seed-content.v1"
TASK_KEY_SCHEMA = "xuunity.task-measurement-key.v1"
STRICT_KEY_SCHEMA = "xuunity.strict-profile-key.v1"

NORMALIZED_MTIME = 946684800

TASK_KEY_FIELDS = frozenset(
    {
        "fixture_id",
        "fixture_revision",
        "fixture_hash",
        "suite_id",
        "suite_revision",
        "suite_hash",
        "task_prompt_hash",
        "base_content_hash",
        "protocol_content_hash",
        "ruleset_hash",
        "runner_hash",
        "observer_hash",
        "scorer_hash",
        "cause_classifier_hash",
        "statistical_method_hash",
        "oracle_schema_versions",
    }
)

STRICT_KEY_FIELDS = frozenset(
    {
        "requested_model",
        "observed_model",
        "reasoning_effort",
        "surface",
        "adapter_id",
        "adapter_version",
        "parser_capability_hash",
        "sandbox",
        "permission_mode",
        "approval_policy",
        "tool_contract",
        "context_delivery_mode",
        "enforcement_level",
        "os",
        "architecture",
        "toolchain_versions",
        "cache_image",
        "clean_cache_policy",
        "locale",
        "timezone",
        "network_policy_hash",
        "environment_allowlist_hash",
        "read_namespace_policy_hash",
        "replay_corpus_hash",
        "inference_parameters",
        "provider_backend_revision",
    }
)


class BaselineError(ValueError):
    pass


def _entry_mode(mode: int) -> str:
    return "100755" if mode & stat.S_IXUSR else "100644"


def content_entries(
    root: Path,
    *,
    gitlink_hashes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(root)
    if not root.is_dir():
        raise BaselineError(f"seed root is not a directory: {root}")
    gitlinks = {
        xc.normalize_repo_path(path): value
        for path, value in (gitlink_hashes or {}).items()
    }
    entries: list[dict[str, Any]] = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in list(dirnames):
            relative = (current_path / name).relative_to(root).as_posix()
            if relative in gitlinks:
                dirnames.remove(name)
                entries.append(
                    {
                        "path": xc.nfc(relative),
                        "type": "gitlink",
                        "mode": "160000",
                        "size": 0,
                        "sha256": gitlinks[relative],
                    }
                )
        dirnames.sort()
        for name in sorted(filenames):
            path = current_path / name
            relative = xc.nfc(path.relative_to(root).as_posix())
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                entries.append(
                    {
                        "path": relative,
                        "type": "symlink",
                        "mode": "120000",
                        "size": len(target.encode("utf-8")),
                        "sha256": xc.sha256_bytes(target.encode("utf-8")),
                    }
                )
                continue
            if not stat.S_ISREG(info.st_mode):
                raise BaselineError(f"unsupported entry type: {relative}")
            entries.append(
                {
                    "path": relative,
                    "type": "file",
                    "mode": _entry_mode(info.st_mode),
                    "size": info.st_size,
                    "sha256": xc.sha256_file(path),
                }
            )
    unresolved = sorted(set(gitlinks) - {entry["path"] for entry in entries})
    if unresolved:
        raise BaselineError(f"gitlink paths not found in tree: {unresolved}")
    aliases = xc.case_alias_conflicts([entry["path"] for entry in entries])
    if aliases:
        raise BaselineError(f"case-alias paths in seed: {aliases}")
    entries.sort(key=lambda entry: entry["path"])
    return entries


def content_identity(
    root: Path,
    *,
    gitlink_hashes: dict[str, str] | None = None,
) -> str:
    entries = content_entries(root, gitlink_hashes=gitlink_hashes)
    return xc.domain_digest(SEED_IDENTITY_SCHEMA, {"entries": entries})


def _git_lines(repo_root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", os.fspath(repo_root), *args],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise BaselineError(
            f"git {' '.join(args[:2])} failed: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()}"
        )
    return [
        line
        for line in completed.stdout.decode("utf-8").split("\0")
        if line
    ]


def git_content_entries(
    repo_root: Path,
    commit: str,
    scopes: list[str] | None = None,
    *,
    gitlink_resolver: Callable[[str, str], str] | None = None,
) -> list[dict[str, Any]]:
    """Content entries read straight from a git commit via plumbing —
    identical identity semantics to :func:`content_entries` over a
    materialized worktree of the same tracked content, with no worktree
    needed. Gitlink boundaries fail closed unless ``gitlink_resolver``
    returns an attested nested content hash for (path, commit oid)."""
    repo_root = Path(repo_root)
    listing = _git_lines(
        repo_root,
        "ls-tree", "-r", "-z", "--full-tree", commit, "--", *(scopes or []),
    )
    rows: list[tuple[str, str, str, str]] = []
    for line in listing:
        meta, _, path = line.partition("\t")
        mode, _, rest = meta.partition(" ")
        _, _, oid = rest.partition(" ")
        rows.append((mode, oid.strip(), xc.nfc(path), line))

    entries: list[dict[str, Any]] = []
    blob_rows = [row for row in rows if row[0] != "160000"]
    for mode, oid, path, _ in rows:
        if mode == "160000":
            if gitlink_resolver is None:
                raise BaselineError(
                    f"gitlink without an attested nested content hash: "
                    f"{path}@{oid}"
                )
            entries.append(
                {
                    "path": path,
                    "type": "gitlink",
                    "mode": "160000",
                    "size": 0,
                    "sha256": gitlink_resolver(path, oid),
                }
            )

    if blob_rows:
        batch_input = "".join(f"{oid}\n" for _, oid, _, _ in blob_rows)
        process = subprocess.Popen(
            ["git", "-C", os.fspath(repo_root), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        stdout, _ = process.communicate(batch_input.encode("ascii"))
        if process.returncode != 0:
            raise BaselineError("git cat-file --batch failed")
        offset = 0
        for mode, oid, path, line in blob_rows:
            header_end = stdout.index(b"\n", offset)
            header = stdout[offset:header_end].decode("ascii").split(" ")
            if header[0] != oid or header[1] == "missing":
                raise BaselineError(f"git object missing: {oid} ({path})")
            size = int(header[2])
            data = stdout[header_end + 1 : header_end + 1 + size]
            offset = header_end + 1 + size + 1
            digest = hashlib.sha256(data).hexdigest()
            if mode == "120000":
                entries.append(
                    {
                        "path": path,
                        "type": "symlink",
                        "mode": "120000",
                        "size": size,
                        "sha256": digest,
                    }
                )
            elif mode in {"100644", "100755"}:
                entries.append(
                    {
                        "path": path,
                        "type": "file",
                        "mode": mode,
                        "size": size,
                        "sha256": digest,
                    }
                )
            else:
                raise BaselineError(f"unsupported git mode {mode}: {path}")

    aliases = xc.case_alias_conflicts([entry["path"] for entry in entries])
    if aliases:
        raise BaselineError(f"case-alias paths in seed: {aliases}")
    entries.sort(key=lambda entry: entry["path"])
    return entries


def git_content_identity(
    repo_root: Path,
    commit: str,
    scopes: list[str] | None = None,
    *,
    gitlink_resolver: Callable[[str, str], str] | None = None,
) -> str:
    entries = git_content_entries(
        repo_root, commit, scopes, gitlink_resolver=gitlink_resolver
    )
    return xc.domain_digest(SEED_IDENTITY_SCHEMA, {"entries": entries})


def _copy_tree_normalized(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, symlinks=True)
    for current, dirnames, filenames in os.walk(destination, followlinks=False):
        for name in dirnames + filenames:
            path = Path(current) / name
            if not path.is_symlink():
                os.utime(path, (NORMALIZED_MTIME, NORMALIZED_MTIME))
    os.utime(destination, (NORMALIZED_MTIME, NORMALIZED_MTIME))


def materialize_seed(
    source_root: Path,
    seed_store: Path,
    *,
    gitlink_hashes: dict[str, str] | None = None,
) -> tuple[str, Path]:
    source_root = Path(source_root)
    seed_store = Path(seed_store)
    identity = content_identity(source_root, gitlink_hashes=gitlink_hashes)
    seed_path = seed_store / identity
    if seed_path.exists():
        existing = content_identity(seed_path, gitlink_hashes=gitlink_hashes)
        if existing != identity:
            raise BaselineError(
                f"seed store corrupt for {identity}: recomputed {existing}"
            )
        return identity, seed_path
    seed_store.mkdir(parents=True, exist_ok=True)
    staging = seed_store / f".staging-{identity}-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    _copy_tree_normalized(source_root, staging)
    staged_identity = content_identity(staging, gitlink_hashes=gitlink_hashes)
    if staged_identity != identity:
        shutil.rmtree(staging)
        raise BaselineError(
            "source tree changed during materialization: "
            f"{identity} -> {staged_identity}"
        )
    try:
        staging.rename(seed_path)
    except OSError:
        shutil.rmtree(staging)
        existing = content_identity(seed_path, gitlink_hashes=gitlink_hashes)
        if existing != identity:
            raise BaselineError(
                f"seed store corrupt for {identity}: recomputed {existing}"
            )
    return identity, seed_path


def clone_seed(
    seed_store: Path,
    identity: str,
    destination: Path,
    *,
    gitlink_hashes: dict[str, str] | None = None,
) -> Path:
    seed_path = Path(seed_store) / identity
    if not seed_path.is_dir():
        raise BaselineError(f"seed {identity} not present in store")
    destination = Path(destination)
    if destination.exists():
        raise BaselineError(f"clone destination already exists: {destination}")
    _copy_tree_normalized(seed_path, destination)
    cloned = content_identity(destination, gitlink_hashes=gitlink_hashes)
    if cloned != identity:
        raise BaselineError(
            f"clone identity mismatch: expected {identity}, got {cloned}"
        )
    return destination


def _key_digest(
    schema: str, fields: dict[str, Any], required: frozenset[str], label: str
) -> str:
    missing = sorted(required - set(fields))
    if missing:
        raise BaselineError(f"{label} missing fields: {missing}")
    extra = sorted(set(fields) - required)
    if extra:
        raise BaselineError(f"{label} unknown fields: {extra}")
    return xc.domain_digest(schema, fields)


def task_measurement_key(fields: dict[str, Any]) -> str:
    return _key_digest(
        TASK_KEY_SCHEMA, fields, TASK_KEY_FIELDS, "task measurement key"
    )


def strict_profile_key(
    task_fields: dict[str, Any], profile_fields: dict[str, Any]
) -> str:
    task_key = task_measurement_key(task_fields)
    missing = sorted(STRICT_KEY_FIELDS - set(profile_fields))
    if missing:
        raise BaselineError(f"strict profile key missing fields: {missing}")
    extra = sorted(set(profile_fields) - STRICT_KEY_FIELDS)
    if extra:
        raise BaselineError(f"strict profile key unknown fields: {extra}")
    payload = {"task_measurement_key": task_key, "profile": profile_fields}
    return xc.domain_digest(STRICT_KEY_SCHEMA, payload)
