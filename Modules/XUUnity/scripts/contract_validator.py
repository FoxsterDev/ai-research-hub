#!/usr/bin/env python3
"""Minimal structural validator for the XUUnity contract schemas.

Covers exactly the JSON Schema subset those contracts use: ``type``,
``const``, ``enum``, ``required``, ``properties``, ``additionalProperties``
(boolean or schema), ``items``, ``minItems``/``maxItems``, ``minLength``,
``minimum``/``maximum``, ``pattern``, ``anyOf``, and local ``$ref`` into
``$defs``. Unknown keys in an object are errors when the schema declares
``additionalProperties: false`` — contract objects fail closed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def validate(
    schema: dict[str, Any],
    document: Any,
    root: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    if root is None:
        root = schema
    errors: list[str] = []
    if "$ref" in schema:
        target: Any = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        return validate(target, document, root, path)
    if "anyOf" in schema:
        candidates = [
            validate(option, document, root, path)
            for option in schema["anyOf"]
        ]
        if not any(not errs for errs in candidates):
            errors.append(f"{path}: no anyOf branch matched")
        return errors
    if "const" in schema and document != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and document not in schema["enum"]:
        errors.append(f"{path}: {document!r} not in enum")
    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_TYPE_CHECKS[name](document) for name in types):
            errors.append(f"{path}: type {types} expected")
            return errors
    if isinstance(document, str):
        if "minLength" in schema and len(document) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength")
        if "pattern" in schema and not re.search(schema["pattern"], document):
            errors.append(f"{path}: pattern mismatch")
    if isinstance(document, (int, float)) and not isinstance(document, bool):
        if "minimum" in schema and document < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and document > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(document, dict):
        for key in schema.get("required", []):
            if key not in document:
                errors.append(f"{path}: missing required {key}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        for key, value in document.items():
            if key in properties:
                errors.extend(
                    validate(properties[key], value, root, f"{path}.{key}")
                )
            elif isinstance(additional, dict):
                errors.extend(
                    validate(additional, value, root, f"{path}.{key}")
                )
            elif additional is False:
                errors.append(f"{path}: unknown property {key!r}")
    if isinstance(document, list):
        if "minItems" in schema and len(document) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(document) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems")
        if isinstance(schema.get("items"), dict):
            for index, value in enumerate(document):
                errors.extend(
                    validate(schema["items"], value, root, f"{path}[{index}]")
                )
    return errors


def validate_against(schema_name: str, document: Any) -> list[str]:
    schema = load_schema(schema_name)
    return validate(schema, document)
