# Task Event Schema

## Identity
- `task_id`
- `project_id`
- `repo_id`
- `origin_type`
  - `jira`
  - `chat`
  - `manual`
- `origin_ref`
- `parent_task_id`

## Core Event Fields
- `timestamp`
- `event_type`
- `actor`
  - `ai`
  - `human`
  - `system`
- `task_kind`
  - `bug`
  - `refactor`
  - `feature`
  - `review`
  - `incident`
  - `research`
- `severity`
- `platform`
- `summary`
- `engineering_state`
- `validation_state`
- `acceptance_state`
- `protocols_used`
- `skills_used`
- `linked_audit_path`

## Event Types
- `task_started`
- `work_finished`
- `audit_saved`
- `slack_reported`
- `build_validated`
- `runtime_validated`
- `production_validated`
- `human_accepted`
- `human_reopened`
- `human_rejected`
- `followup_created`

## State Model
- `engineering_state`
  - `proposed`
  - `in_progress`
  - `work_finished`
  - `blocked`
  - `superseded`
- `validation_state`
  - `not_validated`
  - `build_validated`
  - `runtime_validated`
  - `production_validated`
- `acceptance_state`
  - `pending_human_feedback`
  - `accepted`
  - `reopened`
  - `rejected`

## Timing Coverage Rule
- Lifecycle timing metrics such as `task_started -> work_finished` are valid only for tasks that actually contain a `task_started` event.
- Closure-only tasks remain valid history entries, but they must be excluded from start-to-finish timing aggregates.
