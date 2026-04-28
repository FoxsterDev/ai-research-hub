# XUUnity Utility: Task Tracking Start

## Goal
Create the first durable task-history event so later closure, acceptance, reopen, and metrics flows have a defined lifecycle start.

## Use For
- `start tracking this task`
- `open task record`
- `create task record`
- `task started`

## Inputs
- active repo router
- active project router when one project owns the work
- initial user problem statement or external tracker reference
- current repo-level task registry files when present:
  - `AIOutput/Registry/task_events.jsonl`
  - `AIOutput/Registry/task_index.yaml`
- issue-tracker identity such as Jira when available

## Identity Rules
- Prefer an existing external id such as Jira when available.
- Otherwise create a chat-scoped id in this shape:
  - `<project-slug>_<topic-slug>_<short-hash>`
- If the current session already resolved a matching task id for the same problem, reuse it instead of creating a duplicate.

## Lifecycle Rules
- Default start transition:
  - `engineering_state = in_progress`
  - `validation_state = not_validated`
  - `acceptance_state = pending_human_feedback`
- This utility creates `task_started`. It does not imply any closure or validation.

## Process
1. Resolve the repo-level registry root from the active repo router and host topology.
2. Resolve or create the `task_id`.
3. Determine the initial task kind:
   - `bug`
   - `refactor`
   - `feature`
   - `review`
   - `incident`
   - `research`
4. Append a `task_started` event to `AIOutput/Registry/task_events.jsonl`.
5. Update only low-risk current fields in `AIOutput/Registry/task_index.yaml`:
   - identity
   - latest timestamp
   - latest event type
   - current states
   - initial summary
6. Do not create a task audit note by default unless the host workflow explicitly needs one at task start.

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py start ...` when a shell-capable workflow is available.

## Output
- resolved `task_id`
- appended event type
- current initial states
- suggested follow-up trigger commands

## Rules
- Use this workflow when timing metrics should include the real task start.
- Do not auto-create `task_started` for every casual chat. Keep it human-triggered.
