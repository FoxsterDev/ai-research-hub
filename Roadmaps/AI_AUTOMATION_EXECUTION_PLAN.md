# AI Automation Execution Plan

## Purpose
This document turns the long-term roadmap into a practical 2-3 month execution plan.
It focuses on the highest-leverage work needed to move the current AI protocol system toward:
- scalable support for many Unity projects
- product-owner self-service
- lower routine tech lead review load
- safer AI-assisted feature delivery

## Time Horizon
- 8 to 12 weeks

## Execution Goals
By the end of this plan:
- the portfolio has a standard project AI baseline
- project memory quality and freshness are measurable
- feature work can follow structured AI delivery flows
- product owners can ask more implementation questions directly
- risky work routes into stronger review stacks automatically

## Success Criteria
- active projects have a consistent AI structure
- project memory freshness can be checked and reported
- feature requests can be routed through a standard implementation flow
- release and rollout questions produce more consistent answers
- routine tech lead review load drops for repeated low-risk change types

## Workstreams

## Workstream 1: Project Health And Freshness
Goal:
- make every project measurable as an AI-ready project

Deliverables:
- `xuunity project health audit` protocol
- `xuunity project memory freshness review` protocol
- standard scoring for:
  - structure completeness
  - project memory completeness
  - project memory freshness
  - report availability
  - AI readiness
- output template for project health reports

Definition of done:
- one command can audit a project and produce a health score
- one command can identify stale project memory by checking code against memory
- health report clearly identifies blockers

Priority:
- highest

## Workstream 2: Feature Delivery Protocols
Goal:
- replace open-ended feature prompting with structured AI delivery flows

Deliverables:
- `feature_request_intake.md`
- `feature_design_brief.md`
- `implementation_plan.md`
- `validation_plan.md`
- `delivery_risk_review.md`
- `rollout_plan.md`

Required behavior:
- classify feature risk
- identify touched critical flows
- identify required skills and reviews
- identify missing project memory
- produce a delivery package before code changes

Definition of done:
- a feature request can move from request to implementation-ready brief through a repeatable protocol
- the AI can explain why a given review stack was chosen

Priority:
- highest

## Workstream 3: Risk Routing And Policy Packs
Goal:
- route risky work into stronger review automatically

Deliverables:
- risk classes:
  - low
  - moderate
  - high
  - critical
- policy packs for:
  - SDK changes
  - startup changes
  - monetization changes
  - save/load changes
  - manifest and native changes
  - UI-heavy screen flows
- routing rules in `start_session.md`

Definition of done:
- risky tasks auto-load stronger review stacks
- the user can see what triggered the stronger stack
- policy-based review becomes repeatable across projects

Priority:
- highest

## Workstream 4: Product Owner Self-Service
Goal:
- reduce engineering interruption for implementation-detail questions

Deliverables:
- expand product protocols for:
  - current behavior explanation
  - implementation summary
  - impact analysis
  - rollout readiness
  - dependency map
  - bug impact
- standard response format:
  - answer
  - risk
  - what can break
  - what to validate
  - verification status
- product-owner command guide update

Definition of done:
- product owner can ask common implementation-detail questions without custom prompting
- verification status is always visible and consistent

Priority:
- high

## Workstream 5: Review Artifact Pipeline
Goal:
- make engineering reasoning reusable instead of ephemeral

Deliverables:
- finalize `review_artifact_extract`
- finalize `review_artifact_merge`
- define output storage recommendation for reusable review artifacts
- connect artifact pipeline with `knowledge_intake_review`

Definition of done:
- long engineering chats can be turned into reusable review artifacts
- multiple artifacts on the same topic can be consolidated
- useful artifacts can feed shared knowledge intentionally

Priority:
- high

## Workstream 6: Portfolio Registry
Goal:
- stop managing projects only through folder discovery

Deliverables:
- project registry file or folder
- metadata per project:
  - project type
  - active platform targets
  - monetization stack
  - AI readiness score
  - project memory status
  - known critical flows
- lightweight project index command or report

Definition of done:
- there is one machine-readable place to understand the portfolio
- cross-project prioritization becomes easier

Priority:
- medium-high

## Workstream 7: Low-Risk Autonomy Lane
Goal:
- define what AI can safely do with minimal human review

Deliverables:
- autonomy level model
- low-risk change categories
- explicit exclusion list
- required validation and artifact generation before merge

Definition of done:
- it is clear which changes AI may implement with reduced review
- tech leads only review exceptions, not every low-risk routine change

Priority:
- medium

## Recommended Sequence

### Sprint 1
- project health audit
- project memory freshness review
- scoring and report format
- minimum project memory checklist

### Sprint 2
- feature request intake
- feature design brief
- implementation plan
- validation plan

### Sprint 3
- risk classes
- policy packs for SDK, startup, and manifest changes
- auto-routing updates in `start_session.md`

### Sprint 4
- product protocol refinement
- product-owner quick workflows
- review artifact pipeline finalization

### Sprint 5
- portfolio registry
- low-risk autonomy model
- first autonomy-safe task categories

## Concrete Deliverables To Build First
1. `AIRoot/Modules/XUUnity/product/protocols/project_health_audit.md`
2. `AIRoot/Modules/XUUnity/product/protocols/project_memory_freshness.md`
3. `AIRoot/Modules/XUUnity/tasks/feature_request_intake.md`
4. `AIRoot/Modules/XUUnity/tasks/feature_design_brief.md`
5. `AIRoot/Modules/XUUnity/tasks/implementation_plan.md`
6. `AIRoot/Modules/XUUnity/reviews/delivery_risk_review.md`
7. `AIRoot/Modules/XUUnity/knowledge/risk_classification.md`
8. host registry file in `AIOutput/Registry/`

## Decision Rules
- if a deliverable improves many projects at once, build it before project-specific polish
- if a deliverable reduces stale context risk, build it before more automation
- if a deliverable reduces tech lead routine review load, prioritize it over cosmetic protocol cleanup
- if a deliverable increases autonomy, require stronger validation before rollout

## Metrics To Watch Weekly
- number of projects with valid project memory
- number of projects with freshness-reviewed memory
- number of feature requests handled through structured protocol flow
- number of product questions answered with code verification
- number of risky changes routed through policy packs
- number of reusable review artifacts created

## Maintenance Backlog

### Extraction Evidence Governance
Goal:
- close the remaining governance gap for extraction-health evidence without blocking product work

Backlog item:
- run the authoritative approval flow for the current extraction baseline using:
  - `AIRoot/Operations/XUUNITY_EXTRACTION_AUTHORITATIVE_APPROVAL_CHECKLIST.md`
  - `AIOutput/Reports/System/knowledge_extraction_eval_baseline_v1_run.json`
  - `AIRoot/Operations/knowledge_extraction_eval.py report --write-back`

Done when:
- the current extraction run is either explicitly approved as authoritative human-scored evidence or explicitly replaced by a newer approved run
- `AIOutput/Reports/System/knowledge_extraction_eval_latest_summary.json` is no longer `non_authoritative`

Priority:
- medium

Notes:
- this is a governance and evidence-quality task, not a runtime or product blocker
- do not complete it without real human review of the run bundle

## Expected Constraints
- some projects will have poor or missing project memory
- some project routers will drift from the standard
- product-facing answers will initially vary in quality until verification and output contracts stabilize
- autonomy should remain narrow until risk routing and validation are mature

## What Not To Do In This Window
- do not try to automate full end-to-end coding for all change types yet
- do not expand role or skill taxonomy aggressively unless it solves repeated delivery friction
- do not treat stale project memory as acceptable for product-facing explanations
- do not push heavy portfolio orchestration before project health scoring exists

## Final Priority Order
1. project health and freshness
2. structured feature delivery
3. risk routing and policy packs
4. product-owner self-service
5. review artifact reuse
6. project registry
7. low-risk autonomy

## Final Position
The next 2-3 months should not be spent on adding more prompt volume.

They should be spent on:
- making project truth measurable
- making delivery structured
- making risk routing explicit
- making product queries safer
- making reusable engineering reasoning durable

That is the shortest path to scaling from a useful prompt system to a portfolio operating system.
