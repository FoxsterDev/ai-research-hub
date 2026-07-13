# AI Automation Roadmap — Feature Gap & Milestone Status

**Type:** Principal review (roadmap progress + gap analysis)
**Date:** 2026-07-12
**Scope:** `Roadmaps/AI_AUTOMATION_ROADMAP.md` + `AI_AUTOMATION_EXECUTION_PLAN.md` vs. the current shipped capability surface of the `AIRoot` public module.
**Method:** parallel capability readers over the real files → mapping of all 7 roadmap phases, 7 execution-plan workstreams, and the 12 named "build first" deliverables → adversarial re-verification of every *done / mostly-done* claim (each verifier re-read the source files with a skeptical default). **19/19 completion claims held up; 0 over-claims survived.**

> **Public-module note.** This is a public-safe snapshot. Host-portfolio specifics (project names, per-project counts, host registry contents) are intentionally generalized here; the authoritative, host-specific version lives in the attached host repo under its own `AIOutput/Reports/`. `AIRoot` must not carry host-private state — see `MISSION.md`.

---

## 1. Headline

The execution plan was an **8–12 week** program. **The bulk of it is shipped and holds up under adversarial verification.** Of the two roadmap tiers:

- **Phases 1, 3, 4 are done. Phase 5 is mostly done. Phases 2 and 7 are partial. Phase 6 is designed but not built.**
- **Workstreams 1, 2, 3, 5 are done. WS4 is mostly done (one format nit). WS6 and WS7 are partial.**
- **11 of the 12 "build-first" deliverables are done; #8 (host registry richness) is partial.**

The single largest remaining milestone is the **Low-Risk Autonomy lane (Phase 6 / Workstream 7)**: it is **design-complete** (four detailed design/plan docs, full `L0–L4` model, change categories, exclusion families, four-gate pre-merge artifact contract) but has **zero runtime implementation** — no autonomy protocol files exist in `Modules/`, `grep autonomy` over the shipped tree returns nothing, and the task-registry governance surface is not autonomy-aware.

**A secondary, important finding: the roadmap documents themselves are stale.** They are essentially unchanged since the init commit while the deliverables were built out over the following weeks. The roadmap's "Immediate Next Moves" and "Concrete Deliverables To Build First" read as pending, but all but one are complete. The roadmap should be re-baselined (see §6).

---

## 2. Status Legend

| Status | Meaning |
|---|---|
| ✅ **Done** | Delivered as a real, wired, non-stub capability; satisfies the stated definition-of-done. |
| 🟢 **Mostly done** | DoD substantially met; one minor/format gap to close. |
| 🟡 **Partial** | A real foundation exists but named sub-capabilities are missing. |
| 📐 **Designed, not built** | Specified in `Design/`, no runtime artifacts. |
| ⬜ **Not started** | No design and no implementation. |

---

## 3. Milestone Status — Roadmap Phases

| Phase | Title | Status | Basis |
|---|---|---|---|
| 1 | Strong Foundation | ✅ Done | Multi-hundred-line session router, full XUUnity task/knowledge/review/product families, ~18-category skill system + `skills/registry.md`, wired knowledge intake→review→merge chain, opt-in external extension (`apiBilling:forbidden`, disabled metered stub). Every routed project has a usable router + `ProjectMemory/`. |
| 2 | Portfolio Standardization | 🟡 Partial | Health-audit + memory-freshness protocols are mature. **Missing:** automated project bootstrap, onboarding checklist, minimum project-memory templates, and a *persisted* per-project AI-readiness score (registry only carries an `ai_baseline_status` enum). Health/freshness are on-demand prompts, not automated pipelines. |
| 3 | AI-Guided Delivery Flows | ✅ Done | Full chain: `feature_request_intake → feature_design_brief → implementation_plan → validation_plan → rollout_plan → feature_development → change_delivery`, plus `delivery_risk_review`. Wired to memory, skills, code-verification lanes, and reviews. |
| 4 | Policy-Driven Review | ✅ Done | All six change-type policy packs; `full_review.md` auto-assembles the review stack by risk family via a Deterministic Bundle Matrix + a Bundle Rationale Contract; `release_readiness_review` gate; backed by `risk_classification` + `severity_matrix`. |
| 5 | Product Owner Self-Service | 🟢 Mostly done | 8 product protocols, standardized response format with 3–4 verification-status labels, plain-language command guide wired through `start_session`. **Gap:** no per-role / project-side quickstart (one combined host-level guide + a compatibility-alias stub). |
| 6 | Semi-Autonomous Implementation | 📐 Designed, not built | Full `L0–L4` ladder + categories + gates specified across 4 `Design/` docs. **No runtime capability:** target protocol files absent, no `start_session`/`execution_contract` hooks, task-registry not autonomy-aware. `Design/README.md` self-rates the family ~3–5% built. |
| 7 | Portfolio Orchestration | 🟡 Partial | A real, populated project-registry index + maintenance procedures exist. **Missing:** richer metadata dimensions, cross-project health dashboard, capability matrix, knowledge-promotion analytics, shared incident-pattern tracking. |

---

## 4. Milestone Status — Execution-Plan Workstreams

| WS | Title | Priority | Status | Definition-of-Done result |
|---|---|---|---|---|
| 1 | Project Health & Freshness | Highest | ✅ Done | `project_health_audit` (scoring engine, 7 areas, 0–5, 4 bands) + `project_memory_freshness` (code-vs-memory drift, freshness classes) + report template; both wired as one-command entries in `start_session`. |
| 2 | Feature Delivery Protocols | Highest | ✅ Done | All 6 protocols exist as full contracts; repeatable request→implementation-ready-brief pipeline; "why this review stack" is answerable via `full_review` Bundle Rationale Contract. |
| 3 | Risk Routing & Policy Packs | Highest | ✅ Done | 4 risk classes; all 6 policy packs (Trigger When + Mandatory Stack); `start_session` Risk Routing Hints + Critical Bug Escalation auto-load stronger stacks and surface the trigger. |
| 4 | Product Owner Self-Service | High | 🟢 Mostly done | 6 expanded protocols + standard format + PO command guide, all wired. **One deviation:** `risk` is not a named section in `product_summary_format.md` (it lives per-protocol). |
| 5 | Review Artifact Pipeline | High | ✅ Done | `review_artifact_extract` + `review_artifact_merge` finalized; storage delegated to `report_export` → host `AIOutput/Reports/ReviewArtifacts/`; connected to `knowledge_intake_review` approval gate → `knowledge_integration`. |
| 6 | Portfolio Registry | Med-High | 🟡 Partial | The registry is genuinely populated for all routed projects. **3 of 6 required metadata dimensions present** (type, platform, memory status); **monetization stack, numeric AI-readiness score, and critical flows are absent**; index/report half is a stub; the co-located validator does not validate the project registry and its project list is out of sync with it. |
| 7 | Low-Risk Autonomy Lane | Medium | 🟡 Partial (📐 design-complete, ⬜ implementation) | 4 design docs fully specify the model, categories, exclusions, and gates. **No executable implementation, no runtime wiring, no gate that fires.** |

---

## 5. Milestone Status — 12 "Build First" Concrete Deliverables

| # | Deliverable | Status |
|---|---|---|
| 1 | `product/protocols/project_health_audit.md` | ✅ Done (full scoring engine) |
| 2 | `product/protocols/project_memory_freshness.md` | ✅ Done |
| 3 | `tasks/feature_request_intake.md` | ✅ Done (loose bare-filename cross-refs only) |
| 4 | `tasks/feature_design_brief.md` | ✅ Done (5-field validation contract) |
| 5 | `tasks/implementation_plan.md` | ✅ Done |
| 6 | `reviews/delivery_risk_review.md` | ✅ Done (stack rationale lives in `full_review`) |
| 7 | `knowledge/risk_classification.md` | ✅ Done (class→stack binding intentionally deferred, not tabulated) |
| 8 | host registry file in `AIOutput/Registry/` | 🟡 **Partial** (populated but skeleton metadata; report + validator gaps) |
| 9 | execution-contract hardening in `tasks/start_session.md` | ✅ Done — **verified by running `check_entrypoint_kernel.py` (exit 0)** |
| 10 | bug-fix closure hardening in `tasks/bug_fixing.md` | ✅ Done (Closure Discipline + structured Output + Patch Shape Classification) |
| 11 | complexity-budget hardening in `tasks/bug_fixing.md` | ✅ Done (`## Complexity Budget`, contract-freeze + net-simplification default) |
| 12 | deterministic verification mapping in `tasks/bug_fixing.md` | ✅ Done (`## Verification Policy`, per-shape + per-family mapping) |

---

## 6. Feature Gap Register (prioritized)

Gaps that block a *named* roadmap capability, ranked by leverage. "Effort" is rough.

### P0 — the frontier milestone

**GAP-1 · Low-Risk Autonomy lane is designed but unbuilt (Phase 6 / WS7).**
This is the next real milestone and the one place where documentation could create false confidence that governance is enforced when it is not.
- No `knowledge/autonomy_levels.md`, `knowledge/low_risk_change_categories.md`, `knowledge/autonomy_exclusions.md`, `reviews/autonomy_gate_review.md`, `utilities/autonomy_change_artifact.md`.
- No autonomy hook/fields in `tasks/start_session.md` or `knowledge/execution_contract.md`.
- The task-registry surface (`task_registry_append/validate/rollup`, `task_event_schema`) has no `autonomy_level` / `allowlist_category` / `human_gate` fields — the "artifact + validation before merge" gate cannot fire.
- The parent `Design/XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` predates the ladder — only `L0–L3`, no `L4`; needs reconciliation with the `LEVEL_MODEL_PLAN`.
- **Action:** convert the three plan docs into the five runtime files, add autonomy fields to the execution contract + task-registry schema, wire a self-classification step into `start_session`, and reconcile the parent design to `L0–L4`. *Effort: medium-high.*

### P1 — real defects / half-built capabilities

**GAP-2 · Registry validator drift (correctness bug). ✅ Fixed 2026-07-12.** The registry validator script validated a *different* co-located registry, **not** the project registry, and its hardcoded project list was **out of sync** with the registry (fewer entries than registered projects) — silent under-coverage. *Resolution: the in-scope project roots are now derived from the project registry unioned with on-disk projects (no hardcoded list; can't drift), and the validator now also checks the project registry's own invariants (each project's path, router file, and project-memory path must exist; warns on `has_game_observer` mismatch).*

**GAP-3 · Portfolio index/report is a stub (WS6 / Phase 7 DoD). ✅ Fixed 2026-07-13.** No command produced a portfolio health/readiness report. *Resolution: added the reusable, host-agnostic tool `AIRoot/Operations/project_registry_report.py` — it renders a portfolio status report from a project registry and computes a structural readiness score per project, with `--write-back` (persists `ai_readiness_*`) and `--json`. It is config-driven: which on-disk signals, report columns, and completeness dimensions define readiness come from a host-supplied rubric (`--rubric`), so the public tool carries no host or project specifics; without a rubric it uses a neutral default (router + project-memory presence).*

**GAP-4 · Registry metadata skeleton (WS6, deliverable #8). ✅ Fixed 2026-07-13.** The registry was missing 3 of 6 required dimensions (monetization stack, numeric AI-readiness score, critical flows). *Resolution: sourced per-project metadata from real project files (each project's package manifest + project memory) and enriched the registry with an evidence-backed `monetization_stack` and `critical_flows` per project; `ai_readiness_*` is materialized by the report tool. Any portfolio-wide shared SDK baseline is documented once in the host internal knowledge layer rather than repeated per entry. All 6 metadata dimensions are now present for every project.*

**GAP-5 · Phase 2 standardization primitives absent.** No automated project **bootstrap**, no **onboarding checklist**, no **minimum project-memory templates**, and no *persisted* per-project readiness score. Health/freshness exist but are on-demand, not a portfolio-wide automated pass. *Action: add a bootstrap protocol + memory template + checklist; schedule/persist readiness scores into the registry (couples with GAP-4). Effort: medium.*

**GAP-6 · Phase 7 orchestration analytics unbuilt.** No cross-project health **dashboard**, **capability matrix**, **knowledge-promotion analytics**, or **shared incident-pattern tracking**. (These are later-phase by design; flagged for completeness.) *Effort: high.*

### P2 — consistency / polish (non-blocking)

- **GAP-7 · WS4 format:** add a `risk` line to `product/output/product_summary_format.md` (risk currently only per-protocol). *Effort: trivial.*
- **GAP-8 · Uneven policy-pack severity:** `sdk_changes`, `startup_changes`, `manifest_native_changes` delegate severity to `severity_matrix.md`; the other three carry in-pack Release-Risk Framing. Normalize. *Effort: low.*
- **GAP-9 · `routing_trigger_matrix.md` under-documents the delivery chain:** none of the 7 delivery nodes are enumerated (they route via `start_session` command grammar). *Effort: low.*
- **GAP-10 · Loose cross-refs:** `feature_request_intake` / `feature_design_brief` cite `project_memory_freshness.md` / `project_health_audit.md` by bare filename though they live in `product/protocols/`. Files exist; refs are non-broken. *Effort: trivial.*
- **GAP-11 · `knowledge_merge.md` is thin** (no target-file map) vs `skill_merge.md` — weakest link if used standalone as the shared-knowledge executor. `skill_merge.md` also has a duplicated Process step number "5". *Effort: low.*

---

## 7. Over-Delivery — Capabilities Beyond the Roadmap

The system has shipped substantial capability the roadmap never named. This should be folded into an updated roadmap so it stops being "invisible" work:

- **XUUnity Light Unity MCP** — a shipped file-IPC Unity editor bridge (compile/play/scene/scenario/screenshot validation), with its own design/roadmap/smoke contract and a `com.xuunity.light-mcp` package. This is the concrete backbone behind the "code-verification" lanes the delivery protocols reference.
- **Knowledge-extraction eval harness** — an evaluation script + golden cases (YAML/JSON) + an authoritative-approval checklist. A real quality-measurement loop for the intake pipeline.
- **AIReferenceWatch module** — reference-selection doctrine + feature-bag extraction/comparison prompts (competitive/reference watch).
- **CLI orchestration** — `XUUnityAiCliOrchestrator` + `ai_cli_orchestrator.md` (opt-in, billing-forbidden by default).
- **Ops surfaces** — an OpenSearch prod-health pulse, a Slack delivery MCP, MD→HTML / MD→PDF report export, and a published docs site under `docs/`.
- **Bug-fix execution rigor** — Patch Shape Classification (6 shapes), Complexity Budget, deterministic Verification Policy, kernel-invariant checker script — richer than the roadmap's "bug-fix hardening" line implied.

---

## 8. Roadmap Hygiene Recommendation

The roadmap and execution plan should be **re-baselined** to reflect reality:

1. Mark Sprints 1–4 (WS1–WS5) **complete**; the "Immediate Next Moves" (1–6) and "Concrete Deliverables To Build First" (all except #8) are **done**.
2. Rewrite the frontier as: **(a)** implement the autonomy lane (GAP-1), **(b)** finish registry richness + portfolio report (GAP-2/3/4), **(c)** Phase-2 standardization primitives (GAP-5), then **(d)** Phase-7 orchestration analytics (GAP-6).
3. Add the §7 over-delivered surfaces so MCP, eval harness, and ops tools are tracked capabilities, not shadow work.
4. Keep this gap register as the living checklist; refresh the progress-review cadence.

---

## 9. Recommended Next Moves (reprioritized)

1. **Implement the autonomy lane** — the only fully-designed, zero-built milestone; highest strategic leverage. (GAP-1)
2. **Fix the registry validator + sync project list** — small, real correctness bug. (GAP-2)
3. **Build the portfolio index/report + fill registry metadata** — unlocks the Phase-7 foundation and persists AI-readiness scores. (GAP-3, GAP-4)
4. **Add Phase-2 standardization primitives** — bootstrap, checklist, memory templates; makes "onboard under one day" real. (GAP-5)
5. **Sweep the P2 consistency gaps** in one pass (GAP-7…11) — cheap, raises baseline coherence.
6. **Re-baseline the roadmap docs** (§8).

---

*Verification note:* every "done"/"mostly-done" milestone above was independently re-read against the roadmap's own definition-of-done by a skeptical verifier; deliverable #9 was additionally confirmed by executing `check_entrypoint_kernel.py` (exit 0). No completion claim was found to be overstated. Runtime/behavioral success metrics (e.g. "short commands work consistently") are not file-provable, but all supporting mechanisms are present and non-stub.
