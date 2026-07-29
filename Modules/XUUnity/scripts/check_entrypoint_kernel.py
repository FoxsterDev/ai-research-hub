#!/usr/bin/env python3
"""Model-free integrity check for the start-session entrypoint kernel.

Enforces that an always-loaded entrypoint stays head-complete: every
must-survive marker (must-load rule, routing procedure, execution contract,
root-cause gate, output contract) is byte-complete within the smallest head
read window. The canonical skill router and output contract must also remain
within the tail window.

This replaces the old "150-220 lines / split by 300" line rule. The binding
constraint is bytes, not lines, because some harnesses truncate file reads:
Codex CLI reads files via shell with a ~10 KB head+tail cap that DROPS THE
MIDDLE. A marker outside the head window is silently lost on that lane.

Usage:
    python3 check_entrypoint_kernel.py [entrypoint.md ...]
Exit code 0 if all checked files pass, 1 otherwise.
"""
import os
import sys

HEAD_BUDGET = 8192       # target smallest head window, in bytes
# Observed reference point for one shell-output lane. This checker does not
# enforce total file size; it enforces the byte-complete head/tail kernel.
REFERENCE_TRUNCATION_CEILING = 10240

# (label, literal substring that must START and END within the head window)
HEAD_MARKERS = [
    ("must-load rule", "first line through EOF"),
    ("route procedure", "Route (one-shot"),
    ("execution contract", "knowledge/execution_contract.md"),
    ("root-cause gate", "Root-cause gate"),
    ("pre-edit gate", "**Pre-edit gate.**"),
    ("output contract", "Required output"),
]
# Substrings that must appear within the tail window as recency anchors.
TAIL_MARKERS = [
    ("canonical skill router", "## Skill Routing Hints", True),
    ("output-contract restatement", "Re-state the", False),
]

# Protected headings are exact public routing anchors. A duplicate can make a
# measurement select the wrong section even when both copies are individually
# well-formed.
UNIQUE_MARKERS = [
    ("canonical skill router", "## Skill Routing Hints"),
]


def contains_marker(data, marker, exact_line):
    encoded = marker.encode()
    if exact_line:
        return any(line.rstrip(b"\r") == encoded for line in data.splitlines())
    return encoded in data


def check(path):
    with open(path, "rb") as f:
        data = f.read()
    n = len(data)
    tail = data[-HEAD_BUDGET:] if n > HEAD_BUDGET else data
    errors = []
    offsets = {}
    for label, marker in HEAD_MARKERS:
        idx = data.find(marker.encode())
        if idx == -1:
            errors.append("MISSING [%s]: %r not found" % (label, marker))
        elif idx + len(marker) > HEAD_BUDGET:
            errors.append(
                "OUT-OF-HEAD [%s]: %r starts at byte %d (> %d head budget)"
                % (label, marker, idx, HEAD_BUDGET))
        else:
            offsets[label] = idx
    for label, marker in UNIQUE_MARKERS:
        encoded = marker.encode()
        count = sum(
            line.rstrip(b"\r") == encoded
            for line in data.splitlines()
        )
        if count != 1:
            errors.append(
                "INVALID COUNT [%s]: %r occurs %d times (expected exactly 1)"
                % (label, marker, count))
    for tlabel, tmarker, exact_line in TAIL_MARKERS:
        if not contains_marker(tail, tmarker, exact_line):
            errors.append(
                "MISSING tail marker [%s]: %r not within last %d bytes"
                % (tlabel, tmarker, HEAD_BUDGET))

    print("%s: %d bytes (head budget %d, reference truncation ceiling %d)"
          % (path, n, HEAD_BUDGET, REFERENCE_TRUNCATION_CEILING))
    if errors:
        print("  FAIL — entrypoint kernel integrity:")
        for e in errors:
            print("    - " + e)
        return False
    print("  OK — kernel head-complete:")
    for label, _ in HEAD_MARKERS:
        print("    - %-20s byte %d" % (label, offsets[label]))
    for label, _, _ in TAIL_MARKERS:
        print("    - %-20s present within last %d bytes" % (label, HEAD_BUDGET))
    return True


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    default = os.path.normpath(os.path.join(here, "..", "tasks", "start_session.md"))
    paths = argv[1:] or [default]
    ok = True
    for p in paths:
        ok = check(p) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
