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
Aggressive cleanup still starts with the audit utility; this apply utility only executes the already approved plan.

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
- Treat `Assets/AIOutput/ProjectMemory/` content and runtime-support files as protected unless the approval explicitly names them.
- Do not delete, truncate, or substantively rewrite `ProjectMemory/` during cleanup apply.
- Minimal reference-only rewrites inside `ProjectMemory/` are allowed only when they were explicitly approved as dependency-unlocking cleanup steps.
- Treat `AIOutput/Reports/` canonical summaries, latest evaluation evidence, and `README.md` files as protected unless the approval explicitly names them.
- If the approved cleanup plan explicitly includes reference rewrites needed to unlock archive or delete actions, those rewrites are part of the approved scope and must be applied before moving or deleting the scored artifacts.

## Apply Process
1. Read the reviewed cleanup plan.
2. Extract only the user-approved actions.
3. Re-verify that every approved target still matches the reviewed state.
4. Reprint a short execution summary before destructive actions:
   - approved archive targets
   - approved delete targets
   - approved reference rewrites
   - protected files skipped
5. For every approved delete target, restate:
   - why removal is safe
   - why removal is needed
   - what evidence or canonical artifact remains
6. Apply approved reference rewrites first when the cleanup plan depends on them.
7. Apply archive actions second.
8. Apply delete actions third.
9. Report exactly what changed and what was intentionally left untouched.

## Drift Rule
If any of the following changed since the audit, stop and request a refreshed cleanup review:
- file disappeared or moved
- file contents changed materially
- a newer canonical report appeared
- a protected-path match now applies

## Output
- approved scope applied
- rewritten references
- archived files
- deleted files
- skipped files
- drift or mismatch findings
- residual follow-up items

## Rule
This utility is execution-only.
It must not invent new cleanup candidates.
If the existing cleanup plan is incomplete or stale, route back to `system_output_cleanup.md` instead of improvising.
