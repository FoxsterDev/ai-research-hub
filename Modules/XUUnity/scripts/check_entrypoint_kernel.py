#!/usr/bin/env python3
"""Model-free integrity check for the start-session entrypoint kernel.

Enforces that an always-loaded entrypoint stays head-complete: every
must-survive marker (must-load rule, routing procedure, execution contract,
root-cause gate, output contract) is byte-complete within the smallest head
read window, and the output contract is restated within the tail window.

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
HARD_CEILING = 10240     # Codex CLI shell-output truncation, in bytes

# (label, literal substring that must START and END within the head window)
HEAD_MARKERS = [
    ("must-load rule", "first line through EOF"),
    ("route procedure", "Route (one-shot"),
    ("execution contract", "knowledge/execution_contract.md"),
    ("root-cause gate", "Root-cause gate"),
    ("output contract", "Required output"),
]
# substring that must appear within the tail window (recency restatement)
TAIL_MARKER = ("output-contract restatement", "Re-state the")


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
    tlabel, tmarker = TAIL_MARKER
    if tmarker.encode() not in tail:
        errors.append(
            "MISSING tail restatement [%s]: %r not within last %d bytes"
            % (tlabel, tmarker, HEAD_BUDGET))

    print("%s: %d bytes (head budget %d, hard ceiling %d)"
          % (path, n, HEAD_BUDGET, HARD_CEILING))
    if errors:
        print("  FAIL — entrypoint kernel integrity:")
        for e in errors:
            print("    - " + e)
        return False
    print("  OK — kernel head-complete:")
    for label, _ in HEAD_MARKERS:
        print("    - %-20s byte %d" % (label, offsets[label]))
    print("    - tail restatement present within last %d bytes" % HEAD_BUDGET)
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
