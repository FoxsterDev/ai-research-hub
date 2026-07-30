"""F4 semantic oracle — the version constant was bumped exactly.

Checks the actual declaration; a wrong target value or an untouched seed
fails. Authored by hand, independent of the resolver under test."""

import re
from pathlib import Path

TARGET = "src/BuildInfo.cs"
EXPECTED = "1.2.3"
DECLARATION = re.compile(
    r"^\s*public const string Version = \"([^\"]+)\";", re.MULTILINE
)


def evaluate(tree):
    path = Path(tree) / TARGET
    if not path.is_file():
        return {
            "status": "failed",
            "reason_codes": ["target_file_missing"],
            "score_fraction": 0.0,
        }
    match = DECLARATION.search(path.read_text(encoding="utf-8"))
    if match is None:
        return {
            "status": "failed",
            "reason_codes": ["version_declaration_missing"],
            "score_fraction": 0.0,
        }
    value = match.group(1)
    if value == "1.2.2":
        return {
            "status": "failed",
            "reason_codes": ["version_not_bumped"],
            "score_fraction": 0.0,
        }
    if value != EXPECTED:
        return {
            "status": "failed",
            "reason_codes": ["version_incorrect"],
            "score_fraction": 0.0,
        }
    return {"status": "passed", "reason_codes": [], "score_fraction": 1.0}
