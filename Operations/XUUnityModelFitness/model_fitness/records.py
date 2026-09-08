"""Atomic parent-owned records; integrity hashes are not OS protection."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import xuunity_canonical as xc

from .contracts import fractional_document_hash


def slug(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", value):
        raise ValueError("invalid bounded record identifier")
    return value


def read(path: Path) -> dict[str, Any]:
    value = xc.load_strict(Path(path))
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object")
    return value


def seal(document: dict[str, Any], field: str = "record_hash") -> dict[str, Any]:
    result = dict(document)
    result[field] = fractional_document_hash(result, field)
    return result


def verify(document: dict[str, Any], field: str = "record_hash") -> None:
    if document.get(field) != fractional_document_hash(document, field):
        raise ValueError(f"{field}_mismatch")


def write(path: Path, document: dict[str, Any], *, exclusive: bool = False) -> None:
    """Publish a complete record atomically; exclusive publication never replaces."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(document, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def disjoint(*paths: Path) -> None:
    resolved = [Path(path).resolve() for path in paths]
    for index, path in enumerate(resolved):
        if any(path == other or path in other.parents or other in path.parents
               for other in resolved[index + 1:]):
            raise ValueError("workspace_and_protected_roots_overlap")
