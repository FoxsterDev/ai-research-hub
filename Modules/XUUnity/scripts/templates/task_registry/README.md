# Task Registry

## Purpose
Repo-level delivery memory for human-triggered task closure, follow-up feedback, and derived portfolio metrics.

## Files
- `task_events.jsonl`
  - append-only source of truth
  - created on first task-registry write
- `task_index.yaml`
  - low-risk current snapshot by `task_id`
- `task_event_schema.md`
  - event field contract and state model
- `task_event_schema.json`
  - machine-readable validation contract for task events
- `archive_policy.md`
  - rollover and retention rules for task-history files
- `metrics_summary.md`
  - derived rollups for engineering and business reviews
- `lessons_learned.md`
  - repeated patterns only after multiple tasks support them

## Rules
- Do not treat Slack as source of truth.
- Do not reward chat volume.
- Use `task_started` when you want start-to-finish timing metrics to be real instead of inferred from closure.
- Record closure only on explicit human trigger.
- Preserve history with append-only events.
- Task audit notes under `AIOutput/Reports/Tasks/` are repo-level portfolio artifacts, not project-local `Assets/AIOutput/` delivery-history files.
- Validate public-core task registries against `task_event_schema.json` before publishing metrics or migration results.
