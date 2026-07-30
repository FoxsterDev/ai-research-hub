#!/usr/bin/env python3
"""Normative encoding, hashing, and path rules for XUUnity control-plane JSON.

Implements the "Normative Encoding, Hashing, And Capabilities" section of
``AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md``:

- RFC 8785 (JCS) canonical bytes for the I-JSON subset these contracts use.
  Non-integer numbers are rejected outright: control-plane documents must not
  depend on implementation-defined float formatting;
- strict parsing: UTF-8 without BOM, duplicate object keys rejected before
  semantic parsing, non-finite numbers rejected;
- identifier and repository-path normalization to Unicode NFC; repo paths are
  POSIX repo-relative with absolute paths, backslashes, NUL, empty segments,
  ``.``/``..``, and ambiguous case aliases rejected;
- domain-separated digests:
  ``SHA-256("xuunity:<schema-id>:<schema-version>:\\0" || JCS-bytes)``.

Raw repository files, prompts, and transcripts are hashed as exact bytes and
never normalized; only structured control JSON goes through JCS.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

MAX_SAFE_INTEGER = 2**53 - 1

_SCHEMA_VERSION_RE = re.compile(r"^([a-z0-9][a-z0-9.\-]*)\.(v\d+)$")

_STRING_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


class CanonicalizationError(ValueError):
    pass


def _canonical_string(value: str) -> str:
    parts = ['"']
    for character in value:
        escape = _STRING_ESCAPES.get(character)
        if escape is not None:
            parts.append(escape)
        elif ord(character) < 0x20:
            parts.append(f"\\u{ord(character):04x}")
        else:
            parts.append(character)
    parts.append('"')
    return "".join(parts)


def _utf16_key(value: str) -> bytes:
    return value.encode("utf-16-be")


def canonical_json(value: Any) -> str:
    """RFC 8785 canonical form for the I-JSON subset (integers only)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalizationError(f"integer outside I-JSON range: {value}")
        return str(value)
    if isinstance(value, float):
        raise CanonicalizationError(
            "non-integer numbers are not allowed in control-plane JSON"
        )
    if isinstance(value, str):
        return _canonical_string(value)
    if isinstance(value, list):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError(f"non-string object key: {key!r}")
        items = sorted(value.items(), key=lambda item: _utf16_key(item[0]))
        return "{" + ",".join(
            f"{_canonical_string(key)}:{canonical_json(item)}"
            for key, item in items
        ) + "}"
    raise CanonicalizationError(f"unsupported JSON type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise CanonicalizationError(f"duplicate object key: {key!r}")
        result[key] = item
    return result


def _reject_constant(name: str) -> Any:
    raise CanonicalizationError(f"non-finite number not allowed: {name}")


def strict_parse(data: bytes) -> Any:
    if data.startswith(b"\xef\xbb\xbf"):
        raise CanonicalizationError("UTF-8 BOM is not allowed")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise CanonicalizationError(f"invalid UTF-8: {error}") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise CanonicalizationError(f"invalid JSON: {error}") from error


def load_strict(path: Path) -> Any:
    return strict_parse(Path(path).read_bytes())


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def normalize_repo_path(path: str) -> str:
    value = nfc(path)
    if "\x00" in value:
        raise CanonicalizationError("NUL in repository path")
    if "\\" in value:
        raise CanonicalizationError(f"backslash in repository path: {path!r}")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise CanonicalizationError(f"absolute repository path: {path!r}")
    segments = value.split("/")
    if any(segment == "" for segment in segments):
        raise CanonicalizationError(
            f"empty segment in repository path: {path!r}"
        )
    if any(segment in {".", ".."} for segment in segments):
        raise CanonicalizationError(
            f"dot segment in repository path: {path!r}"
        )
    return value


def exact_case_path_exists(repo_root: Path, repo_path: str) -> bool:
    """Existence check that is honest on case-insensitive filesystems."""
    current = Path(repo_root)
    for segment in repo_path.split("/"):
        if not current.is_dir():
            return False
        try:
            entries = os.listdir(current)
        except OSError:
            return False
        if segment not in entries:
            return False
        current = current / segment
    return True


def case_alias_conflicts(paths: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    conflicts: list[str] = []
    for path in paths:
        folded = path.casefold()
        if folded in seen and seen[folded] != path:
            conflicts.append(path)
        else:
            seen[folded] = path
    return sorted(conflicts)


def split_schema_version(schema_version: str) -> tuple[str, str]:
    match = _SCHEMA_VERSION_RE.match(schema_version)
    if not match:
        raise CanonicalizationError(
            f"invalid schema_version: {schema_version!r}"
        )
    return match.group(1), match.group(2)


def domain_digest(schema_version: str, payload: Any) -> str:
    schema_id, version = split_schema_version(schema_version)
    prefix = f"xuunity:{schema_id}:{version}:\0".encode("utf-8")
    return hashlib.sha256(prefix + canonical_bytes(payload)).hexdigest()


def document_hash(
    document: dict[str, Any], hash_field: str, extra_excluded: tuple[str, ...] = ()
) -> str:
    """Domain-separated digest of a contract document minus its own hash
    field (and any declared volatile fields)."""
    schema_version = document.get("schema_version")
    if not isinstance(schema_version, str):
        raise CanonicalizationError("document has no schema_version string")
    payload = {
        key: value
        for key, value in document.items()
        if key != hash_field and key not in extra_excluded
    }
    return domain_digest(schema_version, payload)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
