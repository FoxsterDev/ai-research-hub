# XUUnity Utility: Task Registry Archive

## Goal
Define safe archive and rollover handling for large task registries without breaking source-of-truth semantics.

## Use For
- event logs reaching high line counts
- yearly or quarterly rollover
- preparing a long-lived repo for public distribution
- reducing day-to-day noise while preserving history

## Inputs
- `AIOutput/Registry/task_events.jsonl`
- `AIOutput/Registry/task_index.yaml`
- `AIOutput/Registry/metrics_summary.md`
- `AIOutput/Registry/lessons_learned.md`
- repo router and host topology

## Archive Policy
- Keep `task_events.jsonl` as the active append target.
- Archive only old immutable event segments, never the latest active segment.
- Keep `task_index.yaml` as the active current snapshot.
- Keep `metrics_summary.md` and `lessons_learned.md` as current derived outputs.

## Default Rollover Triggers
- event log exceeds `5000` lines
- event log exceeds `5 MB`
- calendar-year boundary
- explicit user request

## Archive Destinations
- `AIOutput/Registry/Archive/task_events_<period>.jsonl`
- `AIOutput/Registry/Archive/metrics_summary_<period>.md`
- `AIOutput/Registry/Archive/lessons_learned_<period>.md`

## Process
1. Check whether rollover triggers are met.
2. Define the archive cut:
   - by date range
   - or by completed historical segment
3. Preserve event ordering and append-only semantics.
4. Keep the active `task_events.jsonl` file for current writes.
5. Update any README or index notes needed so archived periods remain discoverable.
6. Do not archive `task_index.yaml`; rebuild it from active plus archived events when necessary through reconciliation.

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py archive-plan --repo-root <repo-root>` when a shell-capable workflow is available.

## Output
- rollover recommendation:
  - `not_needed`
  - `recommended`
  - `required`
- proposed archive segments
- active file after rollover
- cautions

## Rules
- Archive, do not delete, historical task events.
- Never split one task timeline across active and archived files in a way that makes reconciliation impossible without clear period metadata.
- Prefer period-based segment names over ad hoc file names.
