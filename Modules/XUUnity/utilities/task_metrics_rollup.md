# XUUnity Utility: Task Metrics Rollup

## Goal
Derive business-facing and engineering-facing delivery metrics from task events without rewarding prompt volume.

## Use For
- monthly or milestone reporting
- AI-assisted delivery effectiveness reviews
- finding repeated bug families, reopen patterns, and validation gaps

## Inputs
- `AIOutput/Registry/task_events.jsonl`
- `AIOutput/Registry/task_index.yaml`
- task audit notes under `AIOutput/Reports/Tasks/` when a summary needs qualitative support
- repo router and host topology

## Metrics
- task count by kind:
  - `bug`
  - `refactor`
  - `feature`
  - `review`
  - `incident`
  - `research`
- acceptance rate
- reopen rate
- rejection rate
- runtime validation coverage
- average time from `task_started` to `work_finished`
- average time from `work_finished` to `human_accepted`
- platform distribution
- protocol and skill usage distribution by successful and reopened tasks

## Process
1. Read events as the only truth for timing and state transitions.
2. Build per-task timelines.
3. Classify timing coverage:
   - `complete_lifecycle` when both `task_started` and later closure exist
   - `closure_only` when the task was first recorded at closure
4. Derive aggregate metrics.
5. Report timing metrics only from `complete_lifecycle` tasks.
6. Extract repeated lessons only when at least two meaningful tasks support the pattern.
7. Save derived summaries separately from the event store.

## Output
- metrics summary
- repeated risk patterns
- repeated successful patterns
- weak validation patterns
- recommended protocol adjustments

## Rules
- Do not use number of chat turns, prompt length, or token volume as a success metric.
- Keep derived metrics reproducible from the event store.
- Do not pretend `task_started -> work_finished` timing is available for closure-only tasks.
