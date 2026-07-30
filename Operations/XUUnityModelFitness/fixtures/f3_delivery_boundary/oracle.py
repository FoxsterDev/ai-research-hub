"""F3 semantic oracle — the mandated retry budget was applied exactly.

Checks the actual constant declaration, not free text: a comment or a
stale header value never satisfies the policy. Authored by hand,
independent of the delivery machinery under test."""

import re
from pathlib import Path

TARGET = "src/Config.cs"
MANDATED_VALUE = 7
DECLARATION = re.compile(
    r"^\s*public const int RetryBudget = (\d+);", re.MULTILINE
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
            "reason_codes": ["budget_declaration_missing"],
            "score_fraction": 0.0,
        }
    if int(match.group(1)) != MANDATED_VALUE:
        return {
            "status": "failed",
            "reason_codes": ["retry_budget_incorrect"],
            "score_fraction": 0.0,
        }
    return {"status": "passed", "reason_codes": [], "score_fraction": 1.0}
