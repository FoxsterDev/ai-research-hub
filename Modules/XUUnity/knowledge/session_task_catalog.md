# XUUnity Session Reference: Session Task Catalog

Conditional reference extracted from `tasks/start_session.md`. All paths are module-relative unless explicitly host/project-qualified. This is not an always-loaded entrypoint or a new policy layer. Look up the complete matching sections, then read the selected instruction owners in full. The compact entrypoint owns the mandatory route and `knowledge/execution_contract.md` owns requirement/read accounting.

## Contents
- Shorthand Expansion Rules
- Role Selection
- Automatic Role Routing
- Role Groups
- System Utility Hints

## Shorthand Expansion Rules
Interpret short commands by intent:
- `xuunity refactor ...` -> `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity extract service ...`, `xuunity split class ...`, `xuunity split presenter ...`, `xuunity decouple ...`, `xuunity untangle ...`, or `xuunity migrate ...` should also prefer `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity fix ...` -> `tasks/bug_fixing.md`
  - always include the testing baseline from `skills/tests/testing_doctrine.md`
  - when the request also carries SDK, startup, consent, attribution, identity, ad revenue, or third-party wrapper signals, keep `tasks/bug_fixing.md` as the task file but also load the matched SDK-sensitive and startup-sensitive stack instead of staying on a narrow local fix route
  - when the request reports a runtime warning or exception that crosses feature startup, a flow/presenter, async service, remote asset/content service, SDK/service init, or active config/profile, keep `tasks/bug_fixing.md` as the task file but add `startup/config ownership` routing and block local source patches until the owner chain is checked
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
- `xuunity sdk discover <Vendor> ...`, `xuunity sdk check <Vendor> ...`, or `xuunity sdk scout <Vendor> ...` -> `tasks/sdk_update_research.md`
  - this is the canonical one-command SDK update candidate research flow
  - if the command includes `for <Project>`, resolve that project explicitly
  - if no project is named, use the active resolved project or the Unity project that owns the current working directory
  - if the workspace is a multi-project monorepo root and no project is resolved, ask one short clarification question
  - load `knowledge/sdk_stability_scoring.md`, `reviews/policy_packs/sdk_changes.md`, `skills/sdk/discovery_and_inventory.md`, and the matching `knowledge/vendors/<vendor>.md` profile when available
  - when a vendor component is named, such as `xuunity sdk discover AppLovin Pangle`, keep one command but run component-mode research inside the task
  - when the command says `for all apps`, run portfolio-mode research and group projects by safe update lane
  - save the resulting research report before returning the final recommendation
- `xuunity sdk profile design <Vendor> ...`, `xuunity sdk research profile <Vendor> ...`, or `xuunity system design sdk research profile <Vendor> ...` -> `utilities/sdk_vendor_research_profile_template.md`
  - this is the canonical flow for creating a new vendor-specific SDK update research profile
  - compare against `knowledge/vendors/appsflyer.md` and `knowledge/vendors/applovin_max.md`
  - require source-of-truth ladder, candidate identity, wrapper-to-native version mapping, mandatory extraction, breaking-change/API migration checkpoint, hard gates, scoring rules, validation, and command examples
  - create or update `knowledge/vendors/<vendor>.md` only when the user asks for integration or has approved the profile design
- `xuunity commit this work ...`, `xuunity commit all changes ...`, `xuunity push local changes ...`, `xuunity push all changes ...`, `xuunity publish local changes ...`, `xuunity publish all changes ...`, or `xuunity split these changes into commits ...` -> `tasks/change_delivery.md`
- `xuunity agent bootstrap ...`, `xuunity bootstrap agent memory ...`, `xuunity setup agent memory ...`, `xuunity install working discipline ...`, or `xuunity refresh working discipline ...` -> `utilities/agent_private_bootstrap.md`
- `xuunity task registry bootstrap ...`, `xuunity enable task registry ...`, or `xuunity setup task history ...` -> `utilities/task_registry_bootstrap.md`
- `xuunity start tracking this task ...`, `xuunity open task record ...`, or `xuunity create task record ...` -> `utilities/task_tracking_start.md`
- `xuunity finish the work ...`, `xuunity close this task ...`, `xuunity record this fix ...`, or `xuunity post and record this work ...` -> `utilities/task_registry_append.md`
- `xuunity publish the work ...` -> `tasks/change_delivery.md` first, then any host-declared closeout or reporting route from the repo router
- `xuunity this works ...`, `xuunity this has bugs ...`, `xuunity reopen this task ...`, `xuunity mark this validated ...`, or `xuunity customer says it works ...` -> `utilities/task_feedback_capture.md`
- `xuunity task registry reconcile ...`, `xuunity rebuild task index ...`, or `xuunity sync task snapshots ...` -> `utilities/task_registry_reconcile.md`
- `xuunity validate task registry ...`, `xuunity check task events ...`, or `xuunity task registry lint ...` -> `utilities/task_registry_validate.md`
- `xuunity task metrics ...`, `xuunity task registry metrics ...`, or `xuunity ai delivery metrics ...` -> `utilities/task_metrics_rollup.md`
- `xuunity archive task registry ...`, `xuunity task registry rollover ...`, or `xuunity review task registry retention ...` -> `utilities/task_registry_archive.md`
- `xuunity delivery risk ...` or `xuunity feature risk review ...` -> `reviews/delivery_risk_review.md`
- any normal XUUnity task command that includes an explicit Claude execution
  selector such as `via claude`, `with claude`, `use claude`, `through claude`,
  `using claude`, `через claude`, or `с claude` -> keep the normal task routing
  and add the external AI CLI overlay:
  - provider selector: `claude_cli`
  - operation: `AIRoot/Operations/XUUnityAiCliOrchestrator/`
  - auth policy: official login/OAuth only
  - billing policy: subscription quota first, no API-key fallback
  - proof gate: Claude must prove official subscription login, subscription
    quota, enforced access policy, and resolved model before selection
  - if Claude is unavailable or fails proof gate, continue with the local
    XUUnity stack and report the provider gap
  - do not change the primary task file; `xuunity fix the bug via claude` still
    routes as bug fixing, `xuunity review ... via claude` still routes as review
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
    - `reviews/policy_packs/monetization_changes.md`
    - `reviews/policy_packs/save_load_changes.md`
    - `reviews/policy_packs/ui_heavy_changes.md`
  - prefer one aggregate report with canonical merged findings unless the user explicitly asks for per-protocol reports
- `xuunity design review ...`, `xuunity review designs ...`, `xuunity design retro ...`, `xuunity audit designs ...`, or `xuunity score designs ...` -> `utilities/design_retro_review.md`
- `xuunity review ...` -> `tasks/code_review.md`
- `xuunity sdk breakage review ...` -> `reviews/sdk_breakage_review.md`
- `xuunity sdk ...` -> `tasks/sdk_integration.md` or `reviews/sdk_code_review.md` based on whether the user asks to build, update, or review
- `xuunity plugin ...` or `xuunity native ...` -> `tasks/native_plugin_work.md` or `reviews/native_plugin_review.md` based on intent
- `xuunity paid skill author ...` -> `utilities/module_paid_skill_authoring.md`
- `xuunity module pack review ...` -> `reviews/module_pack_review.md`
- `xuunity module validate installer ...` -> `utilities/module_commercialization.md`
- `xuunity module scan ...` or `xuunity module validate ...` -> `utilities/module_registry.md`
- `xuunity module rollsync ...` -> `utilities/module_rollsync.md`
- `xuunity module session plan ...` -> `utilities/module_session_routing.md`
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
- `xuunity system research watch ...` -> `utilities/internet_research_watch.md`
- `xuunity system research what is new ...` -> `utilities/internet_research_watch.md`
- `xuunity system evaluate ...`, `xuunity system installation review ...`, or `xuunity system review this installation ...` -> `utilities/system_self_evaluation.md`
- `xuunity system protocol clean review ...`, `xuunity system protocol cleanup review ...`, `xuunity system clean protocol review ...`, `xuunity system sanitary review ...`, or `xuunity system public core sanitation ...` -> `utilities/system_protocol_clean_review.md`
- `xuunity system health improve ...` -> `utilities/system_health_review.md` in bounded improve mode
- `xuunity system health review ...` or `xuunity system health ...` -> `utilities/system_health_review.md` in review mode
- `xuunity system output cleanup ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup all aggressive ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup ai outputs ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup stale reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup projects ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup apply ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system cleanup aggressive ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup all ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup ...` -> `utilities/system_output_cleanup.md`
- `xuunity system apply cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system apply approved cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system archive old reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system prune old archives ...` -> `utilities/system_output_cleanup.md`
- `xuunity system audit ai clutter ...` -> `utilities/system_output_cleanup.md`
- `xuunity system evaluation cadence ...` -> `utilities/system_evaluation_cadence.md`

### Cleanup Routing Notes
- Treat legacy shorthand `xuunity system output cleanup ...` as an exact alias for `xuunity system cleanup ...`.
- Treat `xuunity system cleanup aggressive ...`, `xuunity system cleanup all aggressive ...`, and user phrasing such as `hard cleanup`, `prune old archives`, `stop keeping so much history`, or `project changes every week` as explicit volatile-project-mode triggers for `utilities/system_output_cleanup.md`.
- When those triggers are present, the cleanup execution contract should explicitly include:
  - `cleanup_mode: aggressive`
  - `volatile_project_mode: yes`
  - `reference_rewrites_required: yes|no`
  - `archive_recheck_required: yes`
- For aggressive cleanup routing, do not default to project-only scope unless the user explicitly narrows it.
- `xuunity slack summary ...`, `xuunity post this work to slack`, `xuunity report this work to slack`, `xuunity finish the work ...`, or `xuunity publish the work ...` -> use the repo-level Slack delivery route and load the host-local Slack work-summary utility when the repo router declares one
- `xuunity product explain ...` or `xuunity product feature ...` -> `product/protocols/feature_explainer.md`
  - if the queried feature is represented by a project-local class that inherits from or delegates into a shared runtime layer, inspect that shared layer before answering
  - for gameplay projects that use a project-local gameplay bridge, flow-style explain requests should inspect the host-declared bridge entry artifact under `Assets/AIOutput/` first unless the current project router or project memory explicitly opts out of that path
- `xuunity product brief ...` or `xuunity product implementation brief ...` -> `product/protocols/implementation_brief.md`
- `xuunity product impact of this bug ...` or `xuunity product bug ...` -> `product/protocols/bug_impact_brief.md`
- `xuunity product impact ...` -> `product/protocols/change_impact.md`
- `xuunity product rollout readiness ...` or `xuunity product rollout ...` -> `product/protocols/rollout_readiness.md`
- `xuunity product deps ...` or `xuunity product dependency map ...` -> `product/protocols/dependency_map.md`
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


## System Utility Hints
Use these utilities when the task is about the protocol system itself:
- `utilities/review_artifact_extract.md` when the user wants a reusable `Engineering Review Artifact` from a long engineering chat, review discussion, or design thread
- `utilities/review_artifact_merge.md` when the user wants to consolidate multiple `Engineering Review Artifact` documents into one stronger reusable artifact
- `utilities/skill_extract.md` when the user provides new best practices or domain knowledge that should become reusable skills
- `utilities/skill_merge.md` when integrating new knowledge into existing skill families
- `utilities/sdk_vendor_research_profile_template.md` when the user wants to design or integrate a new `xuunity sdk discover <Vendor>` research profile for a third-party SDK
- `utilities/agent_private_bootstrap.md` when the user wants a new agent or project to remember how to route through shared `xuunity` without copying shared rules into private memory
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
- `utilities/system_self_evaluation.md` when auditing installation reachability, routing, public-layer boundaries, or corpus efficiency; keep this score separate from model fitness
- `utilities/system_protocol_clean_review.md` when the user wants a sanitary review-and-fix pass over public protocol docs, design registries, templates, routing maps, and current git changes
- `utilities/system_health_review.md` when orchestrating installation evidence, exact model-surface fixture evidence, conflicts, or a bounded one-candidate improvement loop
- `utilities/design_retro_review.md` when auditing a folder of design docs: scoring each for actuality, importance, implementation, and remaining effort against the live repo, then reconciling a prioritized registry and archiving retired designs
- `utilities/system_evaluation_cadence.md` when deciding whether the system should be evaluated now and how to act on the score
