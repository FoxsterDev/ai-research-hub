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
