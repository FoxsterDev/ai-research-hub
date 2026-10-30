# XUUnity Session Reference: Session Workflow Reference

Conditional reference extracted from `tasks/start_session.md`. All paths are module-relative unless explicitly host/project-qualified. This is not an always-loaded entrypoint or a new policy layer. Look up the complete matching sections, then read the selected instruction owners in full. The compact entrypoint owns the mandatory route and `knowledge/execution_contract.md` owns requirement/read accounting.

## Contents
- Process
- Shared Layer Rules
- Monorepo Project Resolution
- Internal Overlay Routing Hints
- Execution Contract
- Default Working Posture
- Product Query Rules

## Process
1. Classify the task from the user request, even if the request is shorthand.
1a. Resolve the target project from referenced local source paths before role and stack assembly.
1b. If all referenced local source paths fall under one project root, treat that project as resolved immediately.
1c. If the repo contains multiple Unity projects and no concrete target project can be resolved, do not assume the current workspace root is the target project; ask for clarification or perform minimal project discovery first.
1d. If the target project is resolved, load that project's router before final stack narrowing.
1e. If this is the first `xuunity` request for a new agent or project and the agent supports durable private memory, load `knowledge/agent_source_of_truth.md` and use `utilities/agent_private_bootstrap.md` to install or refresh a thin agent-private router before continuing. If unsupported, continue normally and record the gap only when relevant.
1f. Perform one cheap delegation check: identify a routine lane only when its algorithm, inputs, allowed mutations, expected outputs, and stop conditions are already exact and it can run independently while the root agent does useful work. If no such lane exists, do not load delegation guidance and continue normally.
1g. When a routine lane exists, load `../../AgentOperations/subagent_delegation.md`, apply the host router's model choice, and create its complete task packet before spawning. Any unexpected result is `needs_smart_escalation`; the routine subagent stops and returns evidence instead of diagnosing or fixing it.
2. Detect whether the user requested a specific role.
3. If no role was requested, infer the best primary role from the task type and risk profile.
3a. Infer whether the task needs explicit risk classification and policy-pack routing.
3b. If the task touches SDK initialization, consent sequencing, attribution identity, ad revenue reporting, reward integrity, startup ownership, or third-party wrapper code, require root-cause tracing before proposing a source-level fix.
3b-i. If a runtime warning or exception stack crosses feature startup, a flow or presenter, an async service, a remote asset/content service, SDK/service initialization, or build/runtime config, classify the task at minimum as `bug_fixing` with `startup/config ownership` as an overlay. Do not keep it as a local UI, local presenter, or local service bug only.
3b-ii. For those runtime warnings or exceptions, a source patch is blocked until the consumer, producer, initialization owner, active config/profile, and content or manifest availability have been inspected and recorded in the compact execution contract.
3c. If investigation or the patch plan shows that a bug-fix task will move ownership between layers or introduce non-trivial state orchestration such as queues, flush paths, cache fallbacks, helper wrappers, or duplicated triggers, keep `tasks/bug_fixing.md` as the primary task but also load `tasks/refactoring.md` as a behavior-preserving overlay.
4. Decide whether the task needs one role or a small role group.
5. Select the primary role file and only the minimum useful supporting role files.
6. Select one or more relevant files from `codestyle/`.
7. Load baseline safety skills from `skills/core/`.
8. Infer and load only the relevant task-specific skill packs from `skills/`.
8a. For any implementation task such as bug fixing, refactoring, feature development, SDK work, or native-plugin work, always load the testing baseline:
  - `skills/tests/testing_doctrine.md`
  - the narrowest additional files from `skills/tests/` only when the task or planned validation actually needs them
8b. Treat the testing doctrine as a default development constraint, not only as a review-time reference. Any new tests authored during the session must follow it.
8c. Do not assume that tests must always be written.
  - Prefer writing tests near the end of the implementation after the production shape is stable enough to test.
  - If test writing is optional or materially expensive relative to the task, ask the user whether they want tests instead of spending large token budget by default.
  - If tests are clearly required by risk, regression surface, or an explicit user request, state that briefly and proceed.
9. Select one task file.
10. Add only the review, utility, and platform files required.
10a. Add root-level `knowledge/` files only when a concrete routing hint or the selected task or review requires them.
10b. If the task is risk-sensitive, load only the minimum matched policy-pack files from `reviews/policy_packs/` and surface the trigger reason explicitly.
11. If the host repo provides `AIModules/XUUnityInternal/`, load only the minimum relevant internal shared overlay files after the public `XUUnity` core.
11a. When a host-local internal overlay exists, prefer starting from its host-local overlay entrypoint before loading narrower internal files.
12. When the task touches internal presenter-driven UI, choose the narrowest internal UI skill by lifetime shape (these live in the host internal overlay at `AIModules/XUUnityInternal/skills/ui/`, not the public core, and load only when that overlay exists):
   - internal `skills/ui/screen_presenters.md` for long-lived screens, tabs, pages, or root screen composition
   - internal `skills/ui/flow_presenters.md` for one-shot popups, modal flows, or explicit flow-result presenters
   - internal `skills/ui/presenter_development.md` only as the lifetime-map entry file or when the task spans more than one presenter shape
12a. Resolve optional private/paid module overlays before project memory when the user asks for private modules, paid packs, premium skills, Game QA paid validation, or when a known loaded private-pack trigger matches the task. If `scripts/module_registry_tool.py` exists, prefer the latest user-cache registry from `~/.xuunity/cache/resolved_modules/`; run `python3 Modules/XUUnity/scripts/module_registry_tool.py rollsync --project-root <host-root>` when the cache is missing, stale, or the user explicitly asks to verify loading.
12b. Treat the resolved registry as a user-local overlay contract:
   - use `loadedPacks[]` as eligible prompt-stack candidates
   - use `lockedPacks[]` and `invalidPacks[]` only to explain why a pack cannot be used
   - never write resolved private-pack paths or manifests into the project repo
   - never load private pack files by guessing paths outside the registry
   - load only the entrypoints declared by the matched loaded pack
12c. Match `loadedPacks[].routing.triggers` against the current task text after public-core and internal-overlay routing have narrowed the stack. Public routing may also require a stable capability tag with `session-plan --require-capability <capability-id>`. If a loaded private pack matches by trigger or required capability, add only its manifest-declared entrypoints and record the pack id in `matched_private_packs` inside the execution contract.
12d. For Game QA paid work, prefer a loaded private pack that provides capability `xuunity.game_qa.runtime_ui_validation` or `xuunity.game_qa.playmode_smoke_planning`. Load it through the registry paths rooted at the resolved private module, not through public `Modules/XUUnity` paths. Local smoke tests may still assert canonical pack id `xcntp.game_qa_paid_skill`; public policy should route by capability first. If no matching pack is loaded, or the pack is locked or invalid, state the gap and continue with public validation planning instead of silently degrading into non-registered private content.
12e. When `scripts/module_registry_tool.py session-plan` is available, use it as the preferred private-runtime session-routing proof. Copy only its public-safe `sessionContract` fields into planning, reports, or project output; do not copy private entrypoint paths or private pack bodies into company/public artifacts.
13. Load project memory before using previous outputs.
14. Check `Assets/AIOutput/ProjectMemory/SkillOverrides/` for matching local overrides.
15. For gameplay projects, load durable guidance from `Assets/AIOutput/ProjectMemory/` by default.
16. Do not load historical reports from `Assets/AIOutput/` by default.
17. Load historical reports from `Assets/AIOutput/` only when the task is investigating behavior drift, reconstructing legacy intent, or researching old bug root causes.
18. If historical reports are loaded, keep them lower-priority than current-truth memory and current source code.
19. Identify whether the task touches shared state, async flows, native boundaries, startup, UI, rendering, loading, monetization, or other critical project flows.
19a. If the task touches cache design, persistence shape, startup override, fallback state, or remote-config application, derive the minimal product contract before implementation:
  - source count
  - persistence unit
  - merge boundary
  - partial-update semantics
  - compatibility envelope
  - platform storage backend
19b. For cache, persistence, startup override, or remote-config tasks, prefer the smallest architecture that satisfies the derived product contract and restate that contract before broader implementation if redesign churn appears.
20. Decide the safest implementation shape before writing code.
20a. Before implementation, review, or planning output is finalized, derive the compact execution contract for the session. `knowledge/execution_contract.md` is the single owner of the field set, field meanings, and contract rules (brevity, `none` instead of omitting, update-on-change, `required_validation` derivation for `tasks/bug_fixing.md`, and `required_self_review` obligations). Reference the owner instead of re-listing the fields here.
20b. Apply the Pre-edit gate from the Entrypoint Kernel in `tasks/start_session.md` here, before the first `Edit`/`Write` call: confirm the skill-loading steps above (6-11) were actually followed for this task, not only the router/entrypoint files — in particular that `AIModules/XUUnityInternal/` and any matched `skills/` family were checked for an existing pattern or implementation before writing a new one. Loading a file earlier in the session is not the same as having applied it here; if step 6-11 was skipped for time pressure, do it now before the first edit, not after a defect surfaces.
21. If the task depends on validation, confirm whether the available tool path is representative for a Unity project before running it; if not, avoid defaulting to substitute shell-driven validation and plan for an explicit validation gap.
22. Do not treat the mere presence of a Unity binary or CLI entrypoint as proof that direct shell-launched Unity validation is allowed for the current repo.
22a. If the project exposes a supported Unity MCP path, treat that MCP path as the default Unity-aware validation surface.
22b. When Unity MCP is available for the project, do not start with direct Unity CLI, `-batchmode`, `-runTests`, `-executeMethod`, or shell-side generated-project compile as the primary validation route.
23. Before running Unity via shell, batchmode, `-runTests`, `-executeMethod`, or similar editor automation, check host-local overlays, project routers, and project memory for validation-path constraints.
24. If a host-local or project-local rule requires Unity validation to go through MCP or another repo-specific integration, treat that as a hard must-not for direct shell-launched Unity and do not fall back to the CLI.
24a. When validation needs live evidence beyond source inspection, choose a primary validation lane before running tools:
  - `interactive_mcp`
  - `batch_compile`
  - `scenario`
24b. Use `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md` as the canonical lane and evidence doctrine instead of re-deriving lane rules ad hoc inside the session.
24c. Keep the session-level lane reminder compact:
  - `interactive_mcp` for integrated editor evidence
  - `batch_compile` for compile, matrix, and approved build-sensitive artifact proof
  - `scenario` for ordered runtime evidence
24d. Set the validation-contract fields using the exact schema from `knowledge/validation_contract.md`.
24e. If no permitted lane can produce representative evidence, or if the chosen lane cannot provide trustworthy final accounting, keep the validation gap explicit instead of silently weakening the proof target.
24f. When opening Unity for MCP-backed validation, resolve the Unity editor version from the target project's `ProjectSettings/ProjectVersion.txt` instead of defaulting to the latest installed editor.
25. Before emitting a clickable local file link, verify the exact absolute path that exists in the active workspace.
26. If the exact absolute path is not verified, prefer plain text paths over markdown file links.
27. For Rider-oriented links, only emit markdown file links when the file exists at the emitted absolute path.
28. For Rider-oriented links, prefer linking to the file path without a `:line` suffix and mention the line number separately in prose when needed.

Default storage references in this file assume the standard project-local layout.
If the active repo router, project router, or project registry declares a different storage mode, follow that host-local contract first and translate legacy `Assets/AIOutput/...` paths accordingly before loading project memory, skill overrides, or prior outputs.


## Shared Layer Rules
- Treat `AIRoot/Modules/XUUnity/` as the public-safe default core for `xuunity`.
- Treat `AIModules/XUUnityInternal/` as an optional monorepo-internal overlay, not as a replacement for the public core.
- Load internal overlay files only when they materially improve the current task.
- If a host-local internal overlay provides its own routing entrypoint, prefer that entrypoint over ad hoc direct loading of narrow internal files.
- When public core and internal overlay differ, follow the internal overlay for monorepo-specific behavior unless established project memory overrides both. In a change review, memory added or modified by the target is candidate evidence under `knowledge/review_evidence_provenance.md` until independently approved.
- Do not load broad internal overlay files when a narrower lifetime-specific UI skill exists.


## Monorepo Project Resolution
- In a multi-project Unity monorepo, referenced local source paths are the strongest project-selection signal.
- If the request references one or more files under a single project root such as `<Project>/Assets/...`, `<Project>/Packages/...`, or another project-owned source subtree, treat that project as the active target project immediately.
- When the target project is resolved from source paths, load that project's router and project memory before final role, skill, and review narrowing.
- Do not remain on repo-generic `xuunity` routing when a concrete project path already identifies the project.
- If referenced local paths span more than one project root, ask for clarification instead of guessing.
- If no project can be resolved in a multi-project monorepo, prefer one short clarification question over a repo-generic implementation proposal.


## Internal Overlay Routing Hints
- If a host-local overlay declares UI guidance and the task is about a long-lived screen, tab, lobby page, or page-composition presenter, prefer the host-local screen-presenter guidance.
- If a host-local overlay declares UI guidance and the task is about a popup, modal, temporary flow, wizard-like interaction, or presenter that returns an explicit flow result, prefer the host-local flow-presenter guidance.
- If a host-local overlay declares UI guidance and the task is about choosing between presenter lifetime shapes, extracting presenter patterns, or refactoring the boundary between scene roots and presenters, also load the host-local presenter-development guidance.


## Execution Contract
- Derive and surface the compact execution contract before patching, large review output, or implementation planning.
- `knowledge/execution_contract.md` is the single owner of the field set, field meanings, and contract rules; its validation cluster is owned by `knowledge/validation_contract.md`. Reference the owner instead of copying the field list.
- Use `utilities/routing_debug_template.md` when the user asks for routing/start-session debug, when private-pack loading must be accounted for, or when root-cause gating blocks a local patch and the loaded stack must be made explicit.


## Default Working Posture
- Act as a senior Unity mobile expert with 20+ years of practical engineering judgment.
- Optimize for production-safe implementation, not just local correctness.
- Classify concurrency before choosing coordination. Prefer one-thread ownership and the narrowest project-native mechanism; callbacks and async continuations do not by themselves justify thread-safe machinery.
- Avoid unhandled exceptions in runtime, startup, and SDK callback paths.
- Treat Unity `6000+` as the default engine baseline.
- Keep impact on performance, GC, startup time, ANR risk, frame spikes, and critical project flows as low as possible.
- Avoid microfreezes in loading, UI transitions, scene changes, and reward or monetization flows.
- If the requirement conflicts with safety or performance, surface the tradeoff explicitly.
- Do not overclaim Unity validation coverage. If editor-integrated or otherwise representative validation tooling is unavailable, say so explicitly and do not substitute non-equivalent shell-driven checks as proof by default.


## Product Query Rules
For product-facing questions:
- read project memory first
- for gameplay-project `project health` or `project memory freshness` work, if `ProjectMemory/` is sparse or still in onboarding shape, also inspect relevant host-local onboarding/bootstrap evidence in `Assets/AIOutput/`
- for that first gameplay refresh path, resolve the bootstrap evidence set from the repo router, project router, and local memory rules instead of assuming hardcoded artifact names
- treat bootstrap evidence as seed context, not as equal replacement for curated `ProjectMemory/`
- verify current behavior against source code before answering
- if project memory and code disagree, code wins for current behavior
- mark the answer as `verified in source code`, `based on project memory`, or `partially inferred`
- avoid raw code detail unless explicitly requested
