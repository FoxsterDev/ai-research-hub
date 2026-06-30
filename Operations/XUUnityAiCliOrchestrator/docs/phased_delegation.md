# Phased Delegation

External AI workers should receive work in bounded chunks when the task is
broad, risky, or likely to run long.

## Modes

```text
auto_phased
single_run
phase_plan_only
```

- `auto_phased`: default. The worker creates a phase plan and executes phases
  until the goal is reached, policy says to stop, or evidence becomes
  inconclusive.
- `single_run`: use only when the task is already small and bounded.
- `phase_plan_only`: create a phase plan without executing it.

## Phase Shape

Each phase should include:

- objective
- allowed actions
- expected evidence
- exit criteria
- timeout budget

## Default Limits

```text
maxPhaseCount: 6
maxPhaseSeconds: 600
```

These are coordination limits, not provider billing caps. Provider spending
rules still come from the auth and cost policy.

## Host-Agent Behavior

The XUUnity host agent should:

- prefer `auto_phased` for large work;
- stop after any failed, blocked, suspicious, or inconclusive phase;
- relay complete worker reports without redoing routine evidence collection;
- verify locally only when the worker report is invalid, contradictory, or
  user-challenged.

## Worker Report Fields

```text
phase_plan
phase_results
```

These fields are additive to the standard worker report. Future multi-run
schedulers should use the same fields rather than creating a separate progress
protocol.
