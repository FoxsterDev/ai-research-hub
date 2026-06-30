# XUUnity Protocol

Canonical task shape:

```text
xuunity <normal task> via claude
```

Examples:

```text
xuunity fix the bug via claude
xuunity review the git change via claude
xuunity architecture plan this subsystem via claude
xuunity product impact this change via claude
```

Meaning:

- Load the normal XUUnity task stack first.
- Treat `via claude` as an external AI provider selector.
- Use `XUUnityAiCliOrchestrator` with provider `claude_cli`.
- Keep the run subscription-first and official-login-only.
- If Claude is unavailable or does not pass the proof gate, continue locally and
  report the provider gap.

Execution boundary:

- The XUUnity host agent owns routing: classify the normal task, select the
  provider, enforce auth/cost/access policy, and relay the final answer.
- Claude owns the delegated work: execute the bounded task, gather evidence,
  read generated artifacts or log tails, interpret the result, and return a
  compact worker report.
- The XUUnity host agent should not redo routine evidence collection after a
  successful worker report. It should verify only when the worker failed,
  returned an invalid or inconclusive report, produced suspicious evidence, or
  the user asks for independent confirmation.

Phased execution:

- Use `auto_phased` by default for broad, risky, or long-running tasks.
- The worker should create a small phase plan before deep execution.
- Each phase needs an objective, allowed actions, expected evidence, exit
  criteria, and timeout budget.
- The worker should report phase results as it completes them and stop when the
  goal is reached, policy would be exceeded, or evidence becomes inconclusive.
- Use `single_run` only for already-small tasks.
- Use `phase_plan_only` when the host agent wants a plan before spending quota
  on execution.

Expected worker report shape:

```json
{
  "worker_status": "completed|failed|blocked|inconclusive",
  "task_status": "passed|failed|changed|unchanged|unavailable",
  "phase_plan": [],
  "phase_results": [],
  "actions_taken": [],
  "evidence": [],
  "artifacts": [],
  "workspace_side_effects": {},
  "interpretation": "",
  "doubts_or_escalation": []
}
```

Supported selector aliases:

```text
via claude
with claude
use claude
through claude
using claude
через claude
с claude
```

Do not use a bare mention of `Claude` as the canonical selector when the task is
about Claude implementation itself. Use `via claude` when the word is intended
as an execution route.
