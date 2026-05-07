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
- In Unity test environments that do not reliably support `async Task` methods under plain `[Test]`, do not rely on async NUnit helpers such as `Assert.DoesNotThrowAsync(...)`.
- If the target runner reports `Method has non-void return value, but no result is expected`, rewrite the test to a synchronous `[Test]` and wait explicitly with `GetAwaiter().GetResult()` when the contract being checked is still synchronous from the caller point of view.
- Do not use reflection against project-owned code in tests when an explicit seam, test double, or accessible contract type can express the scenario directly.
- For project-owned code that lives in the repo and can be changed safely, prefer narrow `internal` seams plus `InternalsVisibleTo` over reflection when non-public access is required.
- Reflection in tests is reserved for external closed boundaries only:
  - Unity engine internals
  - Unity-owned package cache code that the repo does not own
  - precompiled third-party SDKs or closed DLLs
  - manifest-resolved read-only external packages that cannot be safely reshaped in the repo
- Do not add `#if UNITY_INCLUDE_TESTS` branches to shipping code by default just to satisfy tests.
- Do not widen inheritance surface, add `virtual`, or unseal types primarily for tests when an `internal` seam or real contract path is sufficient.
- Prefer a test-only subclass, explicit protected seam, or test double only when that shape already matches the runtime design and is cleaner than adding a repo-owned `internal` seam.
- Use production-code test hooks only in the rare case where the maintenance and design cost is clearly lower than the alternative and the seam remains narrow, intentional, and non-public.
