# XUUnity Utility: Task Registry Bootstrap

## Goal
Provision the minimal repo-level scaffold required for the task-registry workflows.

## Use For
- first-time enablement of task history in a repo
- public-core setup where host-specific scaffolding is not present yet
- validating that the repo can support task start, closure, feedback, and metrics flows

## Inputs
- active repo router
- host topology when present
- current repo-level `AIOutput/Registry/` contents

## Required Scaffold
- `AIOutput/Registry/task_events.jsonl`
- `AIOutput/Registry/task_index.yaml`
- `AIOutput/Registry/task_event_schema.md`
- `AIOutput/Registry/task_event_schema.json`
- `AIOutput/Registry/metrics_summary.md`
- `AIOutput/Registry/lessons_learned.md`
- `AIOutput/Registry/archive_policy.md`
- `AIOutput/Reports/Tasks/`

## Process
1. Resolve the repo-level `AIOutput/` root from the active repo router.
2. Create the required scaffold when it is missing.
3. Preserve existing files when they already exist.
4. Validate that the public-core task-registry utilities and routing can operate against the scaffold.
5. Report whether the repo is:
   - `ready`
   - `partially provisioned`
   - `missing required scaffold`

## Tool Path
- Prefer `AIRoot/Modules/XUUnity/scripts/task_registry_tool.py bootstrap --repo-root <repo-root>` when a shell-capable workflow is available.

## Output
- bootstrap status
- created files
- existing files preserved
- remaining setup gaps

## Rules
- This utility defines the public-core bootstrap contract for task history.
- Do not hide task-registry requirements behind one host repo's private assumptions.
