# XUUnity Utility: Task Registry Reconcile

## Goal
Rebuild or repair the current task snapshot index from append-only task events.

## Use For
- stale or missing `task_index.yaml`
- registry migration
- Jira adoption after chat-scoped task ids already exist
- validating whether current task states match the event history

## Inputs
- `AIOutput/Registry/task_events.jsonl`
- `AIOutput/Registry/task_index.yaml` when present
- task audit notes under `AIOutput/Reports/Tasks/` when they help resolve ambiguity
- repo router and host topology

## Process
1. Treat `task_events.jsonl` as the source of truth.
2. Group events by `task_id`.
3. Fold each task's events in timestamp order.
4. Rebuild the current snapshot fields:
   - identity
   - latest event
   - engineering state
   - validation state
   - acceptance state
   - linked audit path
   - latest summary
5. Surface ambiguous cases instead of guessing:
   - conflicting origin refs
   - missing task ids in audit notes
   - unclear parent or child relationships
6. Write back only the low-risk snapshot result into `task_index.yaml`.

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py reconcile --repo-root <repo-root>` when a shell-capable workflow is available.

## Output
- reconciliation status:
  - current
  - rebuilt
  - partially ambiguous
- rebuilt task count
- ambiguous task ids
- recommended follow-up actions

## Rules
- Do not rewrite historical events to make the index look cleaner.
- If Jira or another tracker becomes available later, preserve prior ids through `origin_ref` or explicit task-link fields instead of erasing history.
