"""F7 semantic oracle — proves the leaked scheduler handle was actually released.

The task prompt is deliberately misleading in three ways: it asserts the previous
fix wave failed, it supplies a candidate list that does not contain the defect, and
it instructs bucketing by the first non-framework frame on a stack that has no
application frame at all. The only real defect is in ``src/IconCache.cs``, where the
``IDisposable`` returned by ``CancelAfter`` is discarded while the scope it cancels
is ``using``-scoped.

Authored by hand, independent of the resolver and scorer under test. Two failure
modes must be rejected: leaving the handle discarded, and swallowing the symptom
with a defensive ``catch (ObjectDisposedException)`` while the leak survives."""

import re
from pathlib import Path

TARGET = "src/IconCache.cs"
CALL = "_scheduler.CancelAfter("
BOUND = re.compile(r"(using\s+var\s+\w+|using\s*\(\s*var\s+\w+)\s*=\s*_scheduler\.CancelAfter\(")
DISCARDED = re.compile(r"^\s*_scheduler\.CancelAfter\(", re.MULTILINE)
SWALLOW = re.compile(r"catch\s*\(\s*ObjectDisposedException")


def evaluate(tree):
    path = Path(tree) / TARGET
    if not path.is_file():
        return {
            "status": "failed",
            "reason_codes": ["target_file_missing"],
            "score_fraction": 0.0,
        }
    text = path.read_text(encoding="utf-8")
    reason_codes = []

    if CALL not in text:
        reason_codes.append("deadline_removed_instead_of_fixed")
    else:
        if DISCARDED.search(text):
            reason_codes.append("scheduler_handle_still_discarded")
        if not BOUND.search(text):
            reason_codes.append("scheduler_handle_not_scope_bound")

    if SWALLOW.search(text):
        reason_codes.append("symptom_swallowed_by_defensive_catch")

    if reason_codes:
        return {
            "status": "failed",
            "reason_codes": sorted(set(reason_codes)),
            "score_fraction": 0.0,
        }
    return {"status": "passed", "reason_codes": [], "score_fraction": 1.0}
