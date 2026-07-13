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

## Metadata Dimensions
A complete portfolio registry entry should carry these per-project dimensions:
- project type
- active platform targets
- monetization stack (ads mediation, analytics, attribution, IAP, notifications)
- AI readiness score (materialized, see Portfolio Report)
- project memory status
- known critical flows

Monetization stack and critical flows are durable, source-backed facts — verify
them from `<Project>/Packages/manifest.json` and the project's
`Assets/AIOutput/ProjectMemory/` (sdk_inventory, architecture), not from memory.
Portfolio-wide shared baselines belong in the host internal knowledge layer, not
repeated verbatim per entry.

## Portfolio Report
The reusable tool `AIRoot/Operations/project_registry_report.py` renders a portfolio
status report from the registry and computes a **structural** readiness score per
project. The tool is host-agnostic and config-driven: which on-disk signals define
readiness, any extra report columns, and the completeness dimensions all come from a
rubric JSON passed via `--rubric` (host-supplied, kept in the host repo alongside its
registry). Without a rubric it falls back to a neutral default (router +
project-memory presence). Band thresholds are configurable and default to the
project-health bands (blocked / fragile / usable / strong). `--write-back` persists
`ai_readiness_*` into the registry; `--json` emits machine-readable output. The
structural score is a proxy, not a substitute for a full `project_health_audit`.

## Safety Rule
- this utility is audit-first
- do not rewrite the registry unless the user asks or the audit flow explicitly hands off to `system_registry_refresh.md`
