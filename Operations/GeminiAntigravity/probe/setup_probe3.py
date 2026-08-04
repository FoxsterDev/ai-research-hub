#!/usr/bin/env python3
"""Probe 3: glob syntax/semantics disambiguation, no-frontmatter rule, and
model_decision on-demand activation."""
import json
import os
import shutil
import subprocess

HOME = os.path.expanduser("~")
PROBE = os.path.join(HOME, "tmp-agy-probe")
if os.path.isdir(PROBE):
    shutil.rmtree(PROBE)


def w(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if mode:
        os.chmod(path, mode)


w(os.path.join(PROBE, "Agents.md"), "# Probe root\n\nMARKER_ROOT_MIXEDCASE is active.\n")
w(os.path.join(PROBE, "root.cs"), "public class Root { }\n")
w(os.path.join(PROBE, "deep", "nested", "Deep.cs"), "public class Deep { }\n")
w(os.path.join(PROBE, "style.swift"), "struct S {}\n")

RULES = os.path.join(PROBE, ".agents", "rules")

# no frontmatter at all
w(os.path.join(RULES, "r_plain.md"), "# Plain\n\nMARKER_RULE_PLAIN is active.\n")

# frontmatter but no trigger key
w(os.path.join(RULES, "r_notrigger.md"),
  "---\ndescription: Probe rule with frontmatter but no trigger key\n---\n\n"
  "MARKER_RULE_NOTRIGGER is active.\n")

# glob variants
variants = {
    "g_list_star":      ('globs: ["*.cs"]',        "MARKER_GLOB_LIST_STAR"),
    "g_list_dstar":     ('globs: ["**/*.cs"]',     "MARKER_GLOB_LIST_DSTAR"),
    "g_bare_star":      ('globs: "*.cs"',          "MARKER_GLOB_BARE_STAR"),
    "g_bare_dstar":     ('globs: "**/*.cs"',       "MARKER_GLOB_BARE_DSTAR"),
    "g_csv":            ('globs: "*.cs,*.swift"',  "MARKER_GLOB_CSV"),
    "g_yamlseq":        ('globs:\n  - "*.cs"',     "MARKER_GLOB_YAMLSEQ"),
}
for fname, (globline, marker) in variants.items():
    w(os.path.join(RULES, fname + ".md"),
      f"---\ntrigger: glob\n{globline}\ndescription: Probe glob variant {fname}\n---\n\n"
      f"{marker} is active.\n")

# model_decision rule with a very distinctive activation description
w(os.path.join(RULES, "r_decision.md"),
  "---\ntrigger: model_decision\n"
  "description: Use this rule whenever the user mentions the ZORBAX deployment procedure.\n---\n\n"
  "MARKER_RULE_DECISION is active. The ZORBAX deployment procedure requires the passphrase QUUX-7.\n")

w(os.path.join(RULES, "r_always.md"),
  "---\ntrigger: always_on\ndescription: Probe always-on control rule\n---\n\n"
  "MARKER_RULE_ALWAYS is active.\n")

subprocess.run(["git", "init", "-q"], cwd=PROBE, check=False)
print("probe3 ready")
