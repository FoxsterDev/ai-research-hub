#!/usr/bin/env python3
"""Check that files destined for a public location carry no private tokens.

The patterns are the private part, so they are never hardcoded here — supply them in a
JSON file that stays on the private side:

    {
      "forbidden": {
        "internal project name": ["\\\\bProjectAlpha\\\\b", "\\\\bProjectBeta\\\\b"],
        "machine path":          ["/Users/[a-z]+/", "\\\\bmyusername\\\\b"],
        "private protocol":      ["\\\\bmyprotocol\\\\b"]
      },
      "allow": ["tmp-probe-scratch"]
    }

`forbidden` maps a human-readable kind to a list of Python regexes. `allow` is a list of
regexes; any line matching one is exempt, for the cases where a hit is genuinely a synthetic
example rather than a leak.

    leakcheck.py --patterns private/leak_patterns.json PATH [PATH ...]

PATH may be a file or a directory. Exit 0 when clean, 1 on any finding.
"""
import argparse
import json
import os
import re
import sys

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".pb", ".db", ".pyc"}


def walk(target):
    """Yield (path, display) for a file, or for every file under a directory.

    os.walk() on a file yields nothing, so a plain walk would report a single file as clean
    no matter what it contains. Handle both shapes explicitly.
    """
    if os.path.isfile(target):
        yield target, os.path.basename(target)
        return
    if not os.path.isdir(target):
        sys.exit(f"leakcheck: no such file or directory: {target}")
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            p = os.path.join(dirpath, fn)
            yield p, os.path.relpath(p, target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns", required=True, help="JSON file of forbidden/allow patterns")
    ap.add_argument("paths", nargs="+")
    args = ap.parse_args()

    try:
        cfg = json.load(open(args.patterns, encoding="utf-8"))
    except Exception as e:
        sys.exit(f"leakcheck: cannot read --patterns {args.patterns}: {e}")

    forbidden = {kind: [re.compile(p) for p in pats]
                 for kind, pats in (cfg.get("forbidden") or {}).items()}
    if not forbidden:
        sys.exit(f"leakcheck: {args.patterns} defines no 'forbidden' patterns — nothing to check")
    allow = [re.compile(p) for p in (cfg.get("allow") or [])]

    findings = []
    scanned = 0
    for target in args.paths:
        for path, display in walk(target):
            try:
                lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            scanned += 1
            for lineno, line in enumerate(lines, 1):
                if any(a.search(line) for a in allow):
                    continue
                for kind, rxs in forbidden.items():
                    for rx in rxs:
                        m = rx.search(line)
                        if m:
                            findings.append((target, display, lineno, kind,
                                             m.group(0), line.strip()[:110]))

    if not findings:
        print(f"leakcheck CLEAN: {scanned} file(s) across {len(args.paths)} path(s)")
        return 0

    print(f"leakcheck found {len(findings)} issue(s) in {scanned} file(s):\n")
    for target, display, lineno, kind, token, ctx in findings:
        print(f"  {display}:{lineno}  [{kind}] '{token}'")
        print(f"      {ctx}")
    print("\nRedact, generalize, or add a narrow 'allow' pattern — do not widen 'forbidden'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
