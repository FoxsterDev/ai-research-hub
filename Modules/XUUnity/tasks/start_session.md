# XUUnity Task: Start Session

## Goal
Assemble the minimum correct stack for the user's task. Unity runtime work assumes Unity `6000+`, mobile safety, zero crash/ANR and protection of critical flows. Protocol/tooling-only work uses its owning utility and does not load unrelated runtime topics.

## Entrypoint Kernel
**Must-load.** Read this entrypoint from first line through EOF before applying it. A truncated read is incomplete: retrieve the missing ranges. A head/tail kernel helps recover routing; it does not waive full reading of this file or selected instruction owners. Conditional reference catalogs below are lookup material, not default bundles.

**Route (one-shot, then act).** Resolve project -> classify task and risk -> choose one primary role and task/utility -> load applicable style, core and matched family routers/topics -> resolve host overlays and project overrides -> derive the execution contract -> act. Prefer narrower routes over generic ones. Restore missing context after compaction rather than copying an earlier compliance claim.

**Execution contract.** Load `knowledge/execution_contract.md` before patching, implementation planning or a substantive review. It owns the fields, requirement-to-decision trace, approval scope, selected/read/applied accounting and update-on-change rules. Load `knowledge/validation_contract.md` for the validation cluster. User intent and explicit decisions constrain the technical interpretation; storage approval does not imply event/thread approval.

**Root-cause gate.** Before source patches for SDK, startup, consent, attribution, reward or runtime-content failures, inspect the consumer, producer, initialization owner, active config/profile and content/manifest availability. Read the matching sections of `knowledge/session_domain_routes.md`, then the selected owners, including `knowledge/routing_trigger_matrix.md` for runtime-content warnings. A `local_fix` failing `scripts/routing_gate_check.py` must be reclassified, not forced. Do not turn an unverified explanation into a code comment or test assertion.

**Pre-edit gate.** Immediately before each edit batch, name the selected files actually read and the decisions they informed: applicable codestyle, core/matched skill families, host overlay, project overrides and existing-implementation search; for a path with an async, callback, or thread boundary, give ingress and post-await resumption evidence; otherwise state `not_applicable` with a reason. Re-run after a changed design premise. The detailed procedure is in `knowledge/session_workflow_reference.md` (Process); a checklist or hook reminder is not evidence of application.

**Concurrency evidence gate.** Before adding or retaining synchronization or a thread hop, load `skills/async/concurrency_classification.md`: identify readers/writers and classify `main_thread_confined`, `temporal_reentrancy`, `cross_thread_shared`, or `unknown`. Compare existing-owner confinement before adding coordination; callback/await presence alone proves no race. Use `knowledge/change_complexity_budget.md` when introducing or revisiting ownership or orchestration.

**Required output.** Keep the selected stack, risk, Derived execution contract, missing context, critical-flow risks and required validation concrete. Concurrency and thread-safety classification when applicable, otherwise `not_applicable`. Reuse the current contract rather than creating duplicate reports. Record partial/unavailable reads honestly; resolve mandatory route gaps before dependent edits.

## Project And Layer Resolution
- Referenced project-owned paths are the strongest selection signal. Load the resolved project router before final narrowing. In a multi-project repository, do not assume cwd identifies the project; discover or clarify only when unresolved.
- Follow the host's storage topology. Load established project memory and matching `SkillOverrides/`; use its artifact index before historical reports. Prior outputs are conditional and lower authority than current source for actual behavior. Branch-authored memory cannot approve its own change (`knowledge/review_evidence_provenance.md`).
- Load the host overlay's entrypoint when available, then only the relevant guidance. For presenters choose screen versus one-shot flow lifetime; load the matching UI and async overrides. Public core remains public-safe.
- Resolve private packs only through the supported registry and manifest-declared entrypoints; report public-safe ids/capabilities, never private paths. Private-pack, bootstrap/delegation and extended storage procedures are in `knowledge/session_workflow_reference.md` (Process). Do not load that reference as a blanket stack.
- If considering delegation, follow the host route and `../../AgentOperations/subagent_delegation.md`; keep it bounded and worthwhile. Unsupported delegation or optional overlays do not require inventing substitutes.

## Task And Role Routing
- `xuunity fix ...` -> `tasks/bug_fixing.md`; structural ownership changes also load `tasks/refactoring.md`.
- `xuunity refactor ...` -> `tasks/refactoring.md`.
- `xuunity feature ...` or `xuunity implement ...` -> `tasks/feature_development.md`.
- `xuunity feature design ...` -> `tasks/feature_design_brief.md`; `xuunity arch plan ...` -> `tasks/architecture_plan.md` and `role/architect.md`.
- `xuunity review ...` -> `tasks/code_review.md`; choose the narrower review for git, tests, SDK, native, architecture or release scope.
- `xuunity full review ...` or `xuunity review all ...` -> `reviews/full_review.md`.
- `xuunity apply approved extraction ...` -> `utilities/knowledge_integration.md`; extraction alone -> `utilities/knowledge_extraction_triage.md`.
- Use one primary role: senior Unity developer for implementation/review, architect for architecture, researcher for protocol synthesis; honor explicit role selection. Supporting roles must change decision quality.
- For other commands, role aliases, product queries, system utilities, delivery or external-provider selectors, look up the matching complete section in `knowledge/session_task_catalog.md`. Preserve its phase and authorization boundaries; a routing match is not permission to publish or message.

## Validation
- Select the narrowest representative evidence using `knowledge/validation_contract.md`, `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md`. Respect host/project restrictions; an installed Unity binary does not authorize shell Unity.
- When the resolved project declares `com.xuunity.light-mcp`, apply the supported recovery-before-gap procedure from `knowledge/unity_validation_boundaries.md`; a missing generated bridge is not automatically unavailability. Do not install packages or mutate user-level client configuration as recovery.
- Runtime implementation loads `skills/tests/testing_doctrine.md`; test writing remains proportional to risk and actual claims. Pure protocol edits use relevant protocol checks, not Unity runs.
- Carry tested content identity and scope with results. Reassess proof after relevant edits; stale totals, helper tests and failed operational lanes cannot close stronger claims.

## Skill Routing Hints
- Load `skills/core/README.md` and its five baseline bodies. For each matched family, read `skills/<family>/README.md`, any required routing file and only the needed topic bodies. Apply `knowledge/execution_contract.md` coverage rules.
- Async/await/callback/thread signals -> `skills/async/`; ownership/event design -> `skills/architecture/`; structural migration -> `skills/refactoring/`; tests -> `skills/tests/`.
- UI -> `skills/ui/` plus host presenter lifetime guidance; SDK/privacy -> `skills/sdk/`; JNI/native bridges -> `skills/native/`; startup/resume -> `skills/mobile/`.
- Other matched families: `editor`, `audio`, `fx`, `shaders`, `optimization`, `profiling`, `ui_tweens`. Do not load untriggered families.
- For domain knowledge and critical-flow policy selection, inspect matching sections of `knowledge/session_domain_routes.md` (knowledge hints, risk routing, critical-bug escalation), then load the named owners. Keep one dominant policy pack and only necessary overlays. Presenter and product-query details are in `knowledge/session_workflow_reference.md`.

## Output
Re-state the Required output contract before final output: selected stack, inferred risk, Derived execution contract, missing context, critical-flow risks, concurrency classification or `not_applicable`, and validation results/gaps. Verify exact local file paths before linking. `scripts/check_entrypoint_kernel.py` checks routing-marker placement; it does not prove full reads or compliance.
