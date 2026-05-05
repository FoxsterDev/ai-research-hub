# XUUnity Utility: System Health Review

## Goal
Review the health of the prompt system itself, not only the product code.

## Rules
- Prefer identifying structural problems over rewriting everything.
- Treat duplicated routing, conflicting source-of-truth rules, and dead paths as high-severity issues.
- Flag any prompt file that adds cost without changing behavior.
- Recommend deletions, merges, or moves only when they improve clarity and routing reliability.
- Use `knowledge/decision_rules.md` when judging shared-vs-project destination, ownership boundaries, or public-safe placement.
- Use `knowledge/severity_matrix.md` when classifying the severity of system-health findings.
- Check whether the public `xuunity` core and the monorepo-internal `xuunity` overlay are clearly separated.
- Flag any active rule that still treats all reusable knowledge as a single shared layer.
- Flag any active rule that allows non-public-safe guidance to drift into `AIRoot/Modules/XUUnity/`.
- Include the health of the knowledge extraction pipeline when `xuunity extract ...` is part of the active system.
- If a knowledge extraction evaluation baseline or recent regression run exists, use it as evidence during the review.
- Prefer a machine-readable extraction regression summary when available.
- Prefer the canonical latest authoritative summary over ad hoc run files.
- If extraction routing changed recently and no regression evidence exists, flag that gap explicitly.
- When the active system exposes a Unity MCP operational layer, check whether it also exposes a checked-in smoke route.
- Prefer checked-in smoke routes over ad hoc manual command lists when verifying MCP operational health.
- If a checked-in smoke route exists and the current session can access the required project/editor state, run the narrowest representative smoke route and include the result in the review.
- If MCP exists but no checked-in smoke route exists, flag that as a system-health gap.
- Distinguish:
  - public reusable smoke contracts in `AIRoot`
  - host-local operational wrappers in `AIOutput/Operations/`
  - project-local smoke expectations in project memory or project-specific internal knowledge
- Audit shared knowledge reachability:
    - identify shared `knowledge/` or internal overlay knowledge files that have no explicit routing, trigger hints, utility references, or load path
    - treat knowledge with no realistic selection path as dead ballast
    - flag knowledge added without corresponding trigger updates as a system-health issue
- Check storage-consistency explicitly:
    - repo-level storage rule in `Agents.md`
    - public core references to `AIRoot/Modules/XUUnity/`
    - internal shared references to `AIModules/XUUnityInternal/`
    - project-router references to `Assets/AIOutput/`
    - project-router references to `Assets/AIOutput/ProjectMemory/`
    - whether prior-output loading accidentally points only at `ProjectMemory`
    - whether local routers duplicate or contradict the repo-level storage contract
- Prefer project routers that reference the repo storage contract over rephrasing it locally.

## Output
- High-severity conflicts
- Redundant files or sections
- Missing files or weak layers
- Knowledge extraction regression status
- MCP smoke regression status
- Knowledge reachability status
- Public core versus internal overlay boundary status
- Storage consistency status
- Recommended cleanup order

### MCP Smoke Regression Status Template

When Unity MCP operational health is in scope, include a dedicated subsection in
the report using this exact shape:

```md
**MCP Smoke Regression Status**
- `smoke_route`: `<path or none>`
- `scope`: `public_core` | `host_local` | `project_local`
- `run_status`: `passed` | `failed` | `not_run`
- `evidence_date`: `YYYY-MM-DD` or `none`
- `covered_checks`:
  - `<check name>`
  - `<check name>`
- `result_summary`: `<short factual summary>`
- `gaps`:
  - `<gap or none>`
  - `<gap or none>`
```

Use:
- `run_status: not_run` when the route exists but was not executed in the current review
- `smoke_route: none` when MCP exists but the system has no checked-in smoke route
- `scope: public_core` for reusable `AIRoot` smoke contracts
- `scope: host_local` for `AIOutput/Operations/` wrappers
- `scope: project_local` for project-specific validation runners or project-memory-declared smoke paths

Keep `result_summary` short and evidence-based. Do not collapse missing-route,
not-run, and failed-run cases into the same wording.
