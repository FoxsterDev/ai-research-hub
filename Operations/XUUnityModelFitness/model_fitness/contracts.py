"""Schema loading and validation for the fitness-engine control plane.

Operation-owned schemas live in this operation's ``schemas/`` directory;
module-owned schemas (envelope, plan, ledger, gate result, session
attestation) stay with the module and are validated through the module's
validator unchanged."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import OPERATION_DIR

import contract_validator  # noqa: E402

SCHEMAS_DIR = OPERATION_DIR / "schemas"


class ContractError(ValueError):
    pass


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMAS_DIR / name
    if not path.is_file():
        return contract_validator.load_schema(name)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against(schema_name: str, document: Any) -> list[str]:
    return contract_validator.validate(load_schema(schema_name), document)


def require_valid(schema_name: str, document: Any, label: str) -> None:
    errors = validate_against(schema_name, document)
    if errors:
        raise ContractError(f"{label} schema errors: {errors[:5]}")


def hash_payload(value: Any) -> Any:
    """Map a document with fractional numbers onto the integer-only
    canonical stream: a non-integer float becomes a tagged shortest
    round-trip decimal string, an integral float collapses to its int.
    Used only for digest payloads, never for the stored document."""
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return {"__decimal__": repr(value)}
    if isinstance(value, dict):
        return {key: hash_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [hash_payload(item) for item in value]
    return value


def fractional_document_hash(document: dict[str, Any], hash_field: str) -> str:
    import xuunity_canonical as xc

    schema_version = document.get("schema_version")
    if not isinstance(schema_version, str):
        raise ContractError("document has no schema_version string")
    payload = {
        key: value
        for key, value in document.items()
        if key != hash_field
    }
    return xc.domain_digest(schema_version, hash_payload(payload))
