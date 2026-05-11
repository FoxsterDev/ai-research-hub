# XUUnity Task: Validation Plan

## Goal
Define the validation package for a planned feature before or alongside implementation so quality checks are visible before code review time.

## Use For
- features with a concrete implementation plan
- changes that touch critical flows or multiple systems
- work that needs explicit QA coverage before coding starts
- features where validation must be planned, not improvised at the end

## Inputs
- implementation plan
- feature design brief
- project memory and project-specific constraints
- source code when current validation hooks or test surfaces need confirmation

## Process
1. Restate the implementation target:
   - target behavior
   - affected systems
   - critical flows touched
   - main implementation risks
2. Define validation coverage categories:
   - happy path
   - edge cases
   - lifecycle and async behavior
   - state recovery or resume behavior
   - platform-specific checks
   - regression-sensitive neighboring flows
3. Identify required manual QA scenarios:
   - core user journey checks
   - interruption or backgrounding cases
   - error or fallback cases
   - repeated-entry or duplicate-action cases
4. Identify candidate automated checks when evidence is sufficient:
   - unit-level logic checks
   - integration checks
   - smoke or regression checks
5. Choose the primary validation lane and any justified secondary lane:
   - use `knowledge/validation_lanes.md` as the canonical lane model
   - use `knowledge/unity_validation_boundaries.md` when evidence quality or build-sensitive proof surface matters
   - compact lane reminder:
     - `interactive_mcp` for integrated editor evidence
     - `batch_compile` for compile, matrix, deterministic narrow tests, and approved build-sensitive artifact proof
     - `scenario` for ordered runtime evidence
6. State the lane selection reason and expected evidence class:
   - why this lane is the narrowest representative proof
   - what evidence will count as success
7. Identify validation blockers:
   - missing observability
   - unclear acceptance criteria
   - unavailable test hooks
   - unclear environment or device coverage
8. Define release-sensitive checks when relevant:
   - monetization or reward integrity
   - save/load correctness
   - startup or initialization order
   - manifest, SDK, or platform constraints
9. Decide whether the planned evidence is trustworthy enough for the claim:
   - if the lane can start work but cannot provide trustworthy final accounting, downgrade the plan and keep the validation gap explicit
   - if artifact correctness is the real claim, prefer generated-build evidence over source-only inspection
   - if the question is long-running artifact production, prefer an approved batch lane over an interactive scenario waiter
10. Decide the next protocol step:
   - `delivery_risk_review.md` if the validation plan shows material rollout or breakage risk
   - `feature_development.md` if implementation can proceed with a clear validation package
   - stop and request clarification if acceptance criteria or validation surfaces are still too unclear

## Output
- Validation target summary
- Manual QA scenarios
- Edge-case coverage
- Lifecycle and async checks
- Platform-specific checks
- Candidate automated checks
- Validation contract:
  - `primary_validation_lane`
  - `secondary_validation_lane`
  - `lane_selection_reason`
  - `expected_evidence_class`
  - `validation_gaps`
- Validation blockers
- Recommended next protocol step

## Rules
- Do not wait until review time to decide how the feature will be validated.
- Keep validation proportional to risk, but never hide critical-flow checks.
- If current observability or test hooks are too weak, call that out as a blocker instead of pretending validation is complete.
- Distinguish required validation from optional nice-to-have coverage.
- Use the exact validation-contract field names from `knowledge/validation_contract.md`.
- Follow the shared lane and evidence rules from `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md` instead of redefining the full doctrine inside each plan.
- If the chosen lane cannot provide trustworthy final totals, terminal artifact completion, or terminal result accounting, keep that as a validation gap instead of treating the plan as sufficient.
- If repo or project rules require integrated validation, reflect that in the lane choice instead of planning a shell fallback.
