# Codex automatic routing hooks

The repository routers apply to natural-language tasks without a protocol prefix.
The hooks reinforce that contract at SessionStart (including resume/compaction),
UserPromptSubmit, SubagentStart, and PreToolUse. The pre-tool reminder covers shell,
patch, and MCP calls; read-only discovery does not require an edit gate.

`context.py` uses only Python's standard library, reads the event from stdin,
and returns Codex `additionalContext` JSON. It does not read transcripts, retain
prompts, write state, use the network, grant permissions, or block tools. It points
to canonical instructions instead of copying protocol bodies or freezing the
execution-contract field set. The agent must actually read and apply those files.
These are context guardrails, not proof or hard enforcement of agent compliance.

## Installation and activation

- Public checkout: `.codex/hooks.json` at the repository root.
- Mounted checkout: the host may also register `.codex/hooks.json` pointing to
  this operation. Commands walk ancestors from the session directory, so nested
  directories, submodules, spaces, and Git worktrees do not depend on a fixed
  machine path. A host checkout needs its public submodule initialized.
- Codex must trust the project configuration layer. Review and trust the new
  hook definitions through Codex's `/hooks` UI (CLI), then start/resume a task.
  Hook trust is bound to the definition hash; changed definitions require review.
  Do not manually fabricate trust hashes or bypass the review.
- Hooks are enabled by default in the documented runtime. If disabled by local
  or managed configuration, the repository's AGENTS.md still supplies routing.
- When both host and public config layers load, Codex runs both hooks. Repeated
  reminders are harmless and intentionally stateless; do not infer that the host
  hook ran merely because its file exists.

## Validation

Run `python3 Operations/CodexHooks/test_context.py` from the public root.
Tests exercise the real configured shell command from root/nested directories,
mounted and standalone layouts (including spaces), event JSON, and bounded output.
They do not prove a live session has trusted and invoked the hooks.

After trust, start a fresh task with an ordinary Unity edit request. Before the
first edit, expect the agent to load the resolved project router and selected
protocol, then show `Pre-edit check` and `Derived execution contract` based on
actual reads. An unrelated question should not load the Unity runtime stack.

Sources: [Codex hooks](https://learn.chatgpt.com/docs/hooks) and
[AGENTS.md discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
