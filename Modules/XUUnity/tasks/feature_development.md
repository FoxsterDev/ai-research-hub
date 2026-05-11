# XUUnity Task: Feature Development

## Goal
Implement a new feature with production-safe architecture from the start.

## Focus
- Define data ownership, runtime flow, platform dependencies, and failure modes.
- Avoid avoidable startup cost and repeated bridge crossings.
- Design for observability and testability.
- Carry forward the current validation contract during implementation instead of re-deciding it only at closeout.
- Treat `skills/tests/testing_doctrine.md` as a default development constraint for this task.
- Do not default to writing tests too early while the feature shape is still moving.
  - Prefer adding or finalizing tests near the end of the implementation once the runtime behavior and seams are stable enough to validate cleanly.
  - If tests are optional or materially expensive relative to the task, ask the user whether they want tests instead of spending token budget automatically.
  - If the feature risk, regression surface, or an explicit user request clearly requires tests, say so briefly and proceed.
- If new tests are authored, run a quick self-review against the testing doctrine before closure.
  - Check at minimum:
    - real owned code versus fake-heavy coverage
    - seam cleanliness
    - readability
    - whether any newly added test should be simplified, replaced, or deleted

## Implementation Contract
- Keep the current execution contract visible while coding:
  - `primary_validation_lane`
  - `secondary_validation_lane`
  - `lane_selection_reason`
  - `expected_evidence_class`
  - `validation_gaps`
  - `required_validation`
  - `required_self_review`
- If implementation changes the feature shape enough to change the proof surface, update the contract before continuing.
- If the feature touches build-sensitive outputs, keep the expected evidence class explicit during implementation.
- If the planned lane cannot provide trustworthy final accounting for the changed implementation shape, keep the validation gap explicit instead of silently weakening the proof target.

## Validation During Development
- Prefer the narrowest representative proof while the feature is still moving.
- Use the exact validation-contract field names from `knowledge/validation_contract.md`.
- Follow `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md` as the canonical lane and evidence doctrine during implementation.
- If observability is too weak to prove the intended behavior, treat that as implementation work to add or expose the right evidence surface.

## Output
- Feature shape
- Managed and native responsibilities
- Risk areas
- Validation contract:
  - `primary_validation_lane`
  - `secondary_validation_lane`
  - `lane_selection_reason`
  - `expected_evidence_class`
  - `validation_gaps`
- Required validation:
  - `required_validation`
- Validation plan
