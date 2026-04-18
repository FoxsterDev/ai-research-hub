# XUUnity Prompt Family

## Purpose
Shared public module for Unity mobile engineering across projects.
Use it as the default execution layer for project work in Unity.
It covers bug fixing, refactoring, feature development, code review, SDK integration, SDK review, native plugin work, native plugin review, runtime safety, platform bridge code, performance, and store compliance.
It should assume Unity `6000+`, mobile production targets, zero-crash and zero-ANR expectations, no microfreezes on critical flows, and strong performance discipline by default.
This module is the public-safe `xuunity` core. In this monorepo, it may be extended by `AIModules/XUUnityInternal/` as an internal shared overlay.

Canonical module path:
- `AIRoot/Modules/XUUnity/`

Internal overlay when present in this host repo:
- `AIModules/XUUnityInternal/`

Canonical session entrypoint:
- `tasks/start_session.md`
- do not look for `start_session.md` at the module root

## Standard Layering
1. One primary file from `role/` and optional supporting role files only when the task benefits from multiple angles
2. One or more files from `codestyle/`
3. One file from `tasks/`
4. Baseline safety skills from `skills/core/`
5. One or more relevant files from `skills/` only if triggered by the task
6. One or more files from `reviews/` or `utilities/`
7. Platform files from `platforms/` only if relevant
8. Project memory from `Assets/AIOutput/ProjectMemory/`
9. Previous outputs from `Assets/AIOutput/` only if they help the current task

For gameplay-project `project memory freshness` or first-readiness audits, host-local onboarding/bootstrap artifacts in `Assets/AIOutput/` may also be used as seed evidence when `ProjectMemory/` is still sparse. Resolve the exact evidence set from the host repo router, project router, or local memory rules. They do not replace curated durable memory.

In this monorepo, `xuunity` may also load `AIModules/XUUnityInternal/` after the public core and before project-local memory when internal shared overlays are relevant.

## Task Coverage
- `tasks/start_session.md`
- `tasks/bug_fixing.md`
- `tasks/refactoring.md`
- `tasks/feature_request_intake.md`
- `tasks/feature_design_brief.md`
- `tasks/implementation_plan.md`
- `tasks/validation_plan.md`
- `tasks/rollout_plan.md`
- `tasks/feature_development.md`
- `tasks/code_review.md`
- `tasks/sdk_integration.md`
- `tasks/native_plugin_work.md`
- `tasks/incident_response.md`

## Review Coverage
- `reviews/delivery_risk_review.md`
- `reviews/feature_code_review.md`
- `reviews/git_change_review.md`
- `reviews/sdk_code_review.md`
- `reviews/sdk_breakage_review.md`
- `reviews/native_plugin_review.md`
- `reviews/architecture_review.md`
- `reviews/release_readiness_review.md`
- `reviews/policy_packs/sdk_changes.md`
- `reviews/policy_packs/startup_changes.md`
- `reviews/policy_packs/manifest_native_changes.md`

## Utility Coverage
- `utilities/README.md`
- `utilities/knowledge_extract.md`
- `utilities/implementation_pattern_extract.md`
- `utilities/knowledge_extraction_triage.md`
- `utilities/knowledge_merge.md`
- `utilities/knowledge_ingest_from_chat.md`
- `utilities/knowledge_ingest_from_link.md`
- `utilities/knowledge_ingest_from_book.md`
- `utilities/skill_extract.md`
- `utilities/skill_merge.md`
- `utilities/review_artifact_extract.md`
- `utilities/review_artifact_merge.md`
- `utilities/knowledge_intake_review.md`
- `utilities/knowledge_integration.md`
- `utilities/system_progress_review.md`
- `utilities/system_registry_refresh.md`
- `utilities/system_project_registry_audit.md`
- `utilities/internet_research_watch.md`
- `utilities/system_self_evaluation.md`
- `utilities/system_health_review.md`
- `utilities/system_output_cleanup.md`
- `utilities/system_output_cleanup_scorecard_template.md`
- `utilities/system_output_cleanup_apply.md`
- `utilities/system_evaluation_cadence.md`
- `utilities/external_promotion_checklist.md`
- `utilities/report_export.md`

## Product Coverage
- `product/README.md`
- `product/protocols/feature_explainer.md`
- `product/protocols/implementation_brief.md`
- `product/protocols/change_impact.md`
- `product/protocols/rollout_readiness.md`
- `product/protocols/dependency_map.md`
- `product/protocols/bug_impact_brief.md`
- `product/protocols/project_health_audit.md`
- `product/protocols/project_memory_freshness.md`
- `product/output/product_summary_format.md`
- `product/output/project_health_report_format.md`

## Platform Coverage
- `platforms/android.md`
- `platforms/ios.md`
- `platforms/performance.md`
- `platforms/store_compliance.md`

Platform files are a thin platform-specific overlay.
Load the relevant shared skills first, then use `platforms/` for Android-only, iOS-only, device-only, or submission-only checks that remain after shared skill review.

## Knowledge Base
- `knowledge/glossary.md`
- `knowledge/decision_rules.md`
- `knowledge/risk_classification.md`
- `knowledge/ios_passive_network_monitoring.md`
- `knowledge/sdk_stability_scoring.md`
- `knowledge/severity_matrix.md`

Some reusable SDK version-comparison methodology is intentionally stored in `knowledge/` instead of `skills/` because it is decision support, not direct implementation behavior.
Shared risk classification is also stored in `knowledge/` because it is routing doctrine for task assembly, not a code-style or implementation skill by itself.
Knowledge files are not a default bundle.
Load them only when `tasks/start_session.md` or a narrower review or utility file explicitly triggers them.

## Risk Routing
`XUUnity` can strengthen the stack for risky work without turning every task into a broad review bundle.

The initial shared policy-pack surface is:
- `reviews/policy_packs/sdk_changes.md`
- `reviews/policy_packs/startup_changes.md`
- `reviews/policy_packs/manifest_native_changes.md`

These policy packs are review-routing overlays.
They compose existing `reviews/`, `skills/`, `knowledge/`, and `platforms/` files.
They should be selected through `tasks/start_session.md` only when the task's dominant breakage surface warrants them.

## Code Style
- `codestyle/README.md`
- `codestyle/csharp.md`
- `codestyle/unity.md`
- `codestyle/native.md`

Any AI work using XUUnity should load the relevant code style guidance from `codestyle/` before implementation or review.

## Roles
- `role/base_role.md`
- `role/product_owner.md`
- `role/senior_unity_developer.md`
- `role/architect.md`
- `role/technical_developer.md`
- `role/technical_artist.md`
- `role/ui_integrator.md`
- `role/qa_manual.md`
- `role/qa_automation.md`
- `role/researcher.md`
- `role/troubleshooter_master.md`

Use one primary role per task.
If the user explicitly asks for a role, load that role instead of defaulting to `role/base_role.md`.
If the user does not specify a role, `XUUnity` should infer the best primary role from the task.
For complex tasks, `XUUnity` may also use a small role group so the problem is evaluated from multiple useful angles without bloating the stack.

## Role Routing
The canonical role-routing rules live in `tasks/start_session.md`.
This file only defines the available role pack and the general contract:
- exactly one primary role is selected for every task
- supporting roles are optional and should stay minimal
- role routing should reduce ambiguity, not add prompt weight

## Skills
`XUUnity` may load task-specific skill packs from `skills/`.
The baseline safety posture should always include `skills/core/`.
First-class skill families include:
- `async/`
- `ui/`
- `editor/`
- `audio/`
- `fx/`
- `shaders/`
- `optimization/`
- `profiling/`
- `tests/`
- `architecture/`
- `mobile/`
- `sdk/`
- `native/`

Skill packs should be loaded by shorthand intent, code signals, and project context, then narrowed by project memory and `SkillOverrides/` when present.
If a skill family is matched, the implementation or review context is incomplete without that skill layer.

## Shared Layer Contract
- `AIRoot/Modules/XUUnity/` is the public-safe reusable core.
- `AIModules/XUUnityInternal/` is the monorepo-internal shared overlay when the host repo provides it.
- Project memory remains the highest-priority durable layer after the target project is known.
- Internal overlay guidance may narrow public core behavior for monorepo-specific cases, but should not duplicate the public tree without need.

## System Commands
`XUUnity` may also be used to evolve and audit its own protocol system.

Recommended short commands:
- `xuunity review the git change`
- `xuunity git change review`
- `xuunity feature screen this flow`
- `xuunity feature popup this flow`
- `xuunity feature presenter this flow`
- `xuunity rollout plan this feature`
- `xuunity feature rollout plan this flow`
- `xuunity extract knowledge`
- `xuunity extract this source`
- `xuunity extract implementation pattern`
- `xuunity extract presenter pattern`
- `xuunity system extract knowledge`
- `xuunity system extract implementation pattern`
- `xuunity apply approved extraction`
- `xuunity system apply approved extraction`
- `xuunity system extract review artifact from this chat`
- `xuunity system merge these async best practices`
- `xuunity system merge review artifacts`
- `xuunity system integrate review artifacts`
- `xuunity system intake review this knowledge`
- `xuunity system integrate approved knowledge`
- `xuunity intake this knowledge`
- `xuunity integrate approved knowledge`
- `xuunity system evaluate the protocol structure`
- `xuunity system progress review`
- `xuunity system registry refresh`
- `xuunity system project registry audit`
- `xuunity system research watch`
- `xuunity system health review`
- `xuunity system cleanup`
- `xuunity system cleanup projects`
- `xuunity system cleanup reports`
- `xuunity system cleanup all`
- `xuunity system cleanup apply`
- `xuunity system apply cleanup`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system evaluation cadence`
- `xuunity product explain this feature`
- `xuunity product brief this system`
- `xuunity product impact this flow change`
- `xuunity product rollout this feature`
- `xuunity product deps this popup`
- `xuunity product bug this issue`
- `xuunity product health this project`
- `xuunity project memory freshness this project`
- `xuunity feature risk review this flow`
