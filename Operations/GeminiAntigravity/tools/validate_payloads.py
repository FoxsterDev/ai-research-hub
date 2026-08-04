#!/usr/bin/env python3
"""Validate Antigravity / Gemini customization payloads before installing them.

Checks the things this platform fails at silently (see docs/PLATFORM_CONTRACT.md):

  1. every rule file has frontmatter with a `trigger:` key — without it the file is
     discovered and then ignored, with no warning anywhere;
  2. `globs:` is a comma-separated STRING — YAML list and sequence forms never fire;
  3. every SKILL.md has `name` + `description`, and `name` matches its directory;
  4. no single always-on file exceeds the measured ~24 KB injection cutoff, and no
     always-on set exceeds its total budget — nothing in the platform sums a directory;
  5. every corpus path a rule or skill points at actually exists;
  6. skills.json entries are absolute (`~/` does not resolve), exist, hold skill dirs,
     and carry no duplicate skill names (the loader dedupes by name);
  7. no literal secret pattern anywhere in the payloads.

Usage:
  validate_payloads.py --global-rules DIR
                       [--workspace LABEL:PAYLOAD_DIR:REPO_ROOT ...]
                       [--global-budget BYTES] [--workspace-budget BYTES]
                       [--secret-scan DIR] [--json]

PAYLOAD_DIR is the directory holding `rules/`, `skills/`, `skills.json`.
REPO_ROOT is the repository the payload's relative corpus references resolve against.

Exit 0 if clean, 1 on any error.
"""
import argparse
import json
import os
import re
import sys

PER_FILE_CUTOFF = 24 * 1024
VALID_TRIGGERS = {"always_on", "glob", "manual", "model_decision"}

SECRET_PATTERNS = [
    (re.compile(r"(?i)\b(api[_-]?key|secret|passwd|password|client[_-]secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9/_\-+]{12,}"), "key=value"),
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}"), "google api key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "github token"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "slack token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\."), "jwt"),
]

# A corpus reference is a backticked repo-relative path with a directory separator.
CORPUS_REF = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_.<>-]*(?:/[A-Za-z0-9_.<>-]+)+)`")

errors, warnings, notes = [], [], []


def frontmatter(path):
    """Return (dict, body); dict is None when there is no frontmatter block."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    raw, body = text[4:end + 1], text[end + 5:]
    fm, key = {}, None
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2)
        elif key is not None:
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, body


def check_refs(where, text, repo_root):
    if not repo_root:
        return
    for ref in sorted(set(CORPUS_REF.findall(text))):
        if "<" in ref or ref.startswith("~") or ref.startswith("/"):
            continue          # templated, home-relative or absolute: not ours to resolve
        if not os.path.exists(os.path.join(repo_root, ref)):
            errors.append(f"[{where}] references a path that does not exist: {ref}")


def check_rules(label, rules_dir, budget, repo_root=None, require_always_on=False):
    if not os.path.isdir(rules_dir):
        errors.append(f"[{label}] rules dir missing: {rules_dir}")
        return
    files = sorted(f for f in os.listdir(rules_dir) if f.endswith(".md"))
    if not files:
        errors.append(f"[{label}] no rule files in {rules_dir}")
    always_total = 0
    for fn in files:
        p = os.path.join(rules_dir, fn)
        size = os.path.getsize(p)
        fm, body = frontmatter(p)
        if fm is None:
            errors.append(f"[{label}] {fn}: NO frontmatter — discovered and then ignored")
            continue
        trig = (fm.get("trigger") or "").strip()
        if not trig:
            errors.append(f"[{label}] {fn}: frontmatter has no `trigger:` key — silently ignored")
        elif trig not in VALID_TRIGGERS:
            errors.append(f"[{label}] {fn}: trigger '{trig}' not in {sorted(VALID_TRIGGERS)}")
        elif require_always_on and trig != "always_on":
            warnings.append(f"[{label}] {fn}: global-layer files should be always_on (found '{trig}')")
        # A frontmatter value containing ": " must be quoted or the YAML is invalid and the
        # whole rule is silently dropped. This exact defect killed a policy pack in production
        # and was invisible until the model was asked to list its active rules.
        for key in ("description", "globs", "trigger"):
            raw_line = next((l for l in open(p, encoding="utf-8").read().splitlines()
                             if l.startswith(key + ":")), None)
            if raw_line:
                val = raw_line[len(key) + 1:].strip()
                if val and val[0] not in "\"'>|[" and ": " in val:
                    errors.append(f"[{label}] {fn}: `{key}:` value contains ': ' but is "
                                  f"unquoted — invalid YAML, the rule is silently dropped. "
                                  f"Wrap the value in double quotes.")
        if not (fm.get("description") or "").strip():
            warnings.append(f"[{label}] {fn}: no description — needed for model_decision routing")
        if trig == "glob":
            g = (fm.get("globs") or "").strip()
            if not g:
                errors.append(f"[{label}] {fn}: trigger is glob but no `globs:` value")
            elif g.startswith("[") or g.startswith("-"):
                errors.append(f"[{label}] {fn}: `globs: {g}` is a YAML list — never fires; "
                              f"use a comma-separated string")
            elif not (g.startswith('"') or g.startswith("'")):
                warnings.append(f"[{label}] {fn}: quote the globs value (globs: \"*.ext\")")
        if size > PER_FILE_CUTOFF:
            errors.append(f"[{label}] {fn}: {size} bytes exceeds the measured "
                          f"{PER_FILE_CUTOFF}-byte injection cutoff")
        if trig == "always_on":
            always_total += size
        check_refs(f"{label}/rules/{fn}", body, repo_root)
    if always_total > budget:
        errors.append(f"[{label}] always-on total {always_total} bytes exceeds budget {budget}")
    else:
        notes.append(f"[{label}] always-on total {always_total}/{budget} bytes")


def check_skills(label, skills_dir, repo_root=None):
    if not os.path.isdir(skills_dir):
        notes.append(f"[{label}] no local skills dir")
        return
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if not os.path.isdir(d):
            continue
        p = os.path.join(d, "SKILL.md")
        if not os.path.isfile(p):
            errors.append(f"[{label}] skill '{name}' has no SKILL.md")
            continue
        fm, body = frontmatter(p)
        if fm is None:
            errors.append(f"[{label}] skill '{name}': no frontmatter")
            continue
        if fm.get("name", "").strip() != name:
            errors.append(f"[{label}] skill '{name}': frontmatter name "
                          f"'{fm.get('name')}' != directory name")
        desc = (fm.get("description") or "").strip().lstrip(">-").strip()
        if len(desc) < 40:
            errors.append(f"[{label}] skill '{name}': description too thin to route on "
                          f"({len(desc)} chars)")
        elif not re.search(r"(?i)\b(use|fires|run)\b", desc):
            warnings.append(f"[{label}] skill '{name}': description states capability "
                            f"but no activation trigger")
        check_refs(f"{label}/skills/{name}", body, repo_root)


def check_skills_json(label, path):
    if not os.path.isfile(path):
        notes.append(f"[{label}] no skills.json")
        return
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        errors.append(f"[{label}] skills.json is not valid JSON: {e}")
        return
    seen = {}
    for entry in cfg.get("entries", []):
        p = entry.get("path", "")
        if p.startswith("~"):
            errors.append(f"[{label}] skills.json entry '{p}' uses ~/ — does not resolve; "
                          f"use an absolute path")
            continue
        if not p.startswith("/"):
            warnings.append(f"[{label}] skills.json entry '{p}' is workspace-relative — "
                            f"documented but unverified")
            continue
        if not os.path.isdir(p):
            errors.append(f"[{label}] skills.json entry does not exist: {p}")
            continue
        found = [d for d in os.listdir(p) if os.path.isfile(os.path.join(p, d, "SKILL.md"))]
        if not found:
            errors.append(f"[{label}] skills.json entry has no <dir>/SKILL.md children: {p}")
        for d in found:
            fm, _ = frontmatter(os.path.join(p, d, "SKILL.md"))
            nm = (fm or {}).get("name", d).strip()
            if nm in seen:
                errors.append(f"[{label}] duplicate skill name '{nm}': {seen[nm]} and {p}/{d} "
                              f"— the loader dedupes by name")
            else:
                seen[nm] = f"{p}/{d}"
    notes.append(f"[{label}] skills.json registers {len(seen)} uniquely-named skills")


def check_secrets(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".state")]
        for fn in filenames:
            if fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".pb", ".db", ".tar", ".gz")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for rx, kind in SECRET_PATTERNS:
                m = rx.search(text)
                if m:
                    errors.append(f"[secrets] possible {kind} in {os.path.relpath(p, base)}: "
                                  f"{m.group(0)[:20]}… — redact as [REDACTED]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--global-rules")
    ap.add_argument("--workspace", action="append", default=[],
                    metavar="LABEL:PAYLOAD_DIR:REPO_ROOT")
    # Defaults derived from measurement, not inherited from another harness. The
    # per-file cutoff is where injection actually truncates (probed to 1KB resolution);
    # these budgets sit at half of it. An always-on set of ~84KB triggered turn-1 context
    # truncation and ~35KB did not, and nothing between 12KB and 84KB has been measured,
    # so 12KB per layer stays far from the cliff without squeezing load-bearing lines to
    # hit a number. Raise them with a measurement, not a hunch.
    ap.add_argument("--global-budget", type=int, default=12 * 1024)
    ap.add_argument("--workspace-budget", type=int, default=12 * 1024)
    ap.add_argument("--secret-scan", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.global_rules:
        check_rules("global", a.global_rules, a.global_budget, require_always_on=True)

    for spec in a.workspace:
        parts = spec.split(":")
        if len(parts) < 2:
            errors.append(f"bad --workspace spec (need LABEL:PAYLOAD_DIR[:REPO_ROOT]): {spec}")
            continue
        label, payload = parts[0], parts[1]
        repo_root = parts[2] if len(parts) > 2 else None
        check_rules(label, os.path.join(payload, "rules"), a.workspace_budget, repo_root)
        check_skills(label, os.path.join(payload, "skills"), repo_root)
        check_skills_json(label, os.path.join(payload, "skills.json"))

    for d in a.secret_scan:
        check_secrets(d)

    if a.json:
        print(json.dumps({"errors": errors, "warnings": warnings, "notes": notes}, indent=2))
    else:
        for n in notes:
            print("note   ", n)
        for w in warnings:
            print("warn   ", w)
        for e in errors:
            print("ERROR  ", e)
        print()
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
