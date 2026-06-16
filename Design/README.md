# Public Design Rules

Use the design layer with a strict split:

- cross-cutting public designs -> `AIRoot/Design/`
- public tool-specific or surface-specific designs ->
  `AIRoot/Operations/<ToolOrSurface>/Designs/`
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
> **Imp.** = importance to the system (1–5). **Impl.** = degree of implementation as of 2026-06-16
> (✅ done · 🟡 partial · ⬜ not built · 📦 work delivered, doc is a recipe · 🗄 superseded).
> Reconciled against the real state of `AIRoot/Modules/XUUnity/`, `AIModules/XUUnityInternal/`, and `~/.xuunity/cache/`.
>
> **Review: `xuunity system progress review`, 2026-06-16.** Jump to: [Priority Backlog](#priority-backlog-active-work-by-priority) ·
> [Scoring and Actual Status](#scoring-and-actual-status-review-2026-06-16) · [Archived](#archived) ·
> [Analysis Provenance](#analysis-provenance--review-notes).

Rows are sorted by **priority = importance (desc), then remaining effort (asc)** — most important and
cheapest-to-finish first. `implemented` rows carry housekeeping only. `Effort` is a rough remaining-work
estimate to reach 100% (size · time · complexity); `Left to 100%` names the concrete gap; `Why it matters`
justifies the importance score. Archived docs are in their own table below; for the actionable-only ordering
(excluding done + archived) see the [Priority Backlog](#priority-backlog-active-work-by-priority).

| Design | Status | Imp. | Impl. | Effort (size·time·cx) | Left to 100% | Why it matters (or does not) |
| --- | --- | :---: | --- | --- | --- | --- |
| `AIROOT_PUBLIC_MODULE_ARCHITECTURE_DESIGN.md` | implemented | 5 | ✅ 100% | — done | ✓ Done (2026-06-16): `backup_Apr_12_2026/` removed from the public surface. | Defines the public / host-local / project layering contract the whole repo is built on; every other design assumes this topology — breaking it breaks routing and cross-project sharing. |
| `XUUNITY_SKILLS_SYSTEM_DESIGN.md` | implemented | 5 | ✅ 100% | — done | ✓ Done (2026-06-16): Sudoku `SkillOverrides/README.md` normalized to the canonical template (ApperfunHub keeps its hub variant). | Load-bearing content subsystem: skill families, always-on baseline safety, deterministic trigger routing, token budget, project overrides. The core cannot assemble a correct stack without it. |
| `XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md` | implemented | 5 | ✅ 100% | — done | ✓ Done (2026-06-16): pack example synced to the shipped `usage.md` naming. | Mother design of the paid/private module system: `module/pack/entitlements` contracts, resolver behavior, CLI surface, session integration. Defines the public/private boundary and load order. |
| `XUUNITY_PAID_MODULE_FIRST_PRINCIPLES_FIX_PLAN.md` | implemented | 5 | ✅ 100% | — done | ✓ Done (2026-06-16): P0–P2 marked done; 25-test count recorded. | Sets the commercial + security invariants for paid modules (entitlement-provider contract, license ≠ local flag, redaction boundary, capability tags). Errors here become product and security debt. |
| `XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` | planned | 5 | ⬜ ~5% | S · ~1d · Low | Trim to a thin "policy north-star" after the 3 plans land; drop duplicated level/allowlist/gate detail. | Parent safety policy (allowlist, deny-by-default, runtime-critical denylist, mandatory artifact + human gate) that makes *safe* autonomy possible — the most strategically important unbuilt direction. |
| `XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md` | draft | 5 | 🟡 ~50% | M · ~3–5d · High | `knowledge/execution_contract.md` (single owner) + de-dupe 3 inline copies; `routing_trigger_matrix.md`; `scripts/tests/routing_fixtures/`; pre-patch gate checker. | Lifts routing reliability from prompt-discipline to an enforceable, testable contract. The reliability core and the only path from ~82 to 95+. |
| `XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md` | active | 4 | 🟡 ~75% | S · ~1–2d · Low | Build `protocols/flow_explainer.md` + `delivery_scope.md` (+ note formats), or trim them from the design. | Product-facing protocol layer for PMs/producers (explainers, change impact, rollout readiness, dependency maps). Product-critical, but a layer above the engineering core. |
| `XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md` | planned | 4 | ⬜ ~5% | M · ~2–3d · Med | `knowledge/autonomy_levels.md` (L0–L4) + autonomy hook/fields in `start_session.md`. | The executable L0–L4 ladder (act alone vs. need approval vs. stays human). Operationalizes the parent policy; the concrete next slice. |
| `XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md` | planned | 4 | ⬜ ~3% | M · ~2–3d · Med | `knowledge/low_risk_change_categories.md` (allowlist A–F) + `autonomy_exclusions.md` (denylist). | The allowlist (A–F) + denylist that decides what is *actually* safe. Without it the level model is empty. |
| `XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md` | planned | 4 | ⬜ ~5% | M · ~2–3d · Med | `reviews/autonomy_gate_review.md` + `utilities/autonomy_change_artifact.md` + artifact template (4 gates). | Enforcement mechanism (classification → scope → validation → artifact gates) that gives autonomy teeth and auditability. Inert until levels + categories exist. |
| `AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md` | draft | 4 | 🟡 ~35% | L · ~1–2wk · High | Profiles B/C, CLI flags, `mirror_solution.sh`, `storage_profiles.md` + `router_override_rules.md`, topology health checks, registry fields. | Makes onboarding topology explicit and durable instead of implicit bootstrap guessing; matters for scaling to many repo shapes, but evolves an already-working bootstrap rather than being load-bearing today. |
| `AI_TOOLING_AUTOMATION_DESIGN.md` | draft | 4 | 🟡 ~30% | XL · ~2–3wk · High | Pack B (Jira) + Pack D (GitLab/Bitbucket draft-PR) connectors; then Pack E (orchestration). | The bridge from analysis to execution (Jira/Unity/VCS connectors). High-leverage — turns advice into action — but a layer above the core; the system works without the unbuilt connectors. |
| `XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md` | active | 3 | 🟡 ready | S · operational · Low | Run the loop once ≥3–5 real `xuunity_protocol_incident_*` reports exist; consider relocating to `Operations/`. | An operating-loop tool to evolve the `xuunity fix` contract against real incidents. A meta-tool that only fires once incidents accumulate; not the contract itself. |
| `XUUNITY_EXTERNAL_REPOS_DESIGN.md` | implemented | 2 | ✅ ~80% (dormant) | XS · n/a · Low | None (dormant by design); annotate `external/registry.yaml` re-activation note. | Optional, deliberately dormant capability to promote knowledge to external repos. Peripheral — off by default; value is keeping the door open without committing transport. |

## Priority Backlog (active work, by priority)

What is **active and still needs doing**, ordered by leverage (impact × what it unblocks). `implemented`
docs are intentionally absent (done, reference only), as are `archived` docs (retired). The whole
low-risk-autonomy family is the strategic centre of gravity but is gated behind item 1.

| # | Design | Status · Imp. · Impl. | What is left / next action |
| :---: | --- | --- | --- |
| 1 | `XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md` | draft · 5 · 🟡 ~50% | **Highest leverage — unblocks the autonomy gates.** Build the executable layer: `knowledge/execution_contract.md` as the single schema owner (de-dupe the 3 inline copies in `start_session.md`), `knowledge/routing_trigger_matrix.md`, `scripts/tests/routing_fixtures/`, and a pre-patch gate checker. |
| 2 | `XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md` | planned · 4 · ⬜ ~5% | First autonomy slice: create `knowledge/autonomy_levels.md` (L0–L4) + add the autonomy-level hook/fields to `start_session.md`'s execution contract. |
| 3 | `XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md` | planned · 4 · ⬜ ~3% | Create `knowledge/low_risk_change_categories.md` (allowlist A–F) + `knowledge/autonomy_exclusions.md` (denylist); precondition for any `L2` auto-route. |
| 4 | `XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md` | planned · 4 · ⬜ ~5% | Create `reviews/autonomy_gate_review.md` + `utilities/autonomy_change_artifact.md` + the artifact template (the 4 gates). Implemented last; inert until items 2–3 exist. |
| – | `XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` | planned · 5 · ⬜ ~5% | Parent policy — **not separate build work**: once items 2–4 land, trim this to a thin "policy north-star" and remove the duplicated level/allowlist/gate detail. |
| 5 | `XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md` | active · 4 · 🟡 ~75% | Small gap: build `protocols/flow_explainer.md` + `protocols/delivery_scope.md` (+ `decision_note`/`rollout_note` formats), **or** drop them from the design to match reality. |
| 6 | `AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md` | draft · 4 · 🟡 ~35% | Build profiles B/C (root-only / symlinked), the CLI flags, `mirror_solution.sh`, `knowledge/storage_profiles.md` + `router_override_rules.md`, topology checks in `system_health_review.md`, and the extra `project_registry.yaml` fields. |
| 7 | `AI_TOOLING_AUTOMATION_DESIGN.md` | draft · 4 · 🟡 ~30% | Largest effort, lower urgency: build Pack B (Jira connector) and Pack D (GitLab/Bitbucket draft-PR); Pack E (orchestration) afterwards. Pack A/C already shipped. |
| 8 | `XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md` | active · 3 · 🟡 | **Operational, not design work**: run the follow-up loop once ≥3–5 real `xuunity_protocol_incident_*` reports accumulate. Consider relocating to `AIRoot/Operations/<Surface>/Designs/`. |

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
2. **Active (in force, small gaps to finish):** product protocols (🟡 ~75%), fix-contract follow-up tool (ready, loop not run).
3. **Drafts (in progress, 🟡 30–50%):** root-cause-95, topology bootstrap, tooling automation.
4. **Planned (⬜ ~5%):** the entire low-risk autonomy family (none of the promised autonomy files exist yet).
5. **Archived (`./Archived/`):** four Workstream-3 generator prompts (`historical`) + the upstream-submodule tombstone (`legacy`).

### Implemented (done, source of truth)

These remain the canonical references for current behavior. The four importance-5 docs were taken to 100% on 2026-06-16 (their residual was housekeeping, not a design gap); external repos stays intentionally partial (dormant by design).

- **`AIROOT_PUBLIC_MODULE_ARCHITECTURE_DESIGN.md`** — importance **5**, **✅ 100%**.
  The whole layout follows the contract: `AIRoot` as a submodule (`.gitmodules`), `AIModules/XUUnityInternal/`,
  host-local `AIOutput/{Registry,Reports,Operations}/`, project-local `Assets/AIOutput/ProjectMemory/`.
  *Done (2026-06-16): `backup_Apr_12_2026/` removed from the public surface (deletion staged in the `AIRoot` submodule).*
- **`XUUNITY_SKILLS_SYSTEM_DESIGN.md`** — importance **5**, **✅ 100%**.
  All declared skill families physically exist, plus 2 beyond the design (`refactoring/`, `ui_tweens/`) — 16 family directories total;
  `skills/registry.md` (459 lines), baseline `skills/core/`, routing wired into `tasks/start_session.md`.
  Implementation is broader than the design. *Done (2026-06-16): Sudoku `SkillOverrides/README.md` normalized to the canonical template; ApperfunHub keeps its hub-specific variant (it references the internal overlay).*
- **`XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md`** — importance **5**, **✅ 100%**.
  The mother design of paid modules. All 5 schemas present; `module_registry_tool.py` implements every
  designed command + 5 extra (`route-smoke`, `session-plan`, MCP helpers, `validate-installer`);
  the resolved registry is actually written to `~/.xuunity/cache/resolved_modules/`; `start_session.md` steps 12a–12e;
  topology `AIModules/XCNT-P → _HostLocal/XCNT-P` (symlink) resolves. *Done (2026-06-16): pack example synced to the shipped `usage.md` naming; remains the contract source of truth. The optional `xuunity module` CLI wrapper stays deferred by design.*
- **`XUUNITY_PAID_MODULE_FIRST_PRINCIPLES_FIX_PLAN.md`** — importance **5**, **✅ 100%**.
  P0–P2 confirmed: schema `xuunity.entitlements.schema.json` (provider/trustLevel/license/sync),
  resolver/verifier split, redaction boundary (`outputBoundary: redacted_api`, detector `public_game_qa_path_leak()`),
  capability tags, `reviews/module_pack_review.md`, `validate-installer`. **25 unit tests pass** (`python3 -m unittest` over `scripts/tests/test_module_registry_tool.py`).
  *Done (2026-06-16): P0–P2 marked done in the doc and the 25-passing-test count recorded.*
- **`XUUNITY_EXTERNAL_REPOS_DESIGN.md`** — importance **2**, **✅ ~80% (dormant by design)**.
  Registry skeleton `external/registry.yaml` (`status: disabled_by_default`) + runbooks in `Operations/`.
  Transport and the external repo itself are intentionally not wired — complete for its dormant scope.
  *Rec: `implemented` (dormant); note in registry.yaml that `external/repos/` is created only on re-activation.*

### Active (in force, small gaps)

- **`XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md`** — importance **4**, **🟡 ~75%**.
  6 protocols shipped + 2 beyond plan (`project_health_audit`, `project_memory_freshness`), shorthand routing
  in `start_session.md:424-433`. **Not created**: the planned `protocols/flow_explainer.md` and `protocols/delivery_scope.md`
  (+ `decision_note` / `rollout_note` formats). *Rec: build the missing protocols or drop them from the design. (Backlog #5.)*
- **`XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md`** — importance **3**, **🟡 tool ready, loop not started**.
  The 3-mode prompt template is complete and baseline artifacts are in place (`AIOutput/Reports/System/...`), but the
  operating loop has not run (no real `xuunity_protocol_incident_*` reports). *Rec: run the loop once incidents accumulate; consider moving to `Operations/<Surface>/Designs/`. (Backlog #8.)*

### Drafts (in progress)

- **`XUUNITY_ROOT_CAUSE_ROUTING_95_DESIGN.md`** — importance **5**, draft (newest, Jun 16), **🟡 ~50%**.
  The prose layer is already in production: owner-chain tracing and the execution-contract schema in `start_session.md:244-287`,
  patch-shape taxonomy in `bug_fixing.md:47-90`, `utilities/routing_debug_template.md`, capability gate via
  `module_registry_tool.py session-plan --require-capability`. **The executable layer is not built** (the highest-leverage items):
  no `knowledge/execution_contract.md` (canonical owner — the schema is still duplicated inline, violating the design's own "First Principle 3"),
  no `knowledge/routing_trigger_matrix.md`, no `scripts/tests/routing_fixtures/`, no pre-patch gate checker. *(Backlog #1.)*
- **`AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN.md`** — importance **4**, draft, **🟡 ~35%**.
  There is a topology-first entrypoint `AIRoot/scripts/init_ai_topology.sh` + `host_topology.yaml` write. **Not built**: profiles B/C
  (root-only / symlinked — the doc's main motivation), CLI flags, `mirror_solution.sh`, knowledge files `storage_profiles.md` / `router_override_rules.md`,
  topology checks in `system_health_review.md`, the extra fields in `project_registry.yaml`. *Registry overstated maturity — corrected `active → draft`. (Backlog #6.)*
- **`AI_TOOLING_AUTOMATION_DESIGN.md`** — importance **4**, draft, **🟡 ~30%**.
  Only Pack C (Unity Verification) shipped — a standalone MCP package `Operations/XUUnityLightUnityMcp/` (dozens of `mcp__xuunity_light_unity__*` tools in this session).
  Pack A (portfolio metadata) is partially present (`xuunity system registry refresh` + `AIOutput/Registry/project_registry.yaml` + `Operations/router_storage_audit.py`).
  **Not built**: Pack B (Jira) and Pack D (GitLab/Bitbucket draft-PR); the `xuunity system jira|pr|unity` commands are wired nowhere; Pack E (orchestration) not started. *Registry corrected `active → draft`. (Backlog #7.)*

### Planned — low-risk autonomy family (not started)

**Headline finding:** none of the promised autonomy-specific files exist (`knowledge/autonomy_levels.md`,
`low_risk_change_categories.md`, `autonomy_exclusions.md`, `reviews/autonomy_gate_review.md`,
`utilities/autonomy_change_artifact.md`, the artifact template — all absent). The `L0–L4` ladder exists
**only** in `AIRoot/Roadmaps/AI_AUTOMATION_ROADMAP.md` and is wired into routing nowhere. Only the
**prerequisites** are built (Workstream-3 risk routing + policy packs + generic validation contract), not the autonomy lane itself.

- **`XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md`** — importance **5**, ⬜ ~5%. Parent policy; its `L0–L3` level model is stale (superseded by LEVEL_MODEL_PLAN's `L0–L4`).
- **`XUUNITY_LOW_RISK_AUTONOMY_LEVEL_MODEL_PLAN.md`** — importance **4**, ⬜ ~5%. The correct **"next to implement"** document. *(Backlog #2.)*
- **`XUUNITY_LOW_RISK_CHANGE_CATEGORIES_AND_EXCLUSIONS_PLAN.md`** — importance **4**, ⬜ ~3%. Allowlist (A–F) + denylist; a precondition for `L2` routing. *(Backlog #3.)*
- **`XUUNITY_LOW_RISK_VALIDATION_ARTIFACT_GATES_PLAN.md`** — importance **4**, ⬜ ~5%. The 4 gates; the most code-ready, but implemented last. *(Backlog #4.)*

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

Before this review the registry marked **18 of 19** documents `active` (one `draft`), which masked real
maturity. Reconciled in this update:

1. **5 mature designs:** `active → implemented` (built and remain the source of truth; backlog-free).
2. **4 low-risk autonomy docs:** `active → planned` (really ~5%, not built).
3. **`AIROOT_TOPOLOGY_PROFILE_BOOTSTRAP_DESIGN` and `AI_TOOLING_AUTOMATION_DESIGN`:** `active → draft` (the docs themselves are `draft`, implementation partial).
4. **4 Workstream-3 prompts + `XUUNITY_UPSTREAM_SUBMODULE_DESIGN`:** `active → archived` and physically moved to `./Archived/`.
5. **`XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md`** — was **missing from the registry entirely**; added (its operating loop has not started).
6. **Design self-violation:** the execution-contract schema is duplicated three times inline in `start_session.md` (the step-20b minimum-fields list, the `## Execution Contract` section, and the `## Output` derived-contract block) instead of a single canonical owner — exactly the unmet "First Principle 3" from `ROOT_CAUSE_ROUTING_95`.

### Score by workstream

| Workstream | Maturity |
| --- | --- |
| Foundation (module architecture, skills) | ✅ 100% (implemented) |
| Paid / private module overlay | ✅ 100% (implemented) |
| Risk routing (Workstream-3 policy packs) | ✅ 100% (generators archived) |
| Product self-service (protocols) | 🟡 ~75% (active) |
| Tooling automation (MCP connectors) | 🟡 ~30%, Unity only (draft) |
| Topology / bootstrap profiles | 🟡 ~35% (draft) |
| Root-cause routing → 95+ | 🟡 ~50% — prose yes, executable no (draft) |
| Low-risk autonomy | ⬜ ~5% (planned) |

### Current bottleneck and next step

**Bottleneck:** the system is strong on declarative discipline (prompts / routing) but weak on
**executable gates** — there is no testable routing acceptance layer and no autonomy lane. This is what
blocks the move from "the AI advises well" to "the AI acts safely on its own".

**Recommended next milestone (highest leverage):** close the executable half of
`ROOT_CAUSE_ROUTING_95` (Backlog #1), because it unblocks both routing quality and the autonomy gates.

**Next 3 deliverables:**
1. `knowledge/execution_contract.md` as the **single** owner of the schema + de-duplication of the three inline copies in `start_session.md` (closes "First Principle 3").
2. A first popup/runtime-content fixture in `scripts/tests/routing_fixtures/` + a minimal pre-patch gate checker (clears the `draft` status on ROOT_CAUSE).
3. `knowledge/autonomy_levels.md` + an autonomy hook in `start_session.md` (the first executable slice of the autonomy family — from `LEVEL_MODEL_PLAN`).

## Analysis Provenance & Review Notes

- **Author:** `xuunity system progress review`, 2026-06-16. This pass also introduced the
  `implemented` status, moved 5 retired docs into `./Archived/`, and added the Priority Backlog.
- **2026-06-16 closeout:** the four importance-5 `implemented` designs were finished to 100% —
  `backup_Apr_12_2026/` removed from the public surface, Sudoku `SkillOverrides/README.md` normalized to
  the canonical template, the paid-overlay pack example synced to `usage.md`, and the 25-passing-test
  count recorded in the paid-module fix plan.
- **Method:** `xuunity system progress review` discipline — each design read in full, then cross-checked
  against the live repository by parallel assessors, and the resulting claims adversarially re-verified.
  Implementation claims are backed by concrete files, scripts, schemas, and CLI output (cited inline above),
  not by the documents' self-assessment.
- **Scope of judgement:** the **Importance (1–5)** axis is an opinionated, model-produced scoring and is
  the most subjective column; **Status** and **Implementation %** are evidence-based but were sampled at a
  point in time. The submodule (`AIRoot`) may move independently.
- **For independent review agents:** treat this as a first-pass assessment to be challenged, not ground
  truth. Re-verify each row against the current repo before acting — file paths, statuses, and the `~/.xuunity/cache/`
  contents can drift. Disagreement on the Importance axis is expected and welcome; record dissent rather than silently overwriting.
