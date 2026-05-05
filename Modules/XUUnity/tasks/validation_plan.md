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
   - `interactive_mcp` for live editor-state, console, scene, Game View, play mode, or integrated tool evidence
   - `batch_compile` for non-interactive compile, define-matrix, build-target, or deterministic narrow test evidence when direct shell automation is allowed
   - `scenario` for ordered runtime steps, waits, play mode transitions, screenshots, or project-defined hooks
6. Identify validation blockers:
   - missing observability
   - unclear acceptance criteria
   - unavailable test hooks
   - unclear environment or device coverage
7. Define release-sensitive checks when relevant:
   - monetization or reward integrity
   - save/load correctness
   - startup or initialization order
   - manifest, SDK, or platform constraints
8. Decide the next protocol step:
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
- Primary validation lane
- Secondary validation lane
- Lane selection reason
- Validation blockers
- Recommended next protocol step

## Rules
- Do not wait until review time to decide how the feature will be validated.
- Keep validation proportional to risk, but never hide critical-flow checks.
- If current observability or test hooks are too weak, call that out as a blocker instead of pretending validation is complete.
- Distinguish required validation from optional nice-to-have coverage.
- Do not use `batch_compile` as proof for claims that require play mode, Game View, scene-state, or other interactive editor evidence.
- If repo or project rules require integrated validation, reflect that in the lane choice instead of planning a shell fallback.
