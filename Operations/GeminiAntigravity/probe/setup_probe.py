#!/usr/bin/env python3
"""Build the throwaway Antigravity discovery-probe workspace."""
import json
import os
import shutil
import subprocess

HOME = os.path.expanduser("~")
PROBE = os.path.join(HOME, "tmp-agy-probe")
EXT_ABS = os.path.join(HOME, "tmp-agy-probe-ext-abs")
EXT_HOME = os.path.join(HOME, "tmp-agy-probe-ext-home")

for d in (PROBE, EXT_ABS, EXT_HOME):
    if os.path.isdir(d):
        shutil.rmtree(d)


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------- hierarchical router discovery ----------
w(os.path.join(PROBE, "AGENTS.md"),
  "# Probe root router\n\nMARKER_AGENTS_UPPER_ROOT is active.\n")
w(os.path.join(PROBE, "sub", "Agents.md"),
  "# Probe mixed-case router\n\nMARKER_AGENTS_MIXED_SUB is active.\n")
w(os.path.join(PROBE, "sub2", "GEMINI.md"),
  "# Probe gemini router\n\nMARKER_GEMINI_SUB is active.\n")
w(os.path.join(PROBE, "sub", "note.txt"), "probe file in sub\n")
w(os.path.join(PROBE, "sub2", "note.txt"), "probe file in sub2\n")
w(os.path.join(PROBE, "code.cs"), "public class Probe { }\n")

# ---------- .agents/rules with each trigger type ----------
RULES = os.path.join(PROBE, ".agents", "rules")

w(os.path.join(RULES, "r_plain.md"),
  "# Plain rule, no frontmatter\n\nMARKER_RULE_PLAIN is active.\n")

w(os.path.join(RULES, "r_always.md"),
  "---\ntrigger: always_on\ndescription: Probe always-on rule\n---\n\n"
  "MARKER_RULE_ALWAYS is active.\n")

w(os.path.join(RULES, "r_decision.md"),
  "---\ntrigger: model_decision\ndescription: Probe rule that the model loads on demand when asked about probe decision rules\n---\n\n"
  "MARKER_RULE_DECISION is active.\n")

w(os.path.join(RULES, "r_glob.md"),
  "---\ntrigger: glob\nglobs: [\"**/*.cs\"]\ndescription: Probe glob rule for C# files\n---\n\n"
  "MARKER_RULE_GLOB is active.\n")

w(os.path.join(RULES, "r_manual.md"),
  "---\ntrigger: manual\ndescription: Probe manual rule\n---\n\n"
  "MARKER_RULE_MANUAL is active.\n")

# ---------- head-window / truncation probe ----------
# Each file: head marker, filler to target size, tail marker.
FILLER_LINE = ("Filler line for the Antigravity always-on rule size probe; "
               "this text exists only to consume bytes.\n")
for kb in (4, 16, 64):
    head = (f"---\ntrigger: always_on\ndescription: Probe size rule {kb}KB\n---\n\n"
            f"MARKER_HEAD_{kb:02d}K is active.\n\n")
    tail = f"\nMARKER_TAIL_{kb:02d}K is active.\n"
    target = kb * 1024
    body = ""
    while len(head) + len(body) + len(tail) < target:
        body += FILLER_LINE
    w(os.path.join(RULES, f"tail_{kb:02d}k.md"), head + body + tail)

# ---------- skills: local + external via skills.json ----------
def skill(root, name, marker, desc):
    w(os.path.join(root, name, "SKILL.md"),
      f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n"
      f"# {name}\n\n{marker} is active.\n")


skill(os.path.join(PROBE, ".agents", "skills"), "probe-local",
      "MARKER_SKILL_LOCAL",
      "Use when the user asks to run the LOCAL discovery probe in the probe workspace.")
skill(os.path.join(EXT_ABS, "skills"), "probe-abs",
      "MARKER_SKILL_ABS",
      "Use when the user asks to run the ABSOLUTE-PATH discovery probe registered via skills.json.")
skill(os.path.join(EXT_HOME, "skills"), "probe-home",
      "MARKER_SKILL_HOME",
      "Use when the user asks to run the HOME-RELATIVE discovery probe registered via skills.json.")

w(os.path.join(PROBE, ".agents", "skills.json"), json.dumps({
    "entries": [
        {"path": os.path.join(EXT_ABS, "skills")},
        {"path": "~/tmp-agy-probe-ext-home/skills"},
    ]
}, indent=2) + "\n")

# ---------- hooks ----------
HOOKS = os.path.join(PROBE, ".agents", "hooks")
STATE = os.path.join(PROBE, ".agents", ".state")
os.makedirs(STATE, exist_ok=True)

w(os.path.join(HOOKS, "pre_invocation.sh"), """#!/bin/sh
# Probe PreInvocation hook: log payload, inject an ephemeral marker.
STATE="$(dirname "$0")/../.state"
mkdir -p "$STATE"
PAYLOAD=$(cat)
printf '%s\\n' "PreInvocation $(date -u +%%H:%%M:%%S) $PAYLOAD" >> "$STATE/hooks.log"
printf '%s' '{"injectSteps":[{"ephemeralMessage":"MARKER_HOOK_PREINVOCATION is active."}]}'
""")

w(os.path.join(HOOKS, "pre_tool_use.sh"), """#!/bin/sh
STATE="$(dirname "$0")/../.state"
mkdir -p "$STATE"
PAYLOAD=$(cat)
printf '%s\\n' "PreToolUse $(date -u +%%H:%%M:%%S) $PAYLOAD" >> "$STATE/hooks.log"
printf '%s' '{"decision":"allow","reason":"probe hook allow"}'
""")

w(os.path.join(HOOKS, "post_tool_use.sh"), """#!/bin/sh
STATE="$(dirname "$0")/../.state"
mkdir -p "$STATE"
PAYLOAD=$(cat)
printf '%s\\n' "PostToolUse $(date -u +%%H:%%M:%%S) $PAYLOAD" >> "$STATE/hooks.log"
printf '%s' '{}'
""")

# Stop hook: continue exactly once (counter-guarded), then allow stop.
w(os.path.join(HOOKS, "stop.sh"), """#!/bin/sh
STATE="$(dirname "$0")/../.state"
mkdir -p "$STATE"
PAYLOAD=$(cat)
printf '%s\\n' "Stop $(date -u +%%H:%%M:%%S) $PAYLOAD" >> "$STATE/hooks.log"
GUARD="$STATE/stop_continued"
if [ -f "$GUARD" ]; then
  printf '%s' '{}'
else
  : > "$GUARD"
  printf '%s' '{"decision":"continue","reason":"MARKER_HOOK_STOP_CONTINUE: probe stop-hook blocked termination once."}'
fi
""")

w(os.path.join(HOOKS, "post_invocation.sh"), """#!/bin/sh
STATE="$(dirname "$0")/../.state"
mkdir -p "$STATE"
PAYLOAD=$(cat)
printf '%s\\n' "PostInvocation $(date -u +%%H:%%M:%%S) $PAYLOAD" >> "$STATE/hooks.log"
printf '%s' '{}'
""")

for name in os.listdir(HOOKS):
    os.chmod(os.path.join(HOOKS, name), 0o755)

w(os.path.join(PROBE, ".agents", "hooks.json"), json.dumps({
    "probe-pre-invocation": {"PreInvocation": [
        {"type": "command", "command": "./hooks/pre_invocation.sh", "timeout": 10}]},
    "probe-post-invocation": {"PostInvocation": [
        {"type": "command", "command": "./hooks/post_invocation.sh", "timeout": 10}]},
    "probe-pre-tool": {"PreToolUse": [
        {"matcher": "*", "hooks": [
            {"type": "command", "command": "./hooks/pre_tool_use.sh", "timeout": 10}]}]},
    "probe-post-tool": {"PostToolUse": [
        {"matcher": "*", "hooks": [
            {"type": "command", "command": "./hooks/post_tool_use.sh", "timeout": 10}]}]},
    "probe-stop": {"Stop": [
        {"type": "command", "command": "./hooks/stop.sh", "timeout": 10}]},
}, indent=2) + "\n")

# ---------- git init ----------
subprocess.run(["git", "init", "-q"], cwd=PROBE, check=False)

print("probe workspace ready:", PROBE)
for root, dirs, files in os.walk(PROBE):
    if ".git" in root:
        continue
    dirs[:] = [d for d in dirs if d != ".git"]
    for f in sorted(files):
        p = os.path.join(root, f)
        print(f"  {os.path.relpath(p, PROBE):45s} {os.path.getsize(p):>7d} bytes")
print("external:", EXT_ABS, EXT_HOME)
