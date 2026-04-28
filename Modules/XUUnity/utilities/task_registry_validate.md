# XUUnity Utility: Task Registry Validate

## Goal
Validate task-registry files against the public contract before metrics, reporting, or migration work relies on them.

## Use For
- `validate task registry`
- `check task events`
- `task registry lint`
- pre-publication or pre-rollup validation

## Inputs
- `AIOutput/Registry/task_events.jsonl`
- `AIOutput/Registry/task_index.yaml`
- `AIOutput/Registry/task_event_schema.md`
- `AIOutput/Registry/task_event_schema.json`
- task audit notes under `AIOutput/Reports/Tasks/` when path references need spot-checking

## Validation Scope
- JSON event shape
- required field presence
- event-type membership
- state-value membership
- lifecycle consistency:
  - no invalid state values
  - no impossible acceptance states for the latest snapshot
- timing coverage consistency:
  - tasks without `task_started` must not be counted as full-lifecycle tasks
- snapshot consistency:
  - `task_index.yaml` must reflect the latest known event per `task_id`

## Process
1. Validate each event line against `task_event_schema.json`.
2. Check for malformed JSONL rows.
3. Group events by `task_id`.
4. Fold each task timeline and compare the derived latest snapshot against `task_index.yaml`.
5. Flag broken references such as missing audit-note paths when the index claims they exist.
6. Report whether the registry is:
   - `valid`
   - `valid_with_warnings`
   - `invalid`

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py validate --repo-root <repo-root>` when a shell-capable workflow is available.

## Output
- registry validation status
- malformed rows
- schema violations
- snapshot drift
- missing referenced audit notes
- recommended next action

## Rules
- Validation is audit-first. Do not mutate history in this utility.
- Route to `task_registry_reconcile.md` when snapshot drift is the main issue.
- Route to `task_registry_bootstrap.md` when required scaffold files are missing.
