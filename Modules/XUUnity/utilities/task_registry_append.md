# XUUnity Utility: Task Registry Append

## Goal
Record a human-triggered task outcome as append-only task events plus a low-risk current snapshot.

## Use For
- `finish the work`
- `publish the work` when the host repo treats it as a closeout command
- `close this task`
- `record this fix`
- `post and record this work`
- preserving durable delivery history across projects

## Inputs
- active repo router
- active project router when one project owns the work
- current session evidence:
  - root cause
  - patch shape or task kind
  - changed files or reviewed scope
  - validation result
  - remaining runtime gap
- current repo-level task registry files when present:
  - `AIOutput/Registry/task_events.jsonl`
  - `AIOutput/Registry/task_index.yaml`
- `task_started` event when the repo uses full lifecycle timing
- current task audit note under `AIOutput/Reports/Tasks/` when present
- issue-tracker identity such as Jira when available

## Identity Rules
- Prefer the external system id when one already exists:
  - `jira`
  - future tracker ids explicitly declared by the host repo
- If no external id exists, reuse the current task id when the same chat or same audit note already established one.
- Otherwise create a chat-scoped id in this shape:
  - `<project-slug>_<topic-slug>_<short-hash>`
- Keep `parent_task_id` for follow-up, regression, reopen, or split-task relationships instead of overloading one task id.

## Lifecycle Rules
- `finish the work` records engineering closure, not final acceptance.
- Default transition on closure:
  - `engineering_state = work_finished`
  - `acceptance_state = pending_human_feedback`
- Do not silently upgrade a task to `accepted` or `runtime_validated` during closure unless the user explicitly triggered that state and the evidence is already present.
- If no prior `task_started` event exists, keep the closure valid but report that start-to-finish timing metrics are unavailable for that task.

## Process
1. Resolve the repo-level registry root from the active repo router and host topology.
1a. If the registry scaffold is missing, run the equivalent of `task_registry_bootstrap.md` first.
2. Resolve or create the `task_id` using the identity rules.
3. Determine whether the task is:
   - `bug`
   - `refactor`
   - `feature`
   - `review`
   - `incident`
   - `research`
4. Derive the minimum event payload:
   - `timestamp`
   - `task_id`
   - `project_id`
   - `repo_id`
   - `origin_type`
   - `origin_ref`
   - `parent_task_id`
   - `event_type`
   - `actor`
   - `task_kind`
   - `severity`
   - `platform`
   - `summary`
   - `engineering_state`
   - `validation_state`
   - `acceptance_state`
   - `protocols_used`
   - `skills_used`
   - `linked_audit_path`
5. Append a `work_finished` event to `AIOutput/Registry/task_events.jsonl`.
6. If the user explicitly asked for Slack posting and the host repo declares a Slack delivery route, record a separate `slack_reported` event after the post succeeds.
   - Explicit Slack posting includes direct Slack commands and any host-declared closeout trigger such as `finish the work` or `publish the work` when the repo router defines those commands as Slack-delivery triggers.
7. Update only low-risk current fields in `AIOutput/Registry/task_index.yaml`:
   - latest timestamp
   - latest event type
   - current states
   - summary
   - linked audit path
8. Create or refresh the task audit note under `AIOutput/Reports/Tasks/` when the work needs a durable human-readable writeup.

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py finish ...` when a shell-capable workflow is available.

## Output
- resolved `task_id`
- appended event types
- task index update status
- pending human feedback status
- suggested next trigger commands

## Rules
- This workflow is human-triggered. Do not append task-history events automatically during ordinary implementation chatter.
- Keep the event store append-only.
- Keep Slack optional and downstream.
- If the host repo defines specific closeout commands as Slack-delivery triggers, honor that routing when deciding whether `slack_reported` should be appended.
- Keep business rollups derived from events, not from raw chat volume.
- Treat task audit notes as repo-level portfolio artifacts that summarize task history. Do not treat them as project-local `Assets/AIOutput/` delivery history.
