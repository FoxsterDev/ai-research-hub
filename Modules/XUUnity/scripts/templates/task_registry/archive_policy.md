# Task Registry Archive Policy

## Goal
Keep task-history files scalable without losing append-only source-of-truth semantics.

## Active Files
- `task_events.jsonl`
- `task_index.yaml`
- `metrics_summary.md`
- `lessons_learned.md`

## Archive Destinations
- `AIOutput/Registry/Archive/task_events_<period>.jsonl`
- `AIOutput/Registry/Archive/metrics_summary_<period>.md`
- `AIOutput/Registry/Archive/lessons_learned_<period>.md`

## Default Rollover Triggers
- active `task_events.jsonl` exceeds `5000` lines
- active `task_events.jsonl` exceeds `5 MB`
- calendar-year boundary
- explicit human request

## Rules
- Archive historical event segments; do not delete them.
- Keep `task_index.yaml` active and rebuildable.
- Keep timing and reconciliation possible across archived and active segments.
- Do not split one task's timeline across files without clear period metadata.
