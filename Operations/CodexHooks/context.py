#!/usr/bin/env python3
"""Read-only Codex context reminders. No transcript access or approval decisions."""

import json
from pathlib import Path
import re
import shlex
import sys


def _read_only_command(words):
    if not words:
        return False
    if words[0] in {"cat", "head", "tail", "wc", "pwd"}:
        return True
    if words[0] == "rg":
        return not any(word.startswith(("--pre", "--hostname-bin")) for word in words[1:])
    if words[0] == "sed":
        return (
            len(words) >= 3 and words[1] == "-n"
            and re.fullmatch(r"[0-9]+(?:,[0-9]+)?p", words[2]) is not None
            and not any(word.startswith("-") for word in words[3:])
        )
    if words[0] == "git":
        return (
            len(words) >= 2
            and words[1] in {"status", "diff", "log", "show", "ls-files", "rev-parse"}
            and not any(word.startswith(("--out", "--ext", "--textconv")) for word in words[2:])
        )
    return False


def _read_only_shell(command):
    if not isinstance(command, str) or any(char in command for char in "<>$`\n\r"):
        return False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|;&()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        words = list(lexer)
    except ValueError:
        return False
    segment = []
    for word in words:
        if word in {"|", ";", "&&"}:
            if not _read_only_command(segment):
                return False
            segment = []
        elif any(char in word for char in "|;&()"):
            return False
        else:
            segment.append(word)
    return _read_only_command(segment)


def context(event, public_root):
    name = event.get("hook_event_name")
    if name not in {"SessionStart", "SubagentStart", "UserPromptSubmit", "PreToolUse"}:
        return {}
    tool_input = event.get("tool_input")
    if name == "PreToolUse" and event.get("tool_name") in {"Bash", "exec_command"} and isinstance(tool_input, dict):
        if _read_only_shell(tool_input.get("command", tool_input.get("cmd"))):
            return {}
    host = public_root.parent
    mounted = (host / "AGENTS.md").is_file() and (
        host / public_root.name
    ).resolve() == public_root
    router = host / "AGENTS.md" if mounted else public_root / "AGENTS.md"
    core = public_root / "Modules/XUUnity"
    if name == "PreToolUse":
        message = (
            "Before any mutation in this edit batch, apply the active router and "
            "finish the task's pre-edit gate. For Unity work, emit the evidence-based "
            "Pre-edit check and Derived execution contract from "
            f"{core / 'tasks/start_session.md'}. Name files actually read, existing "
            "implementation findings, matched overrides, thread/concurrency evidence "
            "or not_applicable, and representative validation. Read-only discovery "
            "may proceed. This reminder is not proof the gate was satisfied."
        )
    else:
        message = (
            f"Automatic project routing: load {router} first line through EOF "
            "unless its full current contents are already in context. Apply it to "
            "the current request and follow-ups without waiting for a protocol prefix. "
            "Resolve the target from referenced files and task context; load the "
            "target's AGENTS.md, required project memory, and matching overrides. "
            f"For work inside {public_root}, also load {public_root / 'AGENTS.md'}. "
            "For Unity implementation, reviews, architecture, SDK/native work, and "
            "prefab or copy edits, load "
            f"{core / 'tasks/start_session.md'} first line through EOF and assemble "
            "only the matched stack. Follow the host overlay route when present. "
            "For protocol/tooling work, load the relevant module/operation router "
            f"under {public_root}; unrelated requests do not need Unity packs. "
            "Before Unity edits, emit Pre-edit check and Derived execution contract "
            f"using {core / 'knowledge/execution_contract.md'} and its validation "
            "owner. Derive claims from current evidence, never from a previous "
            "example. On resume or compaction, restore any missing route and gate "
            "before editing. This hook supplies routing context, not file-read or "
            "validation evidence."
        )
    return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": message}}


def main():
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("expected an object")
    except (ValueError, UnicodeError):
        print(json.dumps({"systemMessage": "Routing hook received invalid event JSON; use AGENTS.md."}))
        return
    print(json.dumps(context(event, Path(__file__).resolve().parents[2])))


if __name__ == "__main__":
    main()
