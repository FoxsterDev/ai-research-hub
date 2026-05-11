# XUUnity Low-Risk Validation And Artifact Gates Plan

Date: 2026-05-11
Status: implementation plan
Scope: validation and artifact gates before reduced-review AI work can be treated as low-risk

## Purpose
Define the gates that must pass before XUUnity can close a low-risk autonomous or reduced-review change.

This plan turns the autonomy model into an auditable delivery contract. The key rule is simple: no reduced-review claim without an artifact trail.

## Goal
Every `L2` or future `L3` change must leave enough evidence for a human to answer:
- why was this safe for the autonomy lane?
- what changed?
- what was excluded?
- what validation ran?
- what validation did not run?
- what remains risky?
- is this ready for commit, merge, or only local handoff?

## Gate Model
Use four gates:
1. classification gate
2. scope gate
3. validation gate
4. artifact gate

All four must pass before a change can be described as reduced-review-ready.

## Gate 1: Classification Gate
Required fields:
- `autonomy_level`
- `requested_action`
- `risk_class`
- `matched_policy_packs`
- `allowlist_category`
- `exclusion_result`
- `approval_status`

Pass conditions:
- task is classified as `L2` or approved future `L3`
- allowlist category is explicit
- no denylist or policy-pack exclusion applies
- requirements are not ambiguous
- owner or user approval exists where required

Fail conditions:
- touched behavior is unclear
- risk family is high or policy-pack-triggered without explicit approval
- task spans mixed safe and unsafe surfaces
- user asked for broad automation without a bounded scope

Failure action:
- downgrade to `L1`
- produce plan/review only
- ask for approval or narrowing if implementation is still desired

## Gate 2: Scope Gate
Required fields:
- `files_touched`
- `repo_surfaces`
- `runtime_effect`
- `denylist_paths_checked`
- `public_core_boundary_checked`
- `secrets_checked`
- `blast_radius`

Pass conditions:
- touched files match the allowlist category
- no excluded paths are touched
- runtime effect is none or explicitly non-critical
- public-core changes are public-safe
- no literal secrets are exposed
- blast radius is local and understandable

Fail conditions:
- production runtime code changed unexpectedly
- package, manifest, ProjectSettings, SDK, native, save/load, monetization, or startup files changed
- shared routing changed without review classification
- unknown generated files or build artifacts are included

Failure action:
- stop before commit
- split safe and unsafe work into separate units
- route unsafe work through normal review and validation

## Gate 3: Validation Gate
Required fields:
- `validation_lane`
- `commands_or_checks_run`
- `result`
- `representativeness`
- `validation_gap`
- `required_followup`

Allowed validation lanes:
- `source_review`
- `static_check`
- `unit_or_editmode_test`
- `playmode_or_integrated_test`
- `interactive_mcp`
- `batch_compile`
- `scenario`
- `not_applicable_docs_only`

Minimum by category:
- docs/report:
  - path placement check
  - public/private boundary check
  - secret redaction check
  - link/reference check where practical
- prompt/routing markdown:
  - reachability check with `rg`
  - conflict check against existing routing
  - system health review when routing surface materially changes
- test-only:
  - run affected tests when available
  - test-quality self-review
  - no production behavior change check
- editor tooling:
  - compile or source boundary check
  - editor-only assembly or platform guard check
  - dry-run if tool produces output
- registry/metadata:
  - schema/shape check
  - source path existence checks
  - before/after diff

Representativeness rules:
- source review is not runtime proof
- generated project-file build is not Unity runtime proof by default
- editor mock validation is not device/native proof
- `not_applicable_docs_only` is valid only when the change cannot affect runtime behavior

Fail conditions:
- validation lane does not match the claim
- command failed
- validation was skipped without a stated reason
- runtime claim is made from docs-only or source-only checks

Failure action:
- report validation gap
- do not claim reduced-review-ready
- either run the missing check or downgrade closure confidence

## Gate 4: Artifact Gate
Required artifact fields:
- `Summary`
- `Autonomy classification`
- `Scope`
- `Touched files`
- `Allowlist category`
- `Exclusion checks`
- `Risk classification`
- `Validation performed`
- `Validation gaps`
- `Residual risk`
- `Human gate`
- `Commit or handoff status`

Pass conditions:
- artifact can be copied into final answer, commit body, or task-registry event
- validation gap is explicit
- human merge gate is stated
- no secrets or project-private details are leaked into public artifacts

Fail conditions:
- artifact omits touched files
- artifact hides validation gaps
- artifact claims "safe" without allowlist evidence
- artifact uses vague status such as "looks good" or "validated" without proof

Failure action:
- regenerate artifact before closure
- do not create commit until staged diff and artifact match

## Required Shared Outputs
Implement as public-safe reusable core:
1. `AIRoot/Modules/XUUnity/reviews/autonomy_gate_review.md`
2. `AIRoot/Modules/XUUnity/utilities/autonomy_change_artifact.md`
3. `AIRoot/Modules/XUUnity/tasks/start_session.md` execution-contract fields for autonomy when relevant
4. Optional template:
   - `AIRoot/Templates/XUUNITY_AUTONOMY_CHANGE_ARTIFACT_TEMPLATE.md`

If template storage is not desirable in the first implementation, keep the artifact shape inside the review or utility file.

## Proposed Execution Contract Additions
For implementation tasks only, add:
- `autonomy_level`
- `allowlist_category`
- `exclusion_result`
- `human_gate`
- `artifact_required`

Example:
```text
autonomy_level: L2
allowlist_category: docs/report
exclusion_result: none
human_gate: commit allowed by explicit user request; merge not automatic
artifact_required: yes
```

## Commit Integration
When the user asks to commit reduced-review work:
- staged diff must match the artifact
- commit body should include:
  - `Why`
  - `What`
  - `Validation`
  - `Autonomy`

Suggested commit body field:
```text
Autonomy:
- Level: L2
- Category: docs/report
- Exclusions checked: no runtime, SDK, startup, native, manifest, monetization, save/load, or ProjectSettings surfaces touched
- Human gate: committed only after explicit user request
```

## Task Registry Integration
When task registry events are used, append autonomy metadata:
- `autonomy_level`
- `allowlist_category`
- `validation_lane`
- `validation_result`
- `human_gate_status`

Do not make task registry integration a blocker for the first implementation. The first blocker is a usable final-answer and commit artifact.

## Acceptance Criteria
The deliverable is done when:
- `L2` work cannot close without explicit classification, scope, validation, and artifact results
- validation requirements differ by category
- validation gaps are allowed but must downgrade confidence
- final answers and commit messages can reuse the same artifact facts
- future `L3` enablement has a stronger gate than `L2`
- no gate implies automatic merge or push

## Validation Plan
After implementing the gates, run sample dry-runs:
1. docs-only report creation:
   - should pass with `not_applicable_docs_only`
2. markdown routing update:
   - should require reachability and conflict checks
3. test-only addition:
   - should require test execution or explicit unavailable-test gap
4. package manifest update:
   - should fail scope gate
5. monetization callback fix:
   - should fail autonomy lane and route through policy-pack review

Expected result:
- safe categories produce concise artifacts
- excluded categories cannot pass by phrasing themselves as small changes
- final output gives a human enough evidence to accept, reject, or request more validation

## Rollout Plan
1. Implement gate review and artifact utility as public-safe files.
2. Wire them lightly from `tasks/start_session.md`.
3. Use gates manually in final answers before enforcing them broadly.
4. Add task-registry metadata only after the first manual artifacts prove stable.
5. Keep `L3` disabled until gate artifacts show repeated reliable `L2` outcomes.

## Risks
- gates become too verbose and slow normal work
- agents treat artifact creation as proof instead of evidence packaging
- validation gaps get reported but ignored
- commit bodies become noisy for tiny changes

## Controls
- activate autonomy gates only for implementation, commit, publish, or explicitly reduced-review requests
- keep artifacts compact and evidence-based
- require validation gap language when proof is weaker than the claim
- keep merge and push under explicit human/user control

## First Implementation Slice
Build the smallest useful version:
1. `reviews/autonomy_gate_review.md`
2. `utilities/autonomy_change_artifact.md`
3. start-session routing hook
4. five sample task classifications in the file body

Defer:
- task-registry schema changes
- automatic `L3`
- portfolio-wide batch gating
- dashboard metrics
