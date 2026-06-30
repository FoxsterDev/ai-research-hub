# XUUnity AI CLI Orchestrator

`XUUnityAiCliOrchestrator` lets XUUnity use external AI CLI tools through
official account login or OAuth, with subscription quota as the default cost
surface.

The orchestrator is intentionally task-neutral. A task opts in with prompt
metadata such as `external_ai: allowed`; the runner then chooses the best ready
configured provider and model.

## Delegation Model

The orchestrator exists to move the expensive, noisy part of a concrete task to
an external subscription-backed AI worker.

For `via claude` and equivalent external AI routes:

- The XUUnity host agent owns task classification, provider selection, proof gates,
  safety policy, and final relay to the user.
- The external worker owns task execution, evidence collection, artifact/log
  reading, first-pass interpretation, and a compact worker report.
- The XUUnity host agent inspects artifacts directly only when the worker fails,
  returns an invalid or inconclusive report, or the user asks for independent
  verification.
- A green command result is evidence, not automatic acceptance. If the worker
  report creates doubt, the XUUnity host agent may verify, challenge, or
  continue locally.

## Priority

```text
subscription account quota first
API billing later / optional / explicitly enabled
```

Initial adapters:

```text
Claude CLI       official Claude login/OAuth, Pro/Team limits
Gemini CLI       official Google login, Pro/Code Assist limits
Antigravity      official Google account login, Antigravity limits
Metered API      future extension point, disabled by default
```

## Install

From the AIRoot repo:

```sh
bash Operations/XUUnityAiCliOrchestrator/init_xuunity_ai_cli_orchestrator.sh
```

This creates a user-local config when missing:

```text
~/.xuunity/ai-cli-orchestrator/config.json
```

It does not write OAuth tokens or account state into this repo.

## Commands

```sh
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh doctor
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh providers
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh run \
  --project-root /absolute/project \
  --prompt-file /absolute/task.md
```

Use JSON output for automation:

```sh
bash Operations/XUUnityAiCliOrchestrator/xuunity_ai_cli_orchestrator.sh doctor --json
```

## Prompt Opt-In

Recommended XUUnity command form:

```text
xuunity fix the bug via claude
xuunity review the git change via claude
xuunity architecture plan this subsystem via claude
```

Provider selector phrases such as `via claude`, `with claude`, `use claude`,
`through claude`, and `через claude` select the `claude_cli` adapter.

Scalar form:

```yaml
external_ai: allowed
```

Block form:

```yaml
external_ai:
  provider: claude_cli
  model: best_available
  authPolicy: official_login_only
  apiBilling: forbidden
  web: forbidden
  writes: forbidden
```

If no external AI provider is ready, the runner reports
`external_ai_status: unavailable`. XUUnity can then continue locally.

## Worker Report

External workers should return one final report with these fields or clear
equivalents:

```json
{
  "worker_status": "completed|failed|blocked|inconclusive",
  "task_status": "passed|failed|changed|unchanged|unavailable",
  "actions_taken": [],
  "evidence": [],
  "artifacts": [],
  "workspace_side_effects": {},
  "interpretation": "",
  "doubts_or_escalation": []
}
```

The worker should do routine evidence collection itself: read generated result
files, inspect relevant log tails, and compress the finding into decision-grade
evidence. The caller should not need to rediscover basic artifacts after a
successful worker run.

## Safety Defaults

- External AI is opt-in per task.
- Default project access is read-only.
- Web access is separate from project read access.
- Write access requires both task opt-in and config opt-in, plus the run flag
  `--allow-writes`.
- Claude, Gemini, and Antigravity adapters reject API-key fallback for normal
  subscription-backed use.
- Metered API providers are disabled by default and require explicit future
  opt-in plus budget controls.
