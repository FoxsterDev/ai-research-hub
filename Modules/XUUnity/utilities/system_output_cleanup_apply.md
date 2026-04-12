# XUUnity Utility: System Output Cleanup Apply

## Goal
Apply a previously reviewed output-cleanup plan after explicit user approval.
This utility exists to separate cleanup analysis from cleanup execution.

## Entry Commands
- `xuunity system cleanup apply`
- `xuunity system apply cleanup`
- `xuunity system apply approved cleanup`

## Preconditions
Before using this utility, a cleanup audit must already exist from `system_output_cleanup.md`.
Do not use this utility until the user has explicitly approved the exact cleanup scope.

## Approval Inputs
Allowed approval forms:
- full approval
- project-specific approval
- archive-only approval
- delete-only approval
- partial approval with specific file paths
- reject

## Hard Safety Rules
- Never delete any file or folder without explicit user approval.
- Never expand the approved scope during apply.
- If a file was approved for archive, do not silently hard-delete it.
- If a previously approved delete action now has weaker evidence, stop and ask again.
- If current file state differs from the reviewed plan, stop and report the drift before applying anything.
- Treat `Assets/AIOutput/ProjectMemory/` and runtime-support files as protected unless the approval explicitly names them.
- Treat `AIOutput/Reports/` canonical summaries, latest evaluation evidence, and `README.md` files as protected unless the approval explicitly names them.

## Apply Process
1. Read the reviewed cleanup plan.
2. Extract only the user-approved actions.
3. Re-verify that every approved target still matches the reviewed state.
4. Reprint a short execution summary before destructive actions:
   - approved archive targets
   - approved delete targets
   - protected files skipped
5. For every approved delete target, restate:
   - why removal is safe
   - why removal is needed
   - what evidence or canonical artifact remains
6. Apply archive actions first.
7. Apply delete actions second.
8. Report exactly what changed and what was intentionally left untouched.

## Drift Rule
If any of the following changed since the audit, stop and request a refreshed cleanup review:
- file disappeared or moved
- file contents changed materially
- a newer canonical report appeared
- a protected-path match now applies

## Output
- approved scope applied
- archived files
- deleted files
- skipped files
- drift or mismatch findings
- residual follow-up items

## Rule
This utility is execution-only.
It must not invent new cleanup candidates.
If the existing cleanup plan is incomplete or stale, route back to `system_output_cleanup.md` instead of improvising.
