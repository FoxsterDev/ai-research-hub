# XUUnity Low-Risk Autonomy Level Model Plan

Date: 2026-05-11
Status: implementation plan
Scope: next shared XUUnity autonomy deliverable after Workstream 3 policy-pack coverage

## Purpose
Define the shared autonomy-level model from `L0` through `L4` so XUUnity can say what the AI may do, what requires approval, and what must stay human-led.

This plan is for the public-core protocol implementation. It should be converted into shared prompt files only after review.

## Source Constraints
- `AIRoot/Roadmaps/AI_AUTOMATION_ROADMAP.md` defines:
  - `L0`: answer only
  - `L1`: analyze and propose
  - `L2`: implement with human approval
  - `L3`: implement and validate low-risk scoped changes automatically
  - `L4`: portfolio-wide batch automation for approved patterns
- `AIRoot/Roadmaps/AI_AUTOMATION_EXECUTION_PLAN.md` requires:
  - autonomy level model
  - low-risk change categories
  - explicit exclusion list
  - required validation and artifact generation before merge
- `AIRoot/Design/XUUNITY_LOW_RISK_AUTONOMY_DESIGN.md` already establishes the safest posture:
  - allowlist autonomy
  - deny by default
  - no autonomous edits to runtime-critical production paths
  - merge remains human-gated in the current portfolio phase
- Workstream 3 policy packs are now complete, so autonomy can reference the risk-routing surface instead of inventing a parallel risk model.

## Design Goal
Create one stable shared model that answers:
- what level applies to this task
- what actions are allowed at that level
- what approval is required
- what validation is mandatory
- what evidence must be reported before closure
- when the task must be downgraded to a lower autonomy level

## Proposed Level Definitions

### `L0`: Answer Only
Use when:
- the user asks for an explanation, comparison, status, or read-only summary
- source evidence is unclear
- the task is exploratory, product-facing, or policy-shaping
- the work touches a sensitive domain but no implementation is requested

Allowed:
- read files
- inspect current state
- summarize behavior
- identify risks
- propose options

Not allowed:
- edit files
- stage, commit, push, or publish
- run destructive commands
- claim validation beyond evidence

Required output:
- answer or analysis
- evidence status
- uncertainty and next-step recommendation when needed

### `L1`: Analyze And Propose
Use when:
- implementation may be useful, but risk, ownership, scope, or acceptance criteria are not yet settled
- the work touches production runtime code, SDKs, startup, native, manifests, monetization, save/load, compliance, or broad architecture
- the user asks for a plan, review, or design before implementation

Allowed:
- inspect source
- classify risk
- build implementation plan
- identify validation strategy
- draft patch proposal

Not allowed without explicit user approval:
- edit production code
- create commits
- broaden scope beyond the requested plan

Required output:
- risk class
- matched policy packs
- implementation boundary
- validation plan
- approval question or clear next action

### `L2`: Implement With Human Approval Or Explicit User Request
Use when:
- the user explicitly asks to implement, create, update, or fix
- the task is inside an allowlisted low-risk category
- the blast radius is local and understandable
- denylist surfaces are not touched

Allowed:
- edit files in the approved scope
- run non-destructive validation
- produce validation and review artifacts
- create commits when explicitly requested

Not allowed:
- autonomous merge to protected branches
- push or publish unless explicitly requested
- modify excluded surfaces
- treat weak validation as full runtime proof

Required output:
- scope classification
- files changed
- validation performed
- validation gaps
- residual risk

### `L3`: Implement And Validate Low-Risk Scoped Changes Automatically
Current status:
- disabled by default for production code
- permitted only for future explicitly approved categories after repeated successful `L2` executions

Candidate future use:
- docs and AI artifact cleanup
- generated report index refresh
- strictly mechanical metadata refresh
- tests that do not change production behavior

Required before enabling:
- allowlist category exists
- exclusion rules exist
- validation gates exist
- artifact contract exists
- task history proves repeated successful `L2` outcomes
- human owner approves promotion

Required output:
- same as `L2`
- plus autonomy-level justification and artifact-gate result

### `L4`: Portfolio-Wide Batch Automation For Approved Patterns
Current status:
- disabled

Candidate future use:
- portfolio-wide report-index refresh
- mechanical project registry refresh
- repeated approved prompt or metadata migration after a pilot proves safety

Required before enabling:
- explicit batch scope
- project registry source of truth
- dry-run artifact
- rollback or no-op strategy
- per-project result reporting
- human approval before write or merge

Not allowed in current phase:
- production runtime code edits
- SDK, startup, native, manifest, monetization, save/load, or compliance changes
- broad architecture rewrites

## Default Portfolio Policy
- `L0`: always available for read-only answers
- `L1`: default for ambiguous, risky, architecture, or production-runtime work
- `L2`: available only for explicit user-requested implementation in allowlisted categories
- `L3`: disabled until allowlisted categories prove repeated success
- `L4`: disabled until batch automation governance exists

## Required Shared Outputs
Implement the level model as public-safe reusable core:
1. `AIRoot/Modules/XUUnity/knowledge/autonomy_levels.md`
2. `AIRoot/Modules/XUUnity/tasks/start_session.md` autonomy-routing hook
3. Optional later review overlay:
   - `AIRoot/Modules/XUUnity/reviews/autonomy_gate_review.md`

Do not write host-private names into the public core. If host-local policy needs additional controls, route them through a host-local overlay.

## Routing Integration Plan
Update `tasks/start_session.md` to derive:
- `autonomy_level`
- `autonomy_reason`
- `allowlist_status`
- `denylist_status`
- `approval_required`
- `required_validation`
- `required_artifact`

Add the autonomy fields to the execution contract only when the task asks for implementation, commit, publish, or reduced-review work. Do not burden ordinary answers with autonomy metadata.

## Level Selection Rules
Start every implementation request at `L1` until proven eligible for `L2`.

Promote to `L2` only when:
- the user explicitly asked for edits or commit work
- the category is allowlisted
- no denylist surface is touched
- the blast radius is local
- validation can be stated before closure

Downgrade to `L1` when:
- requirements are ambiguous
- ownership is unclear
- touched files are mixed risk
- validation cannot prove the claim
- policy-pack routing triggers a high-risk family

Block `L3` or `L4` unless:
- a shared policy says the category is enabled
- the task history proves repeated safe execution
- an owner has approved the promotion

## Acceptance Criteria
The deliverable is done when:
- every XUUnity implementation task can classify itself as `L0`, `L1`, `L2`, `L3`, or `L4`
- the model has clear defaults and downgrade rules
- `L2` cannot be inferred only from small diff size
- production-runtime sensitive work defaults to `L1` or stricter
- the model integrates with existing risk classes and policy packs
- final answers can report the autonomy level without excessive ceremony

## Validation Plan
Run source-level checks after implementation:
- verify `autonomy_levels.md` exists and is referenced by `tasks/start_session.md`
- verify no public-core file includes host-private examples
- verify routing does not conflict with existing risk-classification or policy-pack rules
- run a prompt-surface review against sample tasks:
  - docs-only change
  - test-only change
  - UI runtime change
  - monetization bug
  - save/load migration
  - SDK upgrade

Expected results:
- docs-only and test-only can reach `L2` when explicitly requested
- production runtime risk stays at `L1` unless explicitly approved and separately validated
- policy-pack-triggered critical flows never become `L2` by default

## Rollout Plan
1. Add `knowledge/autonomy_levels.md`.
2. Add start-session routing hooks.
3. Add sample classification examples.
4. Run a system health review focused on routing conflicts.
5. Use the model for several real tasks without enabling `L3`.
6. Only after repeated clean results, consider specific `L3` candidates.

## Risks
- The model could create false confidence if level names sound like permission to skip review.
- Agents may over-promote small runtime changes to `L2`.
- `L3` and `L4` may be misunderstood as current capabilities instead of disabled future states.

## Controls
- `L2` requires allowlist and no denylist intersection.
- `L3` and `L4` explicitly disabled by default.
- Policy-pack triggers downgrade autonomy unless a stronger reviewed policy says otherwise.
- Final answers must report validation gaps plainly.
