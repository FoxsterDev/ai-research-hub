# XUUnity Task: Feature Development

## Goal
Implement a new feature with production-safe architecture from the start.

## Focus
- Define data ownership, runtime flow, platform dependencies, and failure modes.
- Avoid avoidable startup cost and repeated bridge crossings.
- Design for observability and testability.
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

## Output
- Feature shape
- Managed and native responsibilities
- Risk areas
- Validation plan
