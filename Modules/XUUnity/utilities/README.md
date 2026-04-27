# XUUnity System Operations

## Purpose
This folder contains `XUUnity` utilities for:
- knowledge ingestion
- skill extraction and merge
- output routing
- protocol self-evaluation
- system health review
- evaluation cadence decisions

Use this folder when the task is about improving the prompt system itself, not only solving a product feature or bug.

## Main Flows

### Unified Extraction Triage
Use when the user wants one command that evaluates a source artifact and decides what can become a review artifact, a skill update, public core knowledge, internal shared knowledge, or a project-only override.

Flow:
1. `knowledge_extraction_triage.md`
2. post-extraction retrospective when the source is a development or review session
3. review package for user approval
4. `knowledge_integration.md` only after explicit approval

Short commands:
- `xuunity extract knowledge`
- `xuunity extract this source`
- `xuunity system extract knowledge`
- `xuunity system extract this source`

Apply commands after review:
- `xuunity apply approved extraction`
- `xuunity system apply approved extraction`
- `xuunity apply approved`

### Comparative Implementation Pattern Extraction
Use when the user wants to learn how this repo actually implements a repeated code pattern from two or more real examples.

This is the better fit for requests such as:
- extract how presenters are built from `HomePresenter` and `LobbyPresenter`
- extract the house style for startup orchestration from multiple bootstrappers
- extract the shared popup-flow pattern from several concrete presenters

Flow:
1. `implementation_pattern_extract.md`
2. review the extracted invariants, local variations, and non-promoted quirks
3. route the approved pattern into public core, internal shared, or project-local knowledge

Short commands:
- `xuunity extract implementation pattern`
- `xuunity extract presenter pattern`
- `xuunity system extract implementation pattern`
- `xuunity system extract presenter pattern`

Routing rule for approved extraction:
- public-safe shared reusable guidance -> `AIRoot/Modules/XUUnity/`
- monorepo-internal shared reusable guidance -> `AIModules/XUUnityInternal/`
- project-only durable guidance -> `Assets/AIOutput/ProjectMemory/`
- project-specific skill overrides -> `Assets/AIOutput/ProjectMemory/SkillOverrides/`
- project-scoped reports and drafts -> `Assets/AIOutput/`
- external promotion only after explicit public-safety review

### Knowledge To Skills
Use when the user provides new reusable engineering guidance.

Flow:
1. `knowledge_ingest_from_chat.md`, `knowledge_ingest_from_link.md`, or `knowledge_ingest_from_book.md`
2. `skill_extract.md`
3. `skill_merge.md`
4. `knowledge_merge.md` if the knowledge also affects non-skill shared prompts

Short commands:
- `xuunity system extract skill candidates`
- `xuunity system merge these async best practices`

### Review Artifact Extraction
Use when the user wants to convert a long engineering chat or design discussion into a reusable review artifact.

Flow:
1. `review_artifact_extract.md`
2. optional `knowledge_intake_review.md` if the resulting artifact should update shared prompts

Short commands:
- `xuunity system extract review artifact from this chat`
- `xuunity system extract review artifact from this discussion`

### Review Artifact Merge
Use when the user already has two or more review artifacts and wants one stronger canonical artifact.

Flow:
1. `review_artifact_merge.md`
2. optional `knowledge_intake_review.md` if the merged artifact should update shared prompts

Short commands:
- `xuunity system merge review artifacts`
- `xuunity system merge these review artifacts`
- `xuunity system integrate review artifacts`

### Knowledge Intake Review
Use when the user wants one command that evaluates whether new knowledge is worth integrating at all.

Flow:
1. `knowledge_intake_review.md`
2. review report for user approval
3. `knowledge_integration.md` only after explicit approval

Short commands:
- `xuunity system intake review this knowledge`
- `xuunity system integrate approved knowledge`

### System Progress Review
Use when the user wants to know where the current AI system stands and what milestone should come next.

Flow:
1. `system_progress_review.md`
2. optional `system_self_evaluation.md` or `system_health_review.md` if structural issues block progress

Short commands:
- `xuunity system progress review`
- `xuunity system next milestone`

### System Registry Refresh
Use when the user wants to refresh portfolio project metadata from the current monorepo structure.

Flow:
1. `system_registry_refresh.md`
2. optional `system_progress_review.md` if the refreshed registry should be used in the same review pass

Short commands:
- `xuunity system registry refresh`
- `xuunity system refresh project registry`

### System Project Registry Audit
Use when the user wants to validate registry freshness without modifying it by default.

Flow:
1. `system_project_registry_audit.md`
2. optional `system_registry_refresh.md` if the audit finds clear low-risk metadata drift

Short commands:
- `xuunity system project registry audit`
- `xuunity system registry audit`

### Internet Research Watch
Use when the user wants periodic external research focused on improving the current AI system and tools.

Flow:
1. `internet_research_watch.md`
2. optional `knowledge_intake_review.md` for strong findings worth integrating

Short commands:
- `xuunity system research watch`
- `xuunity system research what is new`

### System Output Cleanup
Use when the user wants to reduce AI-generated clutter, archive stale reports, and identify near-zero-value artifacts safely.

Flow:
1. `system_output_cleanup.md`
2. review the cleanup plan
3. `system_output_cleanup_apply.md` only after explicit approval

Short commands:
- `xuunity system cleanup`
- `xuunity system cleanup projects`
- `xuunity system cleanup reports`
- `xuunity system cleanup all`
- `xuunity system cleanup apply`
- `xuunity system apply cleanup`
- `xuunity system apply approved cleanup`
- `xuunity system cleanup stale reports`
- `xuunity system cleanup ai outputs`
- `xuunity system archive old reports`
- `xuunity system audit ai clutter`

## System Audit
Use when validating the protocol system itself.

Flow:
1. `system_self_evaluation.md`
2. `system_health_review.md` if conflicts, redundancy, or dead paths are suspected
3. `system_evaluation_cadence.md` to decide whether cleanup is required now

Short commands:
- `xuunity system evaluate the protocol structure`
- `xuunity system health review`
- `xuunity system evaluation cadence`

## Utility Map
- `knowledge_extract.md`
  - turn validated implementation insights into reusable rules
- `implementation_pattern_extract.md`
  - compare two or more concrete implementations and extract the reusable development pattern, not just generic durable rules
- `knowledge_extraction_triage.md`
  - read one source, run a retrospective when the source is a development or review session, and propose the right split across review artifacts, skills, shared knowledge, and project-only outputs
- `review_artifact_extract.md`
  - turn long engineering chats or discussions into reusable `Engineering Review Artifact` documents
- `review_artifact_merge.md`
  - merge multiple `Engineering Review Artifact` documents into one stronger canonical artifact
- `knowledge_ingest_from_chat.md`
  - ingest knowledge from chat and run a retrospective pass when the chat exposes reusable process or protocol lessons
- `knowledge_ingest_from_link.md`
  - ingest knowledge from external references
- `knowledge_ingest_from_book.md`
  - ingest knowledge from books or long-form notes
- `knowledge_merge.md`
  - merge reusable knowledge into the smallest correct target
- `skill_extract.md`
  - turn new knowledge into candidate skills
- `skill_merge.md`
  - merge new knowledge into `skills/`
- `knowledge_intake_review.md`
  - process one knowledge input into a review package and stop before integration
- `knowledge_intake_review_report_template.md`
  - standard output template for knowledge intake review reports
- `knowledge_integration.md`
  - apply only the approved parts of a reviewed knowledge package
- `external_promotion_checklist.md`
  - decide whether knowledge should be promoted to an optional external reusable repo
- `system_progress_review.md`
  - assess current roadmap progress and recommend the next milestone
- `system_registry_refresh.md`
  - refresh `AIOutput/Registry/project_registry.yaml` from current repo evidence
- `system_project_registry_audit.md`
  - audit `AIOutput/Registry/project_registry.yaml` against current repo evidence
- `internet_research_watch.md`
  - periodically research external developments that could improve the current system
- `system_self_evaluation.md`
  - score stability, quality, professionalism, and usefulness
- `system_health_review.md`
  - find conflicts, duplicates, and cleanup priorities
- `system_output_cleanup.md`
  - classify stale reports and AI-generated clutter into keep, archive, delete-candidate, and manual-review buckets
- `system_output_cleanup_scorecard_template.md`
  - standard scoring template for cleanup decisions across keep, archive, delete-candidate, and manual-review outcomes
- `system_output_cleanup_apply.md`
  - execute only the explicitly approved cleanup actions from a reviewed cleanup plan
- `system_evaluation_cadence.md`
  - decide when evaluation should run and how to act on the score
- `report_export.md`
  - route generated outputs into `Assets/AIOutput/`

## Rules
- Keep public-safe shared reusable guidance in `AIRoot/Modules/XUUnity/`.
- Keep monorepo-internal shared reusable guidance in `AIModules/XUUnityInternal/`.
- Keep project-specific exceptions in `Assets/AIOutput/ProjectMemory/`.
- Keep project-specific skill-like exceptions in `Assets/AIOutput/ProjectMemory/SkillOverrides/`.
- Do not merge new knowledge into shared prompts without checking for duplication and conflicts first.
- Prefer small corrective changes over broad rewrites when auditing the system.
- Do not skip strong reusable knowledge only because no existing skill family matches it yet.
- Never include literal secret values in generated AI outputs. Redact credentials and report only the field name, file path, and presence when sensitive config evidence matters.
- Do not treat reusable outputs as automatically public-safe. Public core and internal shared are separate routing decisions.
- Never delete AI outputs as part of cleanup without explicit user approval. Cleanup protocols may audit, classify, and recommend actions, but deletion requires a user-approved apply step with a safety rationale.
