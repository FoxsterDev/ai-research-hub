# XUUnity Utility: System Registry Refresh

## Goal
Refresh `AIOutput/Registry/project_registry.yaml` from the current monorepo structure without changing active prompt behavior.

## Use For
- portfolio metadata refresh
- after project onboarding
- after folder moves or router changes
- before portfolio/system reviews when registry freshness is uncertain

## Inputs
- current monorepo folder structure
- repo-level `Agents.md`
- presence of `AIModules/XUUnityInternal/`
- project-level `Agents.md`
- presence of `Assets/AIOutput/ProjectMemory/`
- presence of any host-declared gameplay bridge entry artifact under `Assets/AIOutput/` when the host registry tracks that concept
- current `AIOutput/Registry/project_registry.yaml` if present

## Process
1. Discover projects that have an active project router.
2. Verify whether each routed project has `Assets/AIOutput/ProjectMemory/`.
3. Verify whether each routed project has any host-declared gameplay bridge entry artifact under `Assets/AIOutput/` if the host registry schema expects that field.
4. Update only evidence-backed metadata fields:
   - project path
   - router filename
   - project memory presence
   - any host-defined gameplay-bridge presence field if explicitly part of the registry schema
   - lifecycle status if explicitly known
5. Refresh low-risk source-of-truth header fields when the repo router or shared-layer topology changed:
   - `shared_protocol_modules`
   - `xuunity_public_core`
   - `host_local_prompt_families`
   - `xuunity_internal_overlay`
6. Do not remove existing projects or reclassify project type unless the evidence is explicit and unambiguous.
7. Keep the registry as a portfolio index, not as a replacement for project-local truth.

## Output
- registry status:
  - current
  - refreshed
  - partially stale
- changed entries
- unchanged entries
- ambiguous fields requiring human review

## Safety Rule
- this utility may perform only low-risk, evidence-backed metadata refreshes
- destructive edits, ambiguous reclassification, or inferred platform changes require human review
