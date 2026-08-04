#!/usr/bin/env python3
"""Probe 2: mixed-case router discovery, exact head-window cutoff, PreToolUse
deny, glob-trigger activation, plugin bundling, global-rule location."""
import json
import os
import shutil
import subprocess

HOME = os.path.expanduser("~")
PROBE = os.path.join(HOME, "tmp-agy-probe")
EXT_ABS = os.path.join(HOME, "tmp-agy-probe-ext-abs")

if os.path.isdir(PROBE):
    shutil.rmtree(PROBE)


def w(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if mode:
        os.chmod(path, mode)


# ---------- router case-sensitivity at repo root ----------
# Root deliberately has ONLY the mixed-case Agents.md plus GEMINI.md.
w(os.path.join(PROBE, "Agents.md"),
  "# Probe mixed-case root router\n\nMARKER_ROOT_MIXEDCASE is active.\n")
w(os.path.join(PROBE, "GEMINI.md"),
  "# Probe gemini root router\n\nMARKER_ROOT_GEMINI is active.\n")

# ---------- glob-trigger target ----------
w(os.path.join(PROBE, "code.cs"),
  "public class Probe\n{\n    // probe C# file for glob rule activation\n    void Run() { }\n}\n")

RULES = os.path.join(PROBE, ".agents", "rules")

w(os.path.join(RULES, "r_always.md"),
  "---\ntrigger: always_on\ndescription: Probe always-on rule\n---\n\nMARKER_RULE_ALWAYS is active.\n")

w(os.path.join(RULES, "r_glob.md"),
  "---\ntrigger: glob\nglobs: [\"**/*.cs\"]\ndescription: Probe glob rule for C# files\n---\n\n"
  "MARKER_RULE_GLOB is active.\n")

w(os.path.join(RULES, "r_glob_bare.md"),
  "---\ntrigger: glob\nglobs: \"*.cs\"\ndescription: Probe glob rule, bare-string globs form\n---\n\n"
  "MARKER_RULE_GLOB_BARE is active.\n")

w(os.path.join(RULES, "r_priority.md"),
  "---\ntrigger: always_on\npriority: 10\ndescription: Probe priority field acceptance\n---\n\n"
  "MARKER_RULE_PRIORITY is active.\n")

# ---------- 1KB-resolution ruler for the head-window cutoff ----------
KB = 1024
CHUNKS = 64
parts = ["---\ntrigger: always_on\ndescription: Probe ruler rule\n---\n"]
filler = ("Ruler filler text used to consume exactly one kilobyte per numbered marker "
          "so the injection cutoff can be measured to 1KB resolution. ")
for i in range(1, CHUNKS + 1):
    seg = f"\nMARKER_KB_{i:03d}\n"
    pad_len = KB - len(seg)
    pad = (filler * ((pad_len // len(filler)) + 1))[:pad_len]
    parts.append(seg + pad)
w(os.path.join(RULES, "ruler.md"), "".join(parts))

# ---------- plugin bundling test ----------
PLUG = os.path.join(PROBE, ".agents", "plugins", "probe-plugin")
w(os.path.join(PLUG, "plugin.json"), json.dumps({"name": "probe-plugin"}, indent=2) + "\n")
w(os.path.join(PLUG, "rules", "p_always.md"),
  "---\ntrigger: always_on\ndescription: Probe plugin always-on rule\n---\n\n"
  "MARKER_PLUGIN_RULE is active.\n")
w(os.path.join(PLUG, "skills", "probe-plugin-skill", "SKILL.md"),
  "---\nname: probe-plugin-skill\ndescription: >-\n"
  "  Use when the user asks to run the PLUGIN discovery probe.\n---\n\n"
  "MARKER_SKILL_PLUGIN is active.\n")

# ---------- skills: local + external absolute (the ~/ form failed in probe 1) ----------
w(os.path.join(PROBE, ".agents", "skills", "probe-local", "SKILL.md"),
  "---\nname: probe-local\ndescription: >-\n"
  "  Use when the user asks to run the LOCAL discovery probe.\n---\n\nMARKER_SKILL_LOCAL is active.\n")

w(os.path.join(PROBE, ".agents", "skills.json"), json.dumps({
    "entries": [
        {"path": os.path.join(EXT_ABS, "skills")},
        {"path": "~/tmp-agy-probe-ext-home/skills"},
    ]
}, indent=2) + "\n")

# ---------- hooks: PreToolUse deny of a specific command ----------
HOOKS = os.path.join(PROBE, ".agents", "hooks")
os.makedirs(os.path.join(PROBE, ".agents", ".state"), exist_ok=True)

w(os.path.join(HOOKS, "pre_invocation.sh"),
  '#!/bin/sh\n'
  'STATE="$(dirname "$0")/../.state"; mkdir -p "$STATE"\n'
  'P=$(cat); printf "PreInvocation %s\\n" "$P" >> "$STATE/hooks.log"\n'
  'printf %s \'{"injectSteps":[{"ephemeralMessage":"MARKER_HOOK_PREINVOCATION is active."}]}\'\n',
  0o755)

w(os.path.join(HOOKS, "pre_tool_use.sh"),
  '#!/bin/sh\n'
  'STATE="$(dirname "$0")/../.state"; mkdir -p "$STATE"\n'
  'P=$(cat); printf "PreToolUse %s\\n" "$P" >> "$STATE/hooks.log"\n'
  'case "$P" in\n'
  '  *FORBIDDEN_CMD*) printf %s \'{"decision":"deny","reason":"MARKER_HOOK_DENY: probe gate blocked this command."}\' ;;\n'
  '  *) printf %s \'{"decision":"allow"}\' ;;\n'
  'esac\n',
  0o755)

w(os.path.join(HOOKS, "stop.sh"),
  '#!/bin/sh\n'
  'STATE="$(dirname "$0")/../.state"; mkdir -p "$STATE"\n'
  'P=$(cat); printf "Stop %s\\n" "$P" >> "$STATE/hooks.log"\n'
  'printf %s \'{}\'\n',
  0o755)

w(os.path.join(PROBE, ".agents", "hooks.json"), json.dumps({
    "probe-pre-invocation": {"PreInvocation": [
        {"type": "command", "command": "./hooks/pre_invocation.sh", "timeout": 10}]},
    "probe-pre-tool": {"PreToolUse": [
        {"matcher": "*", "hooks": [
            {"type": "command", "command": "./hooks/pre_tool_use.sh", "timeout": 10}]}]},
    "probe-stop": {"Stop": [
        {"type": "command", "command": "./hooks/stop.sh", "timeout": 10}]},
}, indent=2) + "\n")

subprocess.run(["git", "init", "-q"], cwd=PROBE, check=False)

# ---------- global rule candidates in both plausible locations ----------
w(os.path.join(HOME, ".gemini", "rules", "zz_agy_probe_global.md"),
  "---\ntrigger: always_on\ndescription: Probe global rule in ~/.gemini/rules\n---\n\n"
  "MARKER_GLOBAL_RULES_DIR is active.\n")
w(os.path.join(HOME, ".gemini", "config", "rules", "zz_agy_probe_global.md"),
  "---\ntrigger: always_on\ndescription: Probe global rule in ~/.gemini/config/rules\n---\n\n"
  "MARKER_GLOBAL_CONFIG_RULES_DIR is active.\n")

print("probe2 ready. ruler.md size:", os.path.getsize(os.path.join(RULES, "ruler.md")))
