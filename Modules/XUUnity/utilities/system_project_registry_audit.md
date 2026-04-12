# XUUnity Utility: System Project Registry Audit

## Goal
Audit `AIOutput/Registry/project_registry.yaml` against the current monorepo structure without modifying it by default.

## Use For
- checking whether the registry is current
- finding stale project metadata
- validating portfolio reviews before reporting
- deciding whether `xuunity system registry refresh` should run next

## Inputs
- current monorepo folder structure
- repo-level `Agents.md`
- presence of `AIModules/XUUnityInternal/`
- project-level `Agents.md`
- presence of `Assets/AIOutput/ProjectMemory/`
- presence of any host-declared gameplay bridge entry artifact under `Assets/AIOutput/` when the host registry tracks that concept
- current `AIOutput/Registry/project_registry.yaml`

## Process
1. Discover projects that currently have an active project router.
2. Compare the discovered set against the registry entries.
3. Verify low-risk source-of-truth header fields:
   - `shared_protocol_modules`
   - `xuunity_public_core`
   - `host_local_prompt_families`
   - `xuunity_internal_overlay`
4. Verify key low-risk project fields:
   - project path
   - router filename
   - project memory presence
   - any host-defined gameplay-bridge presence field if the registry schema uses one
   - lifecycle status if explicitly known in source or operations docs
5. Classify each entry as:
   - current
   - stale
   - missing from registry
   - ambiguous
6. Recommend `xuunity system registry refresh` only when the needed updates are evidence-backed and low-risk.

## Output
- overall registry status
- source-of-truth header status
- current entries
- stale entries
- missing entries
- ambiguous entries
- recommended next action

## Safety Rule
- this utility is audit-first
- do not rewrite the registry unless the user asks or the audit flow explicitly hands off to `system_registry_refresh.md`
