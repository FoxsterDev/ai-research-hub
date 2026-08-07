# XUUnity Utility: System Health Review

## Goal
Measure the health of the installed `xuunity` system and, when explicitly
requested, run a bounded evidence-backed improvement loop.

Keep two independent result axes:
- `installation_health`: model-independent structure, routing, reachability,
  ownership, and public/private boundary health
- `model_surface_fitness`: fixture evidence for one exact model and execution
  surface

Never collapse these axes into one score. A strong model cannot repair an
unreachable installation, and a coherent installation does not prove that a
particular model follows it.

## Modes
- `review` is the default. It measures and reports without editing protocol
  sources.
- `improve` requires explicit user intent such as
  `xuunity system health improve`. It may evaluate one corrective hypothesis at
  a time in an isolated candidate worktree, then accept, reject, or mark the
  result inconclusive.
- A host may set a lower iteration or cost limit. Never exceed the declared
  limit, and never infer permission to spend on external model runs when no
  budget or approved runner is available.

## Ownership
- `utilities/system_self_evaluation.md` owns the installation/corpus review:
  routers, roles, skills, knowledge, conflicts, dead paths, design-registry
  reconciliation, and public-core promotion candidates.
- A host-local model-fitness runner owns fixture execution, transcript
  normalization, scoring, aggregation, and immutable run evidence.
- This utility owns orchestration, comparison, and the final health report.
- `utilities/system_protocol_clean_review.md` owns approved public protocol
  cleanup.
- `utilities/knowledge_integration.md` owns approved knowledge promotion.
- `utilities/system_evaluation_cadence.md` owns freshness and invalidation
  decisions.

## Process
1. Determine `review` or `improve` mode and record the trigger, iteration limit,
   and cost limit.
2. Run the deterministic installation audit when available, then use
   `utilities/system_self_evaluation.md` for the semantic installation review
   required by the current cadence.
3. Resolve the current model-surface identity from runtime or host evidence.
   Never ask the current model to grade its own compliance.
4. Locate an exact compatible fixture baseline. Run the host fixture suite when
   an approved adapter and budget are available; otherwise report `not_run` and
   the concrete gap.
5. Keep installation findings and model-surface findings separate in diagnosis
   and scoring.
6. In `review` mode, stop after the report and ordered recommendations.
7. In `improve` mode, select exactly one hypothesis with a named deterministic
   check or fixture metric. Before execution, record its acceptance threshold
   and the allowed non-regression budget for every protected metric.
8. Test the candidate outside the live source tree. Re-run the same static
   checks and the same comparable fixture matrix.
9. Classify the candidate:
   - `accepted` only when the predeclared threshold is met, no hard gate fires,
     and every supported model surface stays within its predeclared
     non-regression budget
   - `rejected` when the intended evidence does not move or a regression appears
   - `inconclusive` when repeated runs disagree or comparison identity differs
10. Apply an accepted change only through the existing cleanup or knowledge
    integration owner. Record rejected and inconclusive candidates instead of
    re-arguing them.

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
- If the active system keeps extraction regression evidence, resolve current health through the stable
  summary pointer `<host-report-root>/knowledge_extraction_eval_latest_summary.json`. The harness writes
  that file only for authoritative human-scored runs; it is a status projection, not a report locator.
  When full evidence is needed, retrieve the dated report and run bundle through host-local evidence
  records. Do not use an undated `..._baseline_v1.md` file as a selector: the harness reads it only to
  populate `baseline_exists`. Compare current counts (public/internal/skills/hints) against the reviewed
  run evidence. The dated report is the artifact — there is no separate framework spec to consult.
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
- When the active system keeps model-fitness fixtures (a host-level fixture runner and scorer that
  replay known-failure tasks against a model and measure the tool-call transcript), include the
  Model Fitness / Protocol Compliance Status subsection:
    - report per model-surface identity, never as a single aggregate: the same
      model and protocol text can behave differently across adapters, effort,
      permissions, or tools
    - treat "gate delivered but not executed" (a required check signed off — e.g. as a closed task
      item — without being run) as a high-severity, model-specific compliance finding
    - treat a protocol change that claims to fix a compliance or delivery defect as unproven until
      a fixture re-run moves the measured metric; fixtures, not opinions
    - flag as a gap any active model-surface identity with no exact baseline
- Treat a run as `invalid`, not as a low score or a success, when it times out,
  exits unsuccessfully, has an unreadable transcript, lacks the required output
  diff, or does not attempt the fixture task.
- A critical defect trap is a hard gate and cannot be averaged into a passing
  grade.
- Absence of known traps is not task completion. Require the fixture's positive
  completion assertions or task-specific validator before a run is valid.
- Reuse an exact baseline only when all baseline identity fields match:
  - model id and version
  - reasoning effort
  - agent surface
  - adapter and adapter version
  - tool and permission policy
  - protocol fingerprint
  - fixture-suite hash
  - scorer version
- For a protocol-improvement A/B experiment, the protocol fingerprint is the
  recorded treatment variable: baseline and candidate fingerprints must
  differ, while every other identity field above must match. This is a
  controlled experiment, not exact-baseline reuse. If any other field changes,
  the result is `inconclusive`.
- Use repeated-run range or variance when available. Disagreement that can
  change the decision is `inconclusive`.
- Keep raw host transcripts, concrete fixture tasks, and private identifiers out
  of public reports and public protocol files.

## Output
- Mode, trigger, iteration limit, and cost limit
- Installation health status and installation-review evidence pointer
- High-severity conflicts
- Knowledge extraction regression status
- Model fitness / protocol compliance status (per model-surface identity)
- MCP smoke regression status
- Public core versus internal overlay boundary status
- Recommended cleanup order
- Improvement hypothesis and expected metric, or `none`
- Candidate result: `not_run` | `accepted` | `rejected` | `inconclusive`

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

### Model Fitness / Protocol Compliance Status Template

When the active system keeps model-fitness fixtures, include a dedicated
subsection in the report using this exact shape:

```md
**Model Fitness / Protocol Compliance Status**
- `fixture_suite`: `<host fixture-runner path or none>`
- `suite_hash`: `<stable hash or none>`
- `protocol_fingerprint`: `<stable fingerprint or none>`
- `current_session_identity`: `<model + version + effort + surface, or unknown>`
- `current_session_baseline_match`: `exact` | `stale` | `missing` | `not_runnable`
- `fixtures_run`: `<fixture ids or none>`
- `models_scored`:
  - `<model-surface identity>` — baseline `exact` | `stale` | `missing` | `not_runnable`,
    score `<n>/100` (`fit` | `fit_with_supervision` | `marginal` | `unfit`),
    valid runs `<n>/<n>`, range `<min>-<max>`, required stack loaded `<n>%`,
    critical defects `<n>`, gate `executed` | `signed_without_execution` | `absent`
- `invalid_runs`:
  - `<model-surface identity> — <reason>` or `none`
- `compliance_incidents`:
  - `<model-surface identity> — <one-line incident> — <evidence pointer>` or `none`
- `cross_model_notes`: `<which models degrade on which protocol mechanism, or none>`
- `protocol_changes_gated`:
  - `<change> — metric `moved` | `did_not_move` | `inconclusive` — `accepted` | `rejected` | `inconclusive` or `none`
- `evidence_date`: `YYYY-MM-DD` or `none`
- `result_summary`: `<short factual summary>`
- `gaps`:
  - `<model in active use with no baseline, fixture not re-run after a protocol change, or none>`
```

Use:
- `gate: signed_without_execution` when the run produced a gate artifact (task item, checklist
  entry, assertion) without evidence in the tool log that the named files were actually read —
  this is a compliance incident even when the shipped diff happens to be correct.
- `models_scored` rows come from the scorer's `metrics.json`, never from a model's self-report.
- Each model row's `baseline: exact` requires every exact-baseline identity
  field listed in the Rules section to match. The current-session field reports
  only the active session identity.
- Do not put invalid runs into the score denominator.
- `protocol_changes_gated: rejected` is a valid, expected outcome; record it rather than
  re-arguing the change in prose.
- Keep fixture task content and host identifiers out of this public template; the host report
  instance may cite host-local evidence paths.

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

### Installation Review Status Template

Include a dedicated subsection using this exact shape:

```md
**Installation Review Status**
- `audit_tool`: `<public audit path or none>`
- `audit_status`: `clean` | `findings` | `invalid` | `not_run`
- `review_scope`: `quick` | `full`
- `installation_score`: `<n>/20` or `not_scored`
- `report_pointer`: `<host report path or none>`
- `high_severity_findings`: `<n>`
- `public_promotion_candidates`: `<n>`
- `evidence_date`: `YYYY-MM-DD` or `none`
- `result_summary`: `<short factual summary>`
- `gaps`:
  - `<gap or none>`
```

Use:
- `quick` for deterministic inventory and routing checks.
- `full` when semantic conflict review, design reconciliation, or promotion
  decisions were also performed.
- Keep `installation_score` independent of all model-fitness scores.
