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
- If the active project keeps an extraction baseline at `<...>/AIOutput/Reports/Tasks/extraction_baselines/`, use the latest baseline file as evidence. Compare current counts (public/internal/skills/hints) against it. The baseline file IS the artifact — there is no separate framework spec to consult.
- If extraction routing changed recently and no baseline file or recent run exists, flag the gap explicitly.
- When the active system exposes a Unity MCP operational layer, check whether it also exposes a checked-in smoke route.
- Prefer checked-in smoke routes over ad hoc manual command lists when verifying MCP operational health.
- If a checked-in smoke route exists and the current session can access the required project/editor state, run the narrowest representative smoke route and include the result in the review.
- If MCP exists but no checked-in smoke route exists, flag that as a system-health gap.
- Distinguish:
  - public reusable smoke contracts in `AIRoot`
  - host-local operational wrappers in `AIOutput/Operations/`
  - project-local smoke expectations in project memory or project-specific internal knowledge
- When optional private/paid module support is in scope, include the Private Module Overlay Status subsection and check discovery, entitlement, Rollsync, and routing-smoke health without quoting private pack content.
- When `xuunity_module_status` or `xuunity_module_rollsync` are available, prefer their redacted output as the MCP/API-facing evidence source for private module overlay health.
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
- Reconcile the public design registry on every run (standing sanitary step):
    - re-verify each design in `AIRoot/Design/README.md` (and any `AIRoot/Operations/<Surface>/Designs/README.md`) against actual files/scripts/CLI, never the document's self-assessment
    - keep columns truthful: `Status` (`implemented` / `active` / `draft` / `planned` / `archived`), `Imp.` (1–5), `Impl.` (% wired into the live module), `Effort` (size·time·complexity remaining), and the concrete `Left to 100%` gap
    - re-sort rows by importance (desc) then remaining effort (asc) — most important and cheapest-to-finish first
    - move fully-consumed (a generator whose output already shipped) or retired (superseded) designs into `Design/Archived/` via `git mv` and fix inbound links; never delete
    - flag registry drift as a finding: a `Status`/`Impl.` that no longer matches the repo, a design file missing from the registry, or an archived doc still referenced as live
    - keep the registry English-only and evidence-cited; stamp provenance (author + date) when the reconciliation changes statuses

## Output
- High-severity conflicts
- Redundant files or sections
- Missing files or weak layers
- Knowledge extraction regression status
- MCP smoke regression status
- Knowledge reachability status
- Public core versus internal overlay boundary status
- Storage consistency status
- Design registry reconciliation status
- Recommended cleanup order

### Private Module Overlay Status Template

When private or paid module support is in scope, include a dedicated subsection
in the report using this exact shape:

```md
**Private Module Overlay Status**
- `registry_tool`: `<path or none>`
- `discovery_root`: `<path or none>`
- `loaded_pack_ids`: `<pack id or none>`
- `locked_pack_ids`: `<pack id or none>`
- `invalid_pack_ids`: `<pack id or none>`
- `rollsync_status`: `ready` | `ready_with_warnings` | `locked` | `invalid` | `not_configured` | `not_run`
- `route_smoke_status`: `passed` | `failed` | `not_run`
- `mcp_api_status`: `ready` | `ready_with_warnings` | `locked` | `invalid` | `not_configured` | `not_run`
- `entitlement_trust_level`: `local_flag` | `signed_offline` | `server_verified` | `unknown` | `not_run`
- `entitlement_verified`: `true` | `false` | `not_run`
- `evidence_date`: `YYYY-MM-DD` or `none`
- `private_content_boundary`: `clean` | `leak_detected` | `unknown`
- `result_summary`: `<short factual summary>`
- `gaps`:
  - `<gap or none>`
  - `<gap or none>`
```

Use:
- `private_content_boundary: clean` when public files only reference pack ids or registry paths and private skill content stays outside the public repo.
- `route_smoke_status: passed` only when a representative task matched a loaded pack from `loadedPacks[]`.
- `mcp_api_status` should come from redacted `xuunity_module_status` or `xuunity_module_rollsync` output when available.
- `entitlement_trust_level` and `entitlement_verified` should come from
  redacted MCP/API output. Do not inspect or quote user-local entitlement paths
  in the health report.
- `rollsync_status: not_run` when the registry exists but Rollsync was not executed in the current review.
- `discovery_root: none` when no `AIModules/` root or explicit module root is configured.

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

### Design Registry Reconciliation Status Template

When the public design registry is in scope, include a dedicated subsection in
the report using this exact shape:

```md
**Design Registry Reconciliation**
- `registry`: `AIRoot/Design/README.md`
- `designs_total`: `<n>`
- `live`: `<n>` · `archived`: `<n>`
- `status_breakdown`: `implemented=<n> active=<n> draft=<n> planned=<n>`
- `resorted`: `yes` | `no`
- `drift_detected`:
  - `<design — declared vs verified status/impl, or none>`
- `moved_to_archive`:
  - `<design — reason, or none>`
- `evidence_date`: `YYYY-MM-DD`
- `result_summary`: `<short factual summary>`
```

Use:
- `drift_detected: none` only after every row was checked against the live repo.
- `moved_to_archive` lists designs relocated to `Design/Archived/` this run (generator-consumed or superseded); `none` if no move was needed.
- `resorted: yes` when row order was changed to importance (desc) then remaining effort (asc).
