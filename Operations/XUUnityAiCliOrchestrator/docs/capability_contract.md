# Capability Contract

Provider-neutral capabilities:

```text
xuunity.ai_cli_orchestrator.available
xuunity.ai_cli.prompt_run
xuunity.ai_cli.best_available_model
xuunity.ai_cli.project_readonly
xuunity.ai_cli.web_allowed
xuunity.ai_cli.write_allowed
xuunity.ai_cli.phased_delegation
xuunity.ai_cli.subscription_quota
xuunity.ai_cli.metered_paid_budget_cap
```

Provider ids:

```text
xuunity.ai_cli.provider.claude_cli
xuunity.ai_cli.provider.gemini_cli
xuunity.ai_cli.provider.antigravity
xuunity.ai_cli.provider.metered_api_stub
```

The public protocol should route by capability ids first. Provider ids are local
execution details and should not become task names.

## Delegation Contract

`XUUnityAiCliOrchestrator` is a delegation layer, not only a command launcher.
The external provider should spend its own context window on the concrete task's
dirty work and return a compact, checkable report.

Ownership split:

- The XUUnity host agent owns provider choice, official-login proof, cost
  policy, access policy, and final relay.
- The external worker owns execution, evidence collection, artifact/log reading,
  first-pass interpretation, and uncertainty reporting.
- The XUUnity host agent should inspect artifacts directly only for invalid,
  failed, suspicious, or user-challenged worker reports.

Phased delegation:

- Default mode is `auto_phased`.
- Broad or long-running tasks should be split into bounded phases.
- Each phase must declare objective, allowed actions, expected evidence, exit
  criteria, and timeout budget.
- The host agent should be able to stop after any phase without losing the
  useful evidence already gathered.
- Future multi-run schedulers should use the same phase fields instead of a
  second protocol.

The worker report should include:

```text
worker_status
task_status
phase_plan
phase_results
actions_taken
evidence
artifacts
workspace_side_effects
interpretation
doubts_or_escalation
```

## XUUnity Selector

The canonical user-facing selector is:

```text
xuunity <task> via claude
```

This maps to:

```text
external_ai: allowed
provider: claude_cli
```

## Proof Gate

A provider is selectable only after it reports the proof fields required for the
current run:

```text
auth_proof: official_subscription_login
billing_proof: subscription_quota | subscription_or_account_quota
access_proof: adapter-enforced read/write policy
model_proof: resolved_model
```

`ready` without these proofs is not enough.
