# XUUnity Utility: AI CLI Orchestrator

## Goal
Route an already-classified XUUnity task through an external AI CLI provider
when the user explicitly asks for that provider.

Canonical selector:

```text
xuunity <task> via claude
```

Examples:

```text
xuunity fix the bug via claude
xuunity review the git change via claude
xuunity architecture plan this subsystem via claude
```

## Rules
- Do not make `via claude` a separate task family.
- First classify the normal XUUnity task exactly as if the selector were absent.
- Add provider selector `claude_cli`.
- Use `AIRoot/Operations/XUUnityAiCliOrchestrator/` as the execution surface.
- Use official account login or OAuth only.
- Do not allow API-key fallback for subscription providers.
- Delegate the expensive concrete work to the external worker: execution,
  evidence collection, artifact/log reading, first-pass interpretation, and a
  compact worker report.
- Keep the XUUnity host agent focused on routing, proof gates, safety policy,
  final relay, and follow-up verification when the worker report is failed,
  invalid, suspicious, or user-challenged.
- If the provider is unavailable, unauthenticated, or fails the proof gate,
  continue locally and report the external-provider gap.

## Prompt Shape
When a concrete prompt file is needed for the orchestrator, include either the
natural selector:

```text
xuunity review the git change via claude
```

or the explicit marker:

```yaml
external_ai:
  provider: claude_cli
  model: best_available
  apiBilling: forbidden
```

## Proof Gate
The provider is selectable only after these are proven:

- official subscription login
- subscription quota billing surface
- adapter-enforced access policy
- resolved model

For Claude CLI, proof comes from the orchestrator's `doctor` command and the
Claude adapter.

## Worker Report
The external worker should return one compact report with:

- `worker_status`
- `task_status`
- `actions_taken`
- `evidence`
- `artifacts`
- `workspace_side_effects`
- `interpretation`
- `doubts_or_escalation`

If this report is complete and plausible, relay it. Re-read raw artifacts only
when the report is incomplete, contradictory, or worth challenging.
