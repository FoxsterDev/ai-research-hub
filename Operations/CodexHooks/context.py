#!/usr/bin/env python3
"""Read-only Codex context reminders. No transcript access or approval decisions."""

import json
from pathlib import Path
import sys


def context(event, public_root):
    name = event.get("hook_event_name")
    if name not in {"SessionStart", "SubagentStart", "UserPromptSubmit", "PreToolUse"}:
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
