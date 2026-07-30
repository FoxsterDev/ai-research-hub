# Public Design Rules

Use the design layer with a strict split:

- cross-cutting public designs -> `AIRoot/Design/`
- public tool-specific or surface-specific designs ->
  `AIRoot/Operations/<ToolOrSurface>/Designs/`
- reusable public prompt/scaffold templates -> `AIRoot/Templates/`
- host-local or private designs -> `AIOutput/Operations/Design/`

Use `AIRoot/Design/` for:
- reusable public architecture plans
- protocol design that spans more than one operation
- topology, automation, and policy models that should travel across repos

Do not put host-local workflow plans, private operational wrappers, or
project-specific implementation notes here.

If a design is only about one public tool or operational surface, keep it under
that tool or surface's own `Designs/` folder instead of placing it here.

Retired or fully-consumed designs are not deleted — they move to
[`./Archived/`](./Archived) and are listed in the [Archived](#archived) section below.

## Registry

> **Status** = document lifecycle:
> `implemented` (≈100% built **and** still the source of truth — reference only, no work pending) ·
> `active` (in force and still being finished) ·
> `draft` (design not finalized) ·
> `planned` (approved direction, not built yet) ·
> `archived` (moved to [`./Archived/`](./Archived): a `historical` recipe or a `legacy` tombstone).
>
> **Imp.** = importance to the system (1–5). **Impl.** = degree of implementation from the
> 2026-06-16 full review plus targeted additions recorded later
> (✅ done · 🟡 partial · ⬜ not built · 📦 work delivered, doc is a recipe · 🗄 superseded).
> A `%` is an estimate (`est.`) unless backed by a count (e.g. `100% (25/25 tests)`); `implemented` rows reflect verified completion.
> Reconciled against the public `AIRoot` sources and public-safe host integration contracts.
>
> **Review: `xuunity system progress review`, 2026-06-16.** Jump to: [Priority Backlog](#priority-backlog-active-work-by-priority) ·
> [Scoring and Actual Status](#scoring-and-actual-status-review-2026-06-16) · [Archived](#archived) ·
> [Analysis Provenance](#analysis-provenance--review-notes).
>
> **Targeted addition, 2026-07-29:** model-fitness measurement validity and the reduced-stack gate
> were independently audited and added as an implementation-ready planned design. This is not a
> replacement full-registry reconciliation.

Rows are sorted by **priority = importance (desc), then remaining effort (asc)** — most important and
cheapest-to-finish first. `implemented` rows carry housekeeping only. `Effort` is a rough remaining-work
estimate (size · time · complexity). The `Why it matters (or does not)` column justifies the importance
score and, for any design with work remaining, carries the concrete **Left to 100%** gap on a second line
of the same cell (omitted for `implemented`/done rows, whose status already says so). Archived docs are in
their own table below; for the actionable-only ordering see the [Priority Backlog](#priority-backlog-active-work-by-priority).

| Design | Status | Imp. | Impl. | Effort (size·time·cx) | Why it matters (or does not) |
| --- | --- | :---: | --- | --- | --- |
| `AIROOT_PUBLIC_MODULE_ARCHITECTURE_DESIGN.md` | implemented | 5 | ✅ 100% | — done | Defines the public / host-local / project layering contract the whole repo is built on; every other design assumes this topology — breaking it breaks routing and cross-project sharing. |
| `XUUNITY_SKILLS_SYSTEM_DESIGN.md` | implemented | 5 | ✅ 100% | — done | Load-bearing content subsystem: skill families, always-on baseline safety, deterministic trigger routing, token budget, project overrides. The core cannot assemble a correct stack without it. |
| `XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md` | implemented | 5 | ✅ 100% | — done | Mother design of the paid/private module system: `module/pack/entitlements` contracts, resolver behavior, CLI surface, session integration. Defines the public/private boundary and load order. |
| `XUUNITY_PAID_MODULE_FIRST_PRINCIPLES_FIX_PLAN.md` | implemented | 5 | ✅ 100% (25/25 tests) | — done | Sets the commercial + security invariants for paid modules (entitlement-provider contract, license ≠ local flag, redaction boundary, capability tags). Errors here become product and security debt. |
| `XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` | planned | 5 | ⬜ ~5% (est.) | S · ~1d · Low | Parent safety policy (allowlist, deny-by-default, runtime-critical denylist, mandatory artifact + human gate) that makes *safe* autonomy possible — the most strategically important unbuilt direction.<br>**Left to 100%:** trim to a thin "policy north-star" after the 3 plans land; drop duplicated level/allowlist/gate detail. |
| `XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md` | active | 5 | 🟡 ~85% (est.) | S · ~1–2d · Med | Lifts routing reliability from prompt-discipline to an enforceable, testable contract. The reliability core and the only path from ~82 to 95+. Executable layer built 2026-06-16: canonical `knowledge/execution_contract.md`, `knowledge/routing_trigger_matrix.md`, `scripts/tests/routing_fixtures/`, and the `scripts/routing_gate_check.py` gate (8/8 routing-gate tests pass).<br>**Left to 100%:** host-local matrix rows; broader fixture/bug-family coverage; optional CI wiring of the gate. |
| `XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md` | planned | 5 | 🟡 ~20% (host prototype, est.) | XL · ~3–4wk · High | Makes protocol delivery and exact model-surface suitability mechanically measurable without a universal full-stack gate. A host prototype and one fixture exist, but observer false negatives invalidated the first published comparison.<br>**Left to 100%:** P0 observer validity and null-score diagnostic correction; public rules/resolver/loader/gate; deterministic public runner; F2–F6 semantic fixtures; repeated aggregation and health integration. |
| `XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md` | active | 4 | 🟡 ~75% (est.) | S · ~1–2d · Low | Product-facing protocol layer for PMs/producers (explainers, change impact, rollout readiness, dependency maps). Product-critical, but a layer above the engineering core.<br>**Left to 100%:** build `protocols/flow_explainer.md` + `delivery_scope.md` (+ note formats), or trim them from the design. |
| `XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md` | planned | 4 | ⬜ ~5% (est.) | M · ~2–3d · Med | The executable L0–L4 ladder (act alone vs. need approval vs. stays human). Operationalizes the parent policy; the concrete next slice.<br>**Left to 100%:** `knowledge/autonomy_levels.md` (L0–L4) + autonomy hook/fields in `start_session.md`. |
| `XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md` | planned | 4 | ⬜ ~3% (est.) | M · ~2–3d · Med | The allowlist (A–F) + denylist that decides what is *actually* safe. Without it the level model is empty.<br>**Left to 100%:** `knowledge/low_risk_change_categories.md` (allowlist A–F) + `autonomy_exclusions.md` (denylist). |
| `XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md` | planned | 4 | ⬜ ~5% (est.) | M · ~2–3d · Med | Enforcement mechanism (classification → scope → validation → artifact gates) that gives autonomy teeth and auditability. Inert until levels + categories exist.<br>**Left to 100%:** `reviews/autonomy_gate_review.md` + `utilities/autonomy_change_artifact.md` + artifact template (4 gates). |
| `AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md` | draft | 4 | 🟡 ~35% (est.) | L · ~1–2wk · High | Makes onboarding topology explicit and durable instead of implicit bootstrap guessing; matters for scaling to many repo shapes, but evolves an already-working bootstrap rather than being load-bearing today.<br>**Left to 100%:** profiles B/C, CLI flags, `mirror_solution.sh`, `storage_profiles.md` + `router_override_rules.md`, topology health checks, registry fields. |
| `AI_TOOLING_AUTOMATION_DESIGN.md` | draft | 4 | 🟡 ~30% (est.) | XL · ~2–3wk · High | The bridge from analysis to execution (Jira/Unity/VCS connectors). High-leverage — turns advice into action — but a layer above the core; the system works without the unbuilt connectors.<br>**Left to 100%:** Pack B (Jira) + Pack D (GitLab/Bitbucket draft-PR) connectors; then Pack E (orchestration). |
| `XUUNITY_EXTERNAL_REPOS_DESIGN.md` | implemented | 2 | ✅ ~80% (dormant, est.) | XS · n/a · Low | Optional, deliberately dormant capability to promote knowledge to external repos. Peripheral — off by default; value is keeping the door open without committing transport. |

## Priority Backlog (active work, by priority)

What is **active and still needs doing**, ordered by leverage (impact × what it unblocks). `implemented`
docs are intentionally absent (done, reference only), as are `archived` docs (retired). The
2026-07-29 observer audit moved measurement validity to the front: model ranking and gate adoption
cannot be trusted until item 1's P0 is complete.

| # | Design | Status · Imp. · Impl. | What is left / next action |
| :---: | --- | --- | --- |
| 1 | `XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md` | planned · 5 · 🟡 ~20% (host prototype, est.) | **P0 first:** replace silent observer false negatives with explicit states, add real transcript conformance cases, null invalid scores, and reprocess preserved evidence for corrected diagnostics only. Then build the public resolver/loader/gate and F2–F6. |
| 2 | `XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md` | active · 5 · 🟡 ~85% (est.) | **Executable layer built (2026-06-16)** — canonical `knowledge/execution_contract.md` + de-duped 3 inline copies, `knowledge/routing_trigger_matrix.md`, `scripts/tests/routing_fixtures/`, and the `scripts/routing_gate_check.py` gate (8/8 routing-gate tests pass). **Residual:** host-local matrix rows; broader fixture/bug-family coverage; optional CI wiring of the gate. |
| 3 | `XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md` | planned · 4 · ⬜ ~5% (est.) | First autonomy slice: create `knowledge/autonomy_levels.md` (L0–L4) + add the autonomy-level hook/fields to `start_session.md`'s execution contract. |
| 4 | `XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md` | planned · 4 · ⬜ ~3% (est.) | Create `knowledge/low_risk_change_categories.md` (allowlist A–F) + `knowledge/autonomy_exclusions.md` (denylist); precondition for any `L2` auto-route. |
| 5 | `XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md` | planned · 4 · ⬜ ~5% (est.) | Create `reviews/autonomy_gate_review.md` + `utilities/autonomy_change_artifact.md` + the artifact template (the 4 gates). Implemented last; inert until items 3–4 exist. |
| – | `XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` | planned · 5 · ⬜ ~5% (est.) | Parent policy — **not separate build work**: once items 3–5 land, trim this to a thin "policy north-star" and remove the duplicated level/allowlist/gate detail. |
| 6 | `XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md` | active · 4 · 🟡 ~75% (est.) | Small gap: build `protocols/flow_explainer.md` + `protocols/delivery_scope.md` (+ `decision_note`/`rollout_note` formats), **or** drop them from the design to match reality. |
| 7 | `AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md` | draft · 4 · 🟡 ~35% (est.) | Build profiles B/C (root-only / symlinked), the CLI flags, `mirror_solution.sh`, `knowledge/storage_profiles.md` + `router_override_rules.md`, topology checks in `system_health_review.md`, and the extra `project_registry.yaml` fields. |
| 8 | `AI_TOOLING_AUTOMATION_DESIGN.md` | draft · 4 · 🟡 ~30% (est.) | Largest effort, lower urgency: build Pack B (Jira connector) and Pack D (GitLab/Bitbucket draft-PR); Pack E (orchestration) afterwards. Pack A/C already shipped. |

## Archived

Moved to [`./Archived/`](./Archived) — kept for the record only, **not** part of the live design set and
not in the backlog. Two kinds: `historical` (a generator whose output already shipped and is now the live
artifact) and `legacy` (a retired approach).

| Design (in `./Archived/`) | Kind | Imp. | Why archived |
| --- | --- | :---: | --- |
| `XUUNITY_WORKSTREAM3_POLICY_PACK_PROMPT_MASTER.md` | historical | 3 | Generator that produced all three policy packs in one pass; the packs in `reviews/policy_packs/` are now the live artifacts. |
| `XUUNITY_WORKSTREAM3_POLICY_PACK_PROMPT_MONETIZATION.md` | historical | 2 | Generator → `reviews/policy_packs/monetization_changes.md` (shipped). Recipe only. |
| `XUUNITY_WORKSTREAM3_POLICY_PACK_PROMPT_SAVE_LOAD.md` | historical | 2 | Generator → `reviews/policy_packs/save_load_changes.md` (shipped). Recipe only. |
| `XUUNITY_WORKSTREAM3_POLICY_PACK_PROMPT_UI_HEAVY.md` | historical | 2 | Generator → `reviews/policy_packs/ui_heavy_changes.md` (shipped; pack has since grown past the prompt). Recipe only. |
| `XUUNITY_UPSTREAM_SUBMODULE_DESIGN.md` | legacy | 1 | Tombstone for the retired single-upstream submodule model; superseded by `XUUNITY_EXTERNAL_REPOS_DESIGN.md`. |

## Scoring and Actual Status (review 2026-06-16)

This review was run as `xuunity system progress review`: each design was read in full and reconciled
against the **actual** state of the repository (not the document's self-assessment). Implementation is
backed by concrete files / scripts / CLI output. `AIRoot` is itself a git submodule
(`github.com/FoxsterDev/ai-research-hub.git`; it nests a second submodule at `Operations/XUUnityLightUnityMcp`),
so design history lives inside it.

**Scoring axes:** Importance (1–5, how load-bearing the document is for the system) · Relevance
(current / draft / legacy) · Implementation (actual % wired into the live module, with evidence).

### Maturity map

19 designs total — 14 live (in `Design/`) + 5 archived (in `Design/Archived/`):

1. **Implemented (done, source of truth — no work pending):** module architecture, skills system, both
   halves of the paid-module overlay, external repos (dormant by design). The load-bearing frame; works end-to-end.
2. **Active (in force, small gaps to finish):** root-cause routing (🟡 ~85% (est.)) and product protocols (🟡 ~75% (est.)).
3. **Drafts (in progress, 🟡 30–50%):** topology bootstrap, tooling automation (`root-cause-95` advanced to active ~85% on 2026-06-16; see below).
4. **Planned:** the low-risk autonomy family plus the implementation-ready model-fitness and
   reduced-stack gate design (host prototype exists; public enforcement and adoption suite do not).
5. **Archived (`./Archived/`):** four Workstream-3 generator prompts (`historical`) + the upstream-submodule tombstone (`legacy`).

### Implemented (done, source of truth)

These remain the canonical references for current behavior. The four importance-5 docs were taken to 100% on 2026-06-16 (their residual was housekeeping, not a design gap); external repos stays intentionally partial (dormant by design).

- **`AIROOT_PUBLIC_MODULE_ARCHITECTURE_DESIGN.md`** — importance **5**, **✅ 100%**.
  The whole layout follows the public / host-local / project-local contract: reusable public modules live in
  `AIRoot`, host-specific overlays and generated evidence stay outside the public core, and project memory
  remains project-local.
  *Done (2026-06-16): obsolete public-surface backup content was removed.*
- **`XUUNITY_SKILLS_SYSTEM_DESIGN.md`** — importance **5**, **✅ 100%**.
  All declared skill families physically exist, plus 2 beyond the design (`refactoring/`, `ui_tweens/`) — 16 family directories total;
  `skills/registry.md` (459 lines), baseline `skills/core/`, routing wired into `tasks/start_session.md`.
  Implementation is broader than the design. *Done (2026-06-16): project override guidance was normalized to the canonical template while host-specific variants remain outside the public core.*
- **`XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md`** — importance **5**, **✅ 100%**.
  The mother design of paid modules. All 5 schemas present; `module_registry_tool.py` implements every
  designed command + 5 extra (`route-smoke`, `session-plan`, MCP helpers, `validate-installer`);
  generated module resolution is covered by the public tooling contract; `start_session.md` steps 12a-12e
  route the overlay flow. *Done (2026-06-16): pack example synced to the shipped `usage.md` naming; remains the contract source of truth. The optional `xuunity module` CLI wrapper stays deferred by design.*
- **`XUUNITY_PAID_MODULE_FIRST_PRINCIPLES_FIX_PLAN.md`** — importance **5**, **✅ 100% (25/25 tests)**.
  P0–P2 confirmed: schema `xuunity.entitlements.schema.json` (provider/trustLevel/license/sync),
  resolver/verifier split, redaction boundary (`outputBoundary: redacted_api`, detector `public_game_qa_path_leak()`),
  capability tags, `reviews/module_pack_review.md`, `validate-installer`. **25 unit tests pass** (`python3 -m unittest` over `scripts/tests/test_module_registry_tool.py`).
  *Done (2026-06-16): P0–P2 marked done in the doc and the 25-passing-test count recorded.*
- **`XUUNITY_EXTERNAL_REPOS_DESIGN.md`** — importance **2**, **✅ ~80% (dormant by design, est.)**.
  Registry skeleton `external/registry.yaml` (`status: disabled_by_default`) + runbooks in `Operations/`.
  Transport and the external repo itself are intentionally not wired — complete for its dormant scope.
  *Rec: `implemented` (dormant); note in registry.yaml that `external/repos/` is created only on re-activation.*

### Active (in force, small gaps)

- **`XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md`** — importance **5**, active, **🟡 ~85% (est.)** (executable layer built 2026-06-16).
  The prose layer was already in production (owner-chain tracing + execution-contract schema in `start_session.md`,
  patch-shape taxonomy in `bug_fixing.md`, `utilities/routing_debug_template.md`, capability gate via
  `module_registry_tool.py session-plan --require-capability`). **The executable layer is now built:**
  `knowledge/execution_contract.md` is the single owner (the 3 inline copies in `start_session.md` are now references — "First Principle 3" closed),
  `knowledge/routing_trigger_matrix.md`, `scripts/tests/routing_fixtures/` (deep/shallow/legit-`local_fix` cases), and the
  `scripts/routing_gate_check.py` pre-patch gate (the 5 section-3 rules), covered by `scripts/tests/test_routing_gate.py` (8/8 pass).
  **Residual:** host-local matrix rows, broader fixture/bug-family coverage, optional CI wiring. *(Backlog #2.)*
- **`XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md`** — importance **4**, **🟡 ~75% (est.)**.
  6 protocols shipped + 2 beyond plan (`project_health_audit`, `project_memory_freshness`), shorthand routing
  in `start_session.md:380-389`. **Not created**: the planned `protocols/flow_explainer.md` and `protocols/delivery_scope.md`
  (+ `decision_note` / `rollout_note` formats). *Rec: build the missing protocols or drop them from the design. (Backlog #6.)*

### Drafts (in progress)

- **`AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md`** — importance **4**, draft, **🟡 ~35% (est.)**.
  There is a topology-first entrypoint `AIRoot/scripts/init_ai_topology.sh` + `host_topology.yaml` write. **Not built**: profiles B/C
  (root-only / symlinked — the doc's main motivation), CLI flags, `mirror_solution.sh`, knowledge files `storage_profiles.md` / `router_override_rules.md`,
  topology checks in `system_health_review.md`, the extra fields in `project_registry.yaml`. *Registry overstated maturity — corrected `active → draft`. (Backlog #7.)*
- **`AI_TOOLING_AUTOMATION_DESIGN.md`** — importance **4**, draft, **🟡 ~30% (est.)**.
  Only Pack C (Unity Verification) shipped — a standalone MCP package `Operations/XUUnityLightUnityMcp/` (dozens of `mcp__xuunity_light_unity__*` tools in this session).
  Pack A (portfolio metadata) is partially present (`xuunity system registry refresh` + `AIOutput/Registry/project_registry.yaml` + `Operations/router_storage_audit.py`).
  **Not built**: Pack B (Jira) and Pack D (GitLab/Bitbucket draft-PR); the `xuunity system jira|pr|unity` commands are wired nowhere; Pack E (orchestration) not started. *Registry corrected `active → draft`. (Backlog #8.)*

### Planned — model fitness and reduced-stack gate

- **`XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md`** — importance
  **5**, **🟡 ~20% (host prototype, est.)**. The host prototype proves that
  fixture replay and transcript scoring are useful, but a 2026-07-29
  independent audit found observer false negatives that invalidate its first
  published model comparison. The implementation-ready design separates
  obligation derivation, delivery evidence, mechanical gating, semantic
  outcomes, and repeated model-surface fitness. *P0 observer validity and
  corrected null-score diagnostics are Backlog #1.*

### Planned — low-risk autonomy family (not started)

**Headline finding:** none of the promised autonomy-specific files exist (`knowledge/autonomy_levels.md`,
`low_risk_change_categories.md`, `autonomy_exclusions.md`, `reviews/autonomy_gate_review.md`,
`utilities/autonomy_change_artifact.md`, the artifact template — all absent). The `L0–L4` ladder exists
**only** in `AIRoot/Roadmaps/AI_AUTOMATION_ROADMAP.md` and is wired into routing nowhere. Only the
**prerequisites** are built (Workstream-3 risk routing + policy packs + generic validation contract), not the autonomy lane itself.

- **`XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md`** — importance **5**, ⬜ ~5% (est.). Parent policy; its `L0–L3` level model is stale (superseded by LEVEL_MODEL_PLAN's `L0–L4`).
- **`XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md`** — importance **4**, ⬜ ~5% (est.). The correct autonomy implementation entry point. *(Backlog #3.)*
- **`XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md`** — importance **4**, ⬜ ~3% (est.). Allowlist (A–F) + denylist; a precondition for `L2` routing. *(Backlog #4.)*
- **`XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md`** — importance **4**, ⬜ ~5% (est.). The 4 gates; the most code-ready, but implemented last. *(Backlog #5.)*

*Family relationship:* the parent design (2026-04-02) is decomposed by three plans (2026-05-11);
denylist / allowlist / validation contract are **duplicated** across them. On implementation,
`AUTONOMY_DESIGN` should become a thin "policy north-star" while the normative detail lives in the three
plans and the files they generate. All 4 were mislabeled `active` — corrected to `planned`.

### Archived (moved to `./Archived/`)

- **Workstream-3 prompts** (`MASTER`, `MONETIZATION`, `SAVE_LOAD`, `UI_HEAVY`) — `historical`. These are the
  prompts that generated the policy packs. The packs already live in `reviews/policy_packs/` and are wired into
  routing (`start_session.md:179-199, 351-355`); the prompts have fully done their job and remain only as reproducible recipes.
- **`XUUNITY_UPSTREAM_SUBMODULE_DESIGN.md`** — `legacy`. The doc declares itself "Legacy reference only"; the old
  single-upstream model is dismantled, successor is `XUUNITY_EXTERNAL_REPOS_DESIGN.md`.

### Registry vs. reality (governance log)

Before this review the registry marked most documents `active`, which masked real
maturity. Reconciled in this update:

1. **5 mature designs:** `active → implemented` (built and remain the source of truth; backlog-free).
2. **4 low-risk autonomy docs:** `active → planned` (really ~5% (est.), not built).
3. **`AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN` and `AI_TOOLING_AUTOMATION_DESIGN`:** `active → draft` (the docs themselves are `draft`, implementation partial).
4. **4 Workstream-3 prompts + `XUUNITY_UPSTREAM_SUBMODULE_DESIGN`:** `active → archived` and physically moved to `./Archived/`.
5. **Design self-violation (resolved 2026-06-16):** the execution-contract schema was duplicated three times inline in `start_session.md` (the step-20b minimum-fields list, the `## Execution Contract` section, and the `## Output` derived-contract block) instead of a single canonical owner — exactly the unmet "First Principle 3" from `ROOT_CAUSE_ROUTING_95`. Now fixed: `knowledge/execution_contract.md` is the single owner and the three sites are references.

### Score by workstream

| Workstream | Maturity |
| --- | --- |
| Foundation (module architecture, skills) | ✅ 100% (implemented) |
| Paid / private module overlay | ✅ 100% (implemented) |
| Risk routing (Workstream-3 policy packs) | ✅ 100% (generators archived) |
| Product self-service (protocols) | 🟡 ~75% (est.) (active) |
| Tooling automation (MCP connectors) | 🟡 ~30% (est.), Unity only (draft) |
| Topology / bootstrap profiles | 🟡 ~35% (est.) (draft) |
| Root-cause routing → 95+ | 🟡 ~85% (est.) — prose + executable gate built (active) |
| Model fitness + reduced-stack enforcement | 🟡 ~20% (host prototype, est.) — observer P0 and public gate not built (planned) |
| Low-risk autonomy | ⬜ ~5% (est.) (planned) |

### Current bottleneck and next step

**Bottleneck:** model-fitness observer false negatives can currently turn
proven stack delivery into `0%` and can move the apparent first-mutation
boundary. Until P0 is fixed, model scores and a reduced-stack gate cannot be
trusted. The autonomy lane remains an important downstream gap, but it should
not be expanded on top of invalid compliance measurement.

**Recommended next milestone (highest leverage):** complete P0 from
`XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md` (Backlog #1), correct
preserved-evidence diagnostics with null scores, then build the public
reduced-stack resolver/loader.

**Next 3 deliverables:**
1. Observer state taxonomy, real transcript regression cases, null-score
   invalidity, and corrected supersession/diagnostic artifacts.
2. Public reduced-stack rules/schema plus deterministic resolver and loader.
3. Mechanical gate composition with `routing_gate_check.py`, followed by F2/F3
   fixtures.

## Analysis Provenance & Review Notes

- **Author:** `xuunity system progress review`, 2026-06-16. This pass also introduced the
  `implemented` status, moved 5 retired docs into `./Archived/`, and added the Priority Backlog.
- **2026-06-16 closeout:** the four importance-5 `implemented` designs were finished to 100% —
  obsolete public-surface backup content was removed, project override guidance was normalized to
  the canonical template, the paid-overlay pack example synced to `usage.md`, and the 25-passing-test
  count recorded in the paid-module fix plan.
- **2026-07-29 targeted addition:** added
  `XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md` after independent
  observer and architecture audits. The addition updates registry counts and
  current priority only; it does not claim a full re-review of every design.
- **Method:** `xuunity system progress review` discipline — each design read in full, then cross-checked
  against the live repository by parallel assessors, and the resulting claims adversarially re-verified.
  Implementation claims are backed by concrete files, scripts, schemas, and CLI output (cited inline above),
  not by the documents' self-assessment.
- **Scope of judgement:** the **Importance (1–5)** axis is an opinionated, model-produced scoring and is
  the most subjective column; **Status** and **Implementation %** are evidence-based but were sampled at a
  point in time. The submodule (`AIRoot`) may move independently.
- **For independent review agents:** treat this as a first-pass assessment to be challenged, not ground
  truth. Re-verify each row against the current public repo before acting — file paths, statuses, and
  generated host-local evidence can drift. Disagreement on the Importance axis is expected and welcome;
  record dissent rather than silently overwriting.

## Related Public Templates

Operational prompt templates are intentionally kept out of the design registry.
The public-safe fix-contract follow-up loop lives at
[`../Templates/XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md`](../Templates/XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md).
