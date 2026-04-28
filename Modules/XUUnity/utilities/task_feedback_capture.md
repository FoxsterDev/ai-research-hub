# XUUnity Utility: Task Feedback Capture

## Goal
Record human follow-up feedback after work was delivered, without rewriting prior task history.

## Use For
- `this works`
- `this has bugs`
- `reopen this task`
- `mark this validated`
- post-delivery user or customer feedback

## Inputs
- current repo-level task registry files:
  - `AIOutput/Registry/task_events.jsonl`
  - `AIOutput/Registry/task_index.yaml`
- explicit user feedback from the current session
- current task audit note when present
- latest known task states

## Feedback Mapping
- `this works`
  - append `human_accepted`
  - if the wording clearly implies a real representative runtime run, also append `runtime_validated`
- `customer says it works`
  - append `human_accepted`
  - append `runtime_validated` only if the reported path is representative enough to justify that claim
- `mark this validated`
  - append the narrowest truthful validation event:
    - `build_validated`
    - `runtime_validated`
    - `production_validated`
- `this has bugs`
  - append `human_reopened`
- `reopen this task`
  - append `human_reopened`
- explicit rejection or wrong-fix feedback
  - append `human_rejected`

## Process
1. Resolve the target `task_id`.
2. Interpret the user feedback into one or more follow-up event types.
3. Preserve the original closure event. Never mutate history in place.
4. Append the new event or events to `AIOutput/Registry/task_events.jsonl`.
5. Update `AIOutput/Registry/task_index.yaml` with the latest states and timestamp.
6. If the feedback materially changes closure confidence, refresh the task audit note with the new status or remaining gap.

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py feedback ...` when a shell-capable workflow is available.

## Output
- resolved `task_id`
- appended event types
- new current task states
- follow-up recommendation:
  - none
  - reopen implementation
  - gather stronger runtime evidence

## Rules
- Prefer append-only state changes over destructive edits.
- Do not conflate human acceptance with production validation.
- If the feedback is ambiguous, keep the stronger validation state unchanged and say so explicitly.
- Treat task audit notes as repo-level portfolio artifacts, not project-local delivery-history files.
