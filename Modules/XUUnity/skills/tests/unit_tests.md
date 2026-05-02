# Skill: Unit Tests

## Use For
- pure logic
- deterministic rules
- utility and service behavior

## Rules
- Follow `testing_doctrine.md` as the baseline testing policy.
- Unit test logic with stable inputs and outputs.
- Keep as much owned production logic real as practical, even in unit-level coverage.
- Do not fake confidence by unit testing trivial wrappers only.
- Prioritize logic that protects progression, economy, state transitions, and error handling.
- Keep tests deterministic and fast enough for regular execution.
- Do not use reflection against project-owned code in tests when an explicit seam, test double, or accessible contract type can express the scenario directly.
- Reflection in tests is acceptable only when the touched API surface belongs to Unity, a precompiled third-party SDK, or another closed module that the project does not control.
- Do not add `#if UNITY_INCLUDE_TESTS` branches to shipping code by default just to satisfy tests.
- Prefer a test-only subclass, explicit protected seam, or test double over compile-flag branches in production code.
- Use production-code test hooks only in the rare case where the maintenance and design cost is clearly lower than the alternative and the seam remains narrow and intentional.
