# XUUnity Task: Start Session

## Goal
Assemble the minimum prompt stack for the current Unity task.
Start every new task from a senior mobile-production mindset.
Support shorthand commands such as `xuunity refactor this code` and expand them into the full working context automatically.
Assume Unity `6000+`, mobile target constraints, zero-crash and zero-ANR expectations, and no microfreezes on critical flows.

## Process
1. Classify the task from the user request, even if the request is shorthand.
1a. Resolve the target project from referenced local source paths before role and stack assembly.
1b. If all referenced local source paths fall under one project root, treat that project as resolved immediately.
1c. If the repo contains multiple Unity projects and no concrete target project can be resolved, do not assume the current workspace root is the target project; ask for clarification or perform minimal project discovery first.
1d. If the target project is resolved, load that project's router before final stack narrowing.
2. Detect whether the user requested a specific role.
3. If no role was requested, infer the best primary role from the task type and risk profile.
3a. Infer whether the task needs explicit risk classification and policy-pack routing.
3b. If the task touches SDK initialization, consent sequencing, attribution identity, ad revenue reporting, startup ownership, or third-party wrapper code, require root-cause tracing before proposing a source-level fix.
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
12. When the task touches internal presenter-driven UI, choose the narrowest internal UI skill by lifetime shape:
   - `skills/ui/screen_presenters.md` for long-lived screens, tabs, pages, or root screen composition
   - `skills/ui/flow_presenters.md` for one-shot popups, modal flows, or explicit flow-result presenters
   - `skills/ui/presenter_development.md` only as the lifetime-map entry file or when the task spans more than one presenter shape
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
20a. Before implementation, review, or planning output is finalized, derive a compact execution contract for the session.
20b. Minimum execution-contract fields:
  - `resolved_project`
  - `primary_task`
  - `overlay_tasks`
  - `matched_skills`
  - `matched_policy_packs`
  - `trigger_reasons`
  - `required_validation`
  - `required_self_review`
20c. Keep the execution contract short and concrete. Use `none` when a field is intentionally empty instead of omitting it.
20d. If investigation changes the inferred stack, risk class, or validation obligations, update the execution contract before proposing a patch or final recommendation.
20e. For `tasks/bug_fixing.md`, treat `required_validation` as provisional until patch-shape classification is known, then derive it from patch shape and bug family instead of leaving it at generic wording such as `validate fix`.
20f. If investigation reveals queues, flush paths, cache fallbacks, delay gates, helper wrappers, or other orchestration ballast, add those signals to `trigger_reasons` and make `required_self_review` explicitly cover simplification and complexity-budget review.
20g. If the user is likely to copy code, commands, config, prompts, or patch text from the answer, add a copy-safety check to `required_self_review` and plan the final answer around clean fenced blocks.
20h. If new tests are authored, extend `required_self_review` to include a quick test-quality pass against `skills/tests/testing_doctrine.md` and `reviews/test_quality_review.md`.
21. If the task depends on validation, confirm whether the available tool path is representative for a Unity project before running it; if not, avoid defaulting to substitute shell-driven validation and plan for an explicit validation gap.
22. Do not treat the mere presence of a Unity binary or CLI entrypoint as proof that direct shell-launched Unity validation is allowed for the current repo.
23. Before running Unity via shell, batchmode, `-runTests`, `-executeMethod`, or similar editor automation, check host-local overlays, project routers, and project memory for validation-path constraints.
24. If a host-local or project-local rule requires Unity validation to go through MCP or another repo-specific integration, treat that as a hard must-not for direct shell-launched Unity and do not fall back to the CLI.
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
- When public core and internal overlay differ, follow the internal overlay for monorepo-specific behavior unless current project memory overrides both.
- Do not load broad internal overlay files when a narrower lifetime-specific UI skill exists.

## Monorepo Project Resolution
- In a multi-project Unity monorepo, referenced local source paths are the strongest project-selection signal.
- If the request references one or more files under a single project root such as `<Project>/Assets/...`, `<Project>/Packages/...`, or another project-owned source subtree, treat that project as the active target project immediately.
- When the target project is resolved from source paths, load that project's router and project memory before final role, skill, and review narrowing.
- Do not remain on repo-generic `xuunity` routing when a concrete project path already identifies the project.
- If referenced local paths span more than one project root, ask for clarification instead of guessing.
- If no project can be resolved in a multi-project monorepo, prefer one short clarification question over a repo-generic implementation proposal.

## Internal Overlay Routing Hints
- If the task is about a long-lived screen, tab, lobby page, or page-composition presenter on the internal `_Core.UI/UIPresenter` stack, prefer `AIModules/XUUnityInternal/skills/ui/screen_presenters.md`.
- If the task is about a popup, modal, temporary flow, wizard-like interaction, or presenter that returns an explicit flow result, prefer `AIModules/XUUnityInternal/skills/ui/flow_presenters.md`.
- If the task is about choosing between presenter lifetime shapes, extracting presenter patterns, or refactoring the boundary between scene roots and presenters, also load `AIModules/XUUnityInternal/skills/ui/presenter_development.md`.

## Shared Knowledge Routing Hints
- Do not load the whole `knowledge/` folder by default.
- Load `knowledge/decision_rules.md` when the task changes routing, ownership boundaries, storage destinations, shared-vs-project placement, runtime config mutation policy, or when validation strategy depends on tool-path selection and evidence quality.
- Load `knowledge/risk_classification.md` when task assembly needs an explicit risk class or matched policy pack, especially for SDK, startup, manifest/native, monetization, save/load, or other critical-flow-sensitive work.
- Load `knowledge/severity_matrix.md` when the task requires explicit severity classification or release-blocker framing for findings, risks, or system-health issues.
- Load `knowledge/sdk_stability_scoring.md` when comparing SDK versions, connector tracks, upgrade candidates, or stability-first SDK choices.
- Load `knowledge/glossary.md` for protocol/system onboarding, handoff, or when terms such as `project memory`, `previous outputs`, `bridge crossing`, or `release blocker` are likely to be ambiguous.
- Load `knowledge/ios_passive_network_monitoring.md` when the task is about `NWPathMonitor`, iOS path observers, passive network-environment monitoring, VPN or proxy heuristic detection on iOS, tunnel classification, or replacing legacy reachability-style logic.

## Skill Routing Hints
- If the task mentions `PrimeTween`, `DOTween`, tween sequences, UI fade or scale transitions, or null or destroyed tween targets, load the narrowest relevant file from `skills/ui_tweens/`.
- Prefer `skills/ui_tweens/primetween.md` when the codebase uses PrimeTween and the bug or review depends on tween target lifetime, callback ownership, or popup close order.

## Risk Routing Hints
- Keep risk routing additive and narrow. Do not turn policy-pack matching into a broad always-on bundle.
- Prefer one primary policy pack:
  - `reviews/policy_packs/sdk_changes.md`
  - `reviews/policy_packs/startup_changes.md`
  - `reviews/policy_packs/manifest_native_changes.md`
- If more than one family clearly matches, keep one primary pack and load only the extra overlays the second family contributes.
- Use `knowledge/risk_classification.md` to infer:
  - `low`
  - `moderate`
  - `high`
  - `critical`
- Escalate risk when multiple independent high-risk signals are present, when validation-path uncertainty is material, or when the task directly touches critical flows.
- Show the trigger reason explicitly in task framing, for example:
  - `risk class: high`
  - `policy pack: startup changes`
  - `triggered by: startup sequencing + SDK initialization`
- Prefer the first matched policy pack by dominant breakage surface:
  - SDK wrapper, version, connector, or vendor-boundary change -> `reviews/policy_packs/sdk_changes.md`
  - startup sequence, first interactive flow, or startup-blocking consent/init change -> `reviews/policy_packs/startup_changes.md`
  - manifest, plist, entitlement, privacy-manifest, JNI, or native bridge contract change -> `reviews/policy_packs/manifest_native_changes.md`

## Critical Bug Escalation Rules
- Do not keep a bug on generic `tasks/bug_fixing.md` only when the request touches SDK startup, consent sequencing, attribution identity, ad revenue reporting, or third-party wrappers.
- Automatically escalate a bug-fix task into SDK-sensitive and startup-sensitive routing when the request, code paths, or referenced files mention signals such as:
  - `AppsFlyer`
  - `Firebase`
  - `OneSignal`
  - `CustomerUserId`
  - `setCustomerUserId`
  - `af_ad_revenue`
  - `logAdRevenue`
  - `initSDK`
  - `startSDK`
  - `consent`
  - `ATT`
  - `startup`
- For these signals, add the minimum relevant stack from:
  - `reviews/policy_packs/sdk_changes.md`
  - `reviews/policy_packs/startup_changes.md`
  - `skills/sdk/`
  - `skills/async/`
  - `skills/mobile/startup.md`
  - host-local startup-consent knowledge when available
- If the task touches attribution identity, queued delivery, consent-gated SDK start, or revenue-reporting boundaries, prefer `skills/sdk/initialization.md`, `skills/sdk/wrapper_design.md`, and `skills/sdk/callback_safety.md`.
- If investigation or the patch plan shows that the fix also includes moving code across layers, merging duplicated orchestration, or introducing state machinery such as queues, flushes, or cache-backed fallback behavior, also load `tasks/refactoring.md` as an overlay so the final patch is simplified after it works.

## Root Cause Before Patch
- For SDK, startup, consent, attribution, identity-bound, and ad-revenue bugs, do not propose or implement a callsite-only fix before tracing the full ownership path.
- Trace at minimum:
  - the user-visible symptom
  - the wrapper or adapter that emits the event
  - the startup or consent owner that initializes the SDK
  - the identity owner for user or customer ids
  - any queueing, delay, or retry path between initialization and delivery
- If the reported symptom is a missing or empty field on an SDK event, inspect where that field is owned and when the event can be emitted relative to consent, startup readiness, and identity assignment.
- Prefer ownership and sequencing fixes over payload-only patching when the bug touches startup, consent, async delivery, or SDK state.
- A local patch such as `set the id immediately before sending the event` is not sufficient by default when the real breakage surface may be SDK readiness, delayed delivery, consent order, or startup ownership.

## Execution Contract
- Derive and surface a compact execution contract before patching, large review output, or implementation planning.
- Use this shape:
  - `resolved_project`
  - `primary_task`
  - `overlay_tasks`
  - `matched_skills`
  - `matched_policy_packs`
  - `trigger_reasons`
  - `required_validation`
  - `required_self_review`
- `required_validation` should name the narrowest representative proof currently required, such as affected assembly compile, representative build target, explicit runtime validation gap, or a review-only limitation.
- For `tasks/bug_fixing.md`, update `required_validation` after patch-shape classification so it reflects patch shape and bug family rather than generic session risk alone.
- `required_self_review` should say what must still be re-checked before closure, such as hidden behavior drift, queue cleanup, ownership fallout, or contract fallout from moved call paths.
- When queues, flags, wrappers, flush paths, or cache-backed fallbacks appear during investigation, include them in `trigger_reasons` and require explicit simplification and complexity-budget review before closure.
- If investigation changes routing or patch shape later in the session, update the execution contract before patching or final closure.

## Shorthand Expansion Rules
Interpret short commands by intent:
- `xuunity refactor ...` -> `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity extract service ...`, `xuunity split class ...`, `xuunity split presenter ...`, `xuunity decouple ...`, `xuunity untangle ...`, or `xuunity migrate ...` should also prefer `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity fix ...` -> `tasks/bug_fixing.md`
  - always include the testing baseline from `skills/tests/testing_doctrine.md`
  - when the request also carries SDK, startup, consent, attribution, identity, ad revenue, or third-party wrapper signals, keep `tasks/bug_fixing.md` as the task file but also load the matched SDK-sensitive and startup-sensitive stack instead of staying on a narrow local fix route
  - when investigation or the patch plan shows that the fix changes ownership boundaries or adds non-trivial orchestration or state handling, also load `tasks/refactoring.md` as a cleanup and behavior-preservation overlay
- `xuunity feature request ...` or `xuunity intake feature ...` -> `tasks/feature_request_intake.md`
- `xuunity feature design ...` or `xuunity design feature ...` -> `tasks/feature_design_brief.md`
- `xuunity architecture plan ...`, `xuunity arch plan ...`, `xuunity plan this subsystem split ...`, or `xuunity plan the architecture ...` -> `tasks/architecture_plan.md`
- `xuunity feature screen ...` -> `tasks/feature_development.md` plus internal `skills/ui/screen_presenters.md` when the host overlay exists
- `xuunity feature popup ...` -> `tasks/feature_development.md` plus internal `skills/ui/flow_presenters.md` when the host overlay exists
- `xuunity feature presenter ...` -> `tasks/feature_development.md` plus the narrowest internal presenter skill by inferred lifetime shape
- `xuunity implementation plan ...` or `xuunity feature plan ...` -> `tasks/implementation_plan.md`
- `xuunity validation plan ...` or `xuunity feature validation ...` -> `tasks/validation_plan.md`
- `xuunity rollout plan ...` or `xuunity feature rollout plan ...` -> `tasks/rollout_plan.md`
- `xuunity commit this work ...`, `xuunity commit all changes ...`, `xuunity push local changes ...`, `xuunity push all changes ...`, `xuunity publish local changes ...`, `xuunity publish all changes ...`, or `xuunity split these changes into commits ...` -> `tasks/change_delivery.md`
- `xuunity task registry bootstrap ...`, `xuunity enable task registry ...`, or `xuunity setup task history ...` -> `utilities/task_registry_bootstrap.md`
- `xuunity start tracking this task ...`, `xuunity open task record ...`, or `xuunity create task record ...` -> `utilities/task_tracking_start.md`
- `xuunity finish the work ...`, `xuunity close this task ...`, `xuunity record this fix ...`, or `xuunity post and record this work ...` -> `utilities/task_registry_append.md`
- `xuunity publish the work ...` -> `tasks/change_delivery.md` first, then any host-declared closeout or reporting route from the repo router
- `xuunity this works ...`, `xuunity this has bugs ...`, `xuunity reopen this task ...`, `xuunity mark this validated ...`, or `xuunity customer says it works ...` -> `utilities/task_feedback_capture.md`
- `xuunity task registry reconcile ...` or `xuunity rebuild task index ...` -> `utilities/task_registry_reconcile.md`
- `xuunity validate task registry ...`, `xuunity check task events ...`, or `xuunity task registry lint ...` -> `utilities/task_registry_validate.md`
- `xuunity task metrics ...` or `xuunity ai delivery metrics ...` -> `utilities/task_metrics_rollup.md`
- `xuunity archive task registry ...`, `xuunity task registry rollover ...`, or `xuunity review task registry retention ...` -> `utilities/task_registry_archive.md`
- `xuunity delivery risk ...` or `xuunity feature risk review ...` -> `reviews/delivery_risk_review.md`
- `xuunity feature ...` or `xuunity implement ...` -> `tasks/feature_development.md`
  - always include the testing baseline from `skills/tests/testing_doctrine.md`
- `xuunity review the git change ...` -> `reviews/git_change_review.md`
- `xuunity git change review ...` -> `reviews/git_change_review.md`
- `xuunity review tests ...` -> `reviews/test_quality_review.md`
- `xuunity tests review ...` -> `reviews/test_quality_review.md`
- `xuunity review test quality ...` -> `reviews/test_quality_review.md`
- `xuunity full review ...` -> `reviews/full_review.md`
- `xuunity review all ...` -> `reviews/full_review.md`
  - classify target kind first:
    - `current_state_sdk`
    - `current_state_feature`
    - `current_state_project`
    - `change_sdk`
    - `change_feature`
    - `change_project`
  - activate matching policy packs before final bundle assembly:
    - `reviews/policy_packs/sdk_changes.md`
    - `reviews/policy_packs/startup_changes.md`
    - `reviews/policy_packs/manifest_native_changes.md`
  - prefer one aggregate report with canonical merged findings unless the user explicitly asks for per-protocol reports
- `xuunity review ...` -> `tasks/code_review.md`
- `xuunity sdk ...` -> `tasks/sdk_integration.md` or `reviews/sdk_code_review.md` based on whether the user asks to build or review
- `xuunity sdk breakage review ...` -> `reviews/sdk_breakage_review.md`
- `xuunity plugin ...` or `xuunity native ...` -> `tasks/native_plugin_work.md` or `reviews/native_plugin_review.md` based on intent
- `xuunity system extract review artifact ...` -> `utilities/review_artifact_extract.md`
- `xuunity system merge review artifacts ...` -> `utilities/review_artifact_merge.md`
- `xuunity system integrate review artifacts ...` -> `utilities/review_artifact_merge.md`
- `xuunity extract implementation pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity extract presenter pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity system extract implementation pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity system extract presenter pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity extract ...` -> `utilities/knowledge_extraction_triage.md`
- `xuunity system extract ...` -> `utilities/knowledge_extraction_triage.md`
- `xuunity system merge ...` -> `utilities/skill_merge.md` plus `utilities/knowledge_merge.md`
- `xuunity system intake review ...` -> `utilities/knowledge_intake_review.md`
- `xuunity apply approved extraction ...` -> `utilities/knowledge_integration.md`
- `xuunity system integrate approved ...` -> `utilities/knowledge_integration.md`
- `xuunity system apply approved extraction ...` -> `utilities/knowledge_integration.md`
- `xuunity intake ...` -> `utilities/knowledge_intake_review.md`
- `xuunity apply approved ...` -> `utilities/knowledge_integration.md`
- `xuunity integrate approved ...` -> `utilities/knowledge_integration.md`
- `xuunity system progress review ...` -> `utilities/system_progress_review.md`
- `xuunity system next milestone ...` -> `utilities/system_progress_review.md`
- `xuunity system registry refresh ...` -> `utilities/system_registry_refresh.md`
- `xuunity system refresh project registry ...` -> `utilities/system_registry_refresh.md`
- `xuunity system project registry audit ...` -> `utilities/system_project_registry_audit.md`
- `xuunity system registry audit ...` -> `utilities/system_project_registry_audit.md`
- `xuunity task registry bootstrap ...`, `xuunity enable task registry ...`, or `xuunity setup task history ...` -> `utilities/task_registry_bootstrap.md`
- `xuunity start tracking this task ...`, `xuunity open task record ...`, or `xuunity create task record ...` -> `utilities/task_tracking_start.md`
- `xuunity finish the work ...`, `xuunity close this task ...`, `xuunity record this fix ...`, or `xuunity post and record this work ...` -> `utilities/task_registry_append.md`
- `xuunity publish the work ...` -> `tasks/change_delivery.md` first, then any host-declared closeout or reporting route from the repo router
- `xuunity this works ...`, `xuunity this has bugs ...`, `xuunity reopen this task ...`, `xuunity mark this validated ...`, or `xuunity customer says it works ...` -> `utilities/task_feedback_capture.md`
- `xuunity task registry reconcile ...`, `xuunity rebuild task index ...`, or `xuunity sync task snapshots ...` -> `utilities/task_registry_reconcile.md`
- `xuunity validate task registry ...`, `xuunity check task events ...`, or `xuunity task registry lint ...` -> `utilities/task_registry_validate.md`
- `xuunity task metrics ...`, `xuunity task registry metrics ...`, or `xuunity ai delivery metrics ...` -> `utilities/task_metrics_rollup.md`
- `xuunity archive task registry ...`, `xuunity task registry rollover ...`, or `xuunity review task registry retention ...` -> `utilities/task_registry_archive.md`
- `xuunity system research watch ...` -> `utilities/internet_research_watch.md`
- `xuunity system research what is new ...` -> `utilities/internet_research_watch.md`
- `xuunity system evaluate ...` -> `utilities/system_self_evaluation.md`
- `xuunity system health review ...` -> `utilities/system_health_review.md`
- `xuunity system cleanup ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup projects ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup all ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup apply ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system apply cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system apply approved cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system cleanup stale reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup ai outputs ...` -> `utilities/system_output_cleanup.md`
- `xuunity system archive old reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system audit ai clutter ...` -> `utilities/system_output_cleanup.md`
- `xuunity system evaluation cadence ...` -> `utilities/system_evaluation_cadence.md`
- `xuunity slack summary ...`, `xuunity post this work to slack`, `xuunity report this work to slack`, `xuunity finish the work ...`, or `xuunity publish the work ...` -> use the repo-level Slack delivery route and load the host-local Slack work-summary utility when the repo router declares one
- `xuunity product explain ...` or `xuunity product feature ...` -> `product/protocols/feature_explainer.md`
  - if the queried feature is represented by a project-local class that inherits from or delegates into a shared runtime layer, inspect that shared layer before answering
  - for gameplay projects that use a project-local gameplay bridge, flow-style explain requests should inspect the host-declared bridge entry artifact under `Assets/AIOutput/` first unless the current project router or project memory explicitly opts out of that path
- `xuunity product brief ...` or `xuunity product implementation brief ...` -> `product/protocols/implementation_brief.md`
- `xuunity product impact ...` -> `product/protocols/change_impact.md`
- `xuunity product rollout ...` or `xuunity product rollout readiness ...` -> `product/protocols/rollout_readiness.md`
- `xuunity product deps ...` or `xuunity product dependency map ...` -> `product/protocols/dependency_map.md`
- `xuunity product bug ...` or `xuunity product impact of this bug ...` -> `product/protocols/bug_impact_brief.md`
- `xuunity product health ...` or `xuunity project health audit ...` -> `product/protocols/project_health_audit.md`
- `xuunity product memory freshness ...` or `xuunity project memory freshness ...` -> `product/protocols/project_memory_freshness.md`
- `xuunity feature request ...` should prefer `tasks/feature_request_intake.md` before `tasks/feature_development.md` when the user is asking to define scope rather than immediately build
- `xuunity feature design ...` should prefer `tasks/feature_design_brief.md` when the user is shaping a feature before architecture selection or execution planning
- `xuunity feature screen ...` should prefer the internal `screen_presenters.md` overlay when the task is clearly about a long-lived presenter-driven screen on this monorepo stack
- `xuunity feature popup ...` should prefer the internal `flow_presenters.md` overlay when the task is clearly about a modal, popup, or one-shot flow presenter
- `xuunity feature presenter ...` should infer whether the request is a screen presenter or flow presenter task before loading the narrower internal overlay skill
- `xuunity implementation plan ...` should prefer `tasks/implementation_plan.md` when the user is asking for execution sequencing rather than target-shape design or direct coding
- `xuunity architecture plan ...` or `xuunity arch plan ...` should prefer `tasks/architecture_plan.md` plus `role/architect.md` and `skills/architecture/`
- `xuunity validation plan ...` should prefer `tasks/validation_plan.md` when the user is asking how the feature should be validated before or during implementation
- `xuunity rollout plan ...` or `xuunity feature rollout plan ...` should prefer `tasks/rollout_plan.md` when the user is asking how the feature should be exposed, monitored, or rolled back rather than whether it is already ready to ship
- `xuunity commit this work ...`, `xuunity commit all changes ...`, `xuunity push local changes ...`, `xuunity push all changes ...`, `xuunity publish local changes ...`, `xuunity publish all changes ...`, `xuunity publish the work ...`, or `xuunity split these changes into commits ...` should prefer `tasks/change_delivery.md` when the user wants commit hygiene, commit naming, or push sequencing rather than implementation changes

Role selectors are also valid.
Examples:
- `xuunity role product owner evaluate this feature`
- `xuunity role senior unity developer refactor this system`
- `xuunity role architect plan this subsystem split`
- `xuunity role technical developer fix this frame spike`
- `xuunity role technical artist review this shader setup`
- `xuunity role ui integrator integrate this popup`
- `xuunity role qa manual test this reward flow`
- `xuunity role qa automation design tests for this startup path`
- `xuunity role researcher compare these approaches`
- `xuunity role troubleshooter master find the root cause of this legacy bug`
- `xuunity as product owner review this monetization change`
- `xuunity po evaluate this feature`
- `xuunity sud refactor this system`
- `xuunity arch plan this subsystem split`
- `xuunity td fix this frame spike`
- `xuunity ta review this shader setup`
- `xuunity ui integrate this popup`
- `xuunity qa test this reward flow`
- `xuunity qa auto design tests for this startup path`
- `xuunity researcher compare these approaches`
- `xuunity tm find the root cause of this legacy bug`

Then auto-load the rest of the stack:
- the resolved project router when the target project is known
- the selected primary role file from `role/`
- only the minimum useful supporting role files if multi-angle work is needed
- one or more relevant files from `codestyle/`
- `skills/core/`
- only the relevant task-specific files from `skills/`
- optional role support files if useful
- the inferred task file
- required review files
- required utility files
- required platform files
- project memory
- relevant prior outputs
- relevant product protocol file if this is a product-facing query

Do not require the user to manually enumerate prompt files in normal usage.
Any XUUnity implementation or review task should use the shared code style guidance from `codestyle/`.
Skill routing should prefer the minimum correct stack instead of loading broad knowledge dumps.
If a skill family is matched by intent, keywords, code signals, or project context, the task or review is incomplete without loading that matched skill layer.
Treat `platforms/` as a final platform-specific overlay, not as the primary source of reusable engineering knowledge.
Specific routes must take precedence over broader ones.
Examples:
- `xuunity review the git change` must route to `reviews/git_change_review.md`
- generic `xuunity review ...` should be used only when no narrower review command matches

## Default Working Posture
- Act as a senior Unity mobile expert with 20+ years of practical engineering judgment.
- Optimize for production-safe implementation, not just local correctness.
- Prefer thread-safe and ownership-safe solutions when concurrency or callbacks are involved.
- Avoid unhandled exceptions in runtime, startup, and SDK callback paths.
- Treat Unity `6000+` as the default engine baseline.
- Keep impact on performance, GC, startup time, ANR risk, frame spikes, and critical project flows as low as possible.
- Avoid microfreezes in loading, UI transitions, scene changes, and reward or monetization flows.
- If the requirement conflicts with safety or performance, surface the tradeoff explicitly.
- Do not overclaim Unity validation coverage. If editor-integrated or otherwise representative validation tooling is unavailable, say so explicitly and do not substitute non-equivalent shell-driven checks as proof by default.

## Role Selection
Default:
- `role/base_role.md`

Use a role-specific file when the user explicitly asks for:
- `product owner`
- `senior unity developer`
- `architect`
- `technical developer`
- `technical artist`
- `ui integrator`
- `qa manual`
- `qa automation`
- `researcher`
- `troubleshooter master`

Accepted short aliases:
- `po` -> `product owner`
- `sud` -> `senior unity developer`
- `arch` -> `architect`
- `td` -> `technical developer`
- `ta` -> `technical artist`
- `ui` -> `ui integrator`
- `qa` -> `qa manual`
- `qa auto` -> `qa automation`
- `researcher` -> `researcher`
- `tm` -> `troubleshooter master`

Alias precedence:
- if the token appears immediately after `xuunity`, treat it as a role alias
- otherwise treat matching words such as `ui`, `async`, `shader`, or `sdk` as task and skill signals
- example:
  - `xuunity ui integrate this popup` -> `ui integrator` role
  - `xuunity fix this ui popup bug` -> normal task routing plus `skills/ui/`

## Automatic Role Routing
If the user does not specify a role, route by task:
- `bug fixing` -> `role/senior_unity_developer.md`
- `refactoring` -> `role/senior_unity_developer.md`
- `feature development` -> `role/senior_unity_developer.md`
- `code review` -> `role/senior_unity_developer.md`
- `architecture planning` -> `role/architect.md`
- `performance diagnosis or optimization` -> `role/technical_developer.md`
- `UI integration` -> `role/ui_integrator.md`
- `rendering, shader, VFX, or art-tech work` -> `role/technical_artist.md`
- `manual validation design` -> `role/qa_manual.md`
- `automation strategy` -> `role/qa_automation.md`
- `product scope or acceptance review` -> `role/product_owner.md`
- `research or option comparison` -> `role/researcher.md`
- `complex legacy root-cause work` -> `role/troubleshooter_master.md`
- `product explain or implementation brief` -> `role/product_owner.md`
- `product change impact` -> `role/product_owner.md`
- `product rollout readiness` -> `role/product_owner.md`
- `rollout planning` -> `role/product_owner.md`
- `product dependency map` -> `role/product_owner.md`
- `product bug impact` -> `role/product_owner.md`
- `project health audit` -> `role/product_owner.md`
- `project memory freshness` -> `role/product_owner.md`

## Role Groups
Use a role group only when it increases decision quality.
Do not load large role bundles by default.

Role contract:
- always select exactly one primary role
- add supporting roles only when they change the decision quality materially
- supporting roles must not override the primary task intent
- if the task is simple, stay with one primary role

Recommended role groups:
- risky feature on critical flow:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/qa_manual.md`
- performance issue:
  - `role/technical_developer.md`
  - `role/senior_unity_developer.md`
  - `role/technical_artist.md` if rendering, UI, or content cost is involved
- architecture or large refactor:
  - `role/architect.md`
  - `role/senior_unity_developer.md`
  - `role/researcher.md` if tradeoff comparison matters
- UI-heavy feature or regression:
  - `role/ui_integrator.md`
  - `role/senior_unity_developer.md`
  - `role/qa_manual.md`
- complex legacy bug:
  - `role/troubleshooter_master.md`
  - `role/senior_unity_developer.md`
  - `role/researcher.md`
- release-readiness or critical-flow validation:
  - `role/qa_manual.md`
  - `role/qa_automation.md`
  - `role/product_owner.md` if acceptance or rollout risk matters
- product implementation or dependency explanation:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/architect.md` if boundaries matter
- product rollout readiness:
  - `role/product_owner.md`
  - `role/qa_manual.md`
  - `role/qa_automation.md`
- rollout planning:
  - `role/product_owner.md`
  - `role/qa_manual.md`
  - `role/qa_automation.md`
- product dependency or bug impact brief:
- `role/product_owner.md`
- `role/senior_unity_developer.md`
- `role/qa_manual.md` if severity or reproducibility matters

- project health or memory freshness:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/architect.md` if ownership or structure quality matters

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

## Skill Routing Hints
Prefer these skill families when triggered by the task:
- `skills/async/` for `async`, `await`, `UniTask`, `Awaitable`, `.NET Task`, cancellation, and thread affinity
- `skills/ui/` for screens, popups, layout, canvases, and UI navigation
- when the task is about adaptive grids, inventories, stores, galleries, scrollable card collections, `GridLayoutGroup`, or mobile cell-sizing tradeoffs, also load `skills/ui/adaptive_grids.md`
- when the task is about safe areas, cutouts, touch-target sizing, larger text, localization, RTL, readability, or mobile UX bug prevention, also load `skills/ui/mobile_ux_quality.md`
- when the task is about large `ScrollRect` lists or grids, infinite scroll, virtualization, pooled cells, viewport-window math, or recycle-and-rebind behavior, also load `skills/ui/virtualized_scrollrect.md`
- `skills/editor/` for inspectors, importers, validation tools, and internal workflows
- `skills/audio/` for sounds, music, mixer, snapshots, and clip loading
- `skills/fx/` for particles, VFX lifecycle, spawn budgets, and overdraw-sensitive effects
- `skills/shaders/` for materials, variants, mobile rendering, and SRP batcher constraints
- `skills/optimization/` for allocations, loading, startup, ANR prevention, and microfreeze reduction
- `skills/profiling/` for profiler evidence, instrumentation, and regression analysis
- `skills/tests/` for unit, integration, playmode, smoke, and release-critical validation
- when the task explicitly involves Unity Test Runner operation, batchmode `-runTests`, project-lock diagnosis, `EditMode` versus `PlayMode` selection, or turning rough timings into trustworthy perf evidence, also load `skills/tests/unity_test_runner_workflow.md`
- `skills/architecture/` for subsystem boundaries, state ownership, and event-driven flows
- `skills/refactoring/` for behavior-preserving cleanup, extraction, decoupling, and staged migration
- `skills/mobile/` for startup, resume, thermal, battery, and critical mobile runtime posture
- `skills/sdk/` for SDK init, callback safety, consent, and privacy-sensitive integration
- `skills/native/` for JNI, Java, Kotlin, Swift, Objective-C, Objective-C++, and bridge ownership

When the task is a high-risk SDK review, also prefer:
- `reviews/sdk_breakage_review.md`
- `skills/sdk/`
- `skills/async/`
- `skills/native/` if native/plugin layers are involved
- `skills/tests/` for breakage-oriented test design

When policy-pack routing is active:
- load the matched `reviews/policy_packs/*.md` file
- keep the pack narrow by composing existing `reviews/`, `skills/`, `knowledge/`, and `platforms/` files
- preserve narrower routes such as `sdk breakage review`, `native review`, and `release readiness` instead of flattening them into generic risk routing

When async signals are present, load:
- `skills/async/base_async_rules.md`
- the relevant topic files from `skills/async/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/async.md` if present

For family distinctions, prefer the canonical family routing files:
- `skills/architecture/routing.md`
- `skills/refactoring/routing.md`

Use this planning split:
- `tasks/feature_design_brief.md` for feature-shape and user-flow design
- `tasks/architecture_plan.md` for target-shape and ownership decisions
- `tasks/refactoring.md` plus `skills/refactoring/` for safe migration on live code
- `tasks/implementation_plan.md` for execution sequencing after the target shape is accepted
- `tasks/change_delivery.md` for commit splitting, commit-message quality, and push sequencing after the code is ready to publish

## System Utility Hints
Use these utilities when the task is about the protocol system itself:
- `utilities/review_artifact_extract.md` when the user wants a reusable `Engineering Review Artifact` from a long engineering chat, review discussion, or design thread
- `utilities/review_artifact_merge.md` when the user wants to consolidate multiple `Engineering Review Artifact` documents into one stronger reusable artifact
- `utilities/skill_extract.md` when the user provides new best practices or domain knowledge that should become reusable skills
- `utilities/skill_merge.md` when integrating new knowledge into existing skill families
- `utilities/knowledge_intake_review.md` when the user wants a full review report before any integration happens
- `utilities/knowledge_integration.md` only after explicit user approval of a reviewed knowledge package
- `utilities/system_progress_review.md` when the user wants to know current roadmap progress, current bottlenecks, and the next milestone
- `utilities/task_registry_bootstrap.md` when the user wants to enable or verify the repo-level task-history scaffold
- `utilities/task_tracking_start.md` when the user wants lifecycle timing to begin before closure
- `utilities/task_registry_append.md` when the user wants to close work and record a durable task-outcome event
- `utilities/task_feedback_capture.md` when the user wants to record acceptance, reopen, rejection, or validation feedback
- `utilities/task_registry_reconcile.md` when the user wants to rebuild current task snapshots from append-only events
- `utilities/task_registry_validate.md` when the user wants to verify event shape, snapshot consistency, or public-contract compliance
- `utilities/task_metrics_rollup.md` when the user wants delivery metrics or repeated task-pattern summaries
- `utilities/task_registry_archive.md` when the user wants retention or rollover planning for the task-history surface
- `utilities/internet_research_watch.md` when the user wants periodic external research focused on improving the current AI system and tooling
- `utilities/system_self_evaluation.md` when auditing the structure, routing quality, or LLM efficiency of the prompt system
- `utilities/system_health_review.md` when focusing on conflicts, redundancy, dead paths, and cleanup priorities
- `utilities/system_evaluation_cadence.md` when deciding whether the system should be evaluated now and how to act on the score

## Output
- Selected stack
- Inferred risk class, if any
- Derived execution contract:
  - resolved project
  - primary task
  - overlay tasks
  - matched skill packs
  - matched policy packs
  - trigger reasons
  - required validation
  - required self-review
- Missing project memory, if any
- Main risk areas for the session
- Critical flows that must not regress
- Validation focus for thread safety, exception safety, and performance
