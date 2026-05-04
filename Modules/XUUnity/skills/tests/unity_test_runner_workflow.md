# Skill: Unity Test Runner Workflow

## Use For
- running Unity `EditMode` or `PlayMode` tests from automation
- diagnosing stalled or blocked Unity test execution
- package-level runtime validation
- turning rough timing checks into trustworthy performance evidence

## Rules
- Before launching Unity test automation, verify whether the current repo or project allows direct shell-launched Unity validation.
- If Unity test execution is blocked because another Unity instance already has the project open, say that explicitly instead of treating the run as an unexplained hang.
- If the intended Unity editor is blocked by an already open project instance, check whether a nearby installed Unity version is available and not currently holding the same project lock.
- Use that nearby version only as a controlled fallback when the task needs momentum and the validation claim tolerates version-neighbor evidence.
- When using a nearby Unity version as fallback, say so explicitly and record both:
  - the intended editor version
  - the fallback editor version actually used
- Do not present fallback-version results as exact proof for version-specific bugs, package-resolution differences, platform-toolchain issues, or engine-regression claims.
- Prefer a narrow `-testFilter` run first when stabilizing a new suite or isolating failures. Expand to broader suites only after the focused path is green.
- If the change touches shared setup, teardown, static reset helpers, or file-level test infrastructure, do not stop after the narrow `-testFilter` pass. Expand to the full test file or closest shared suite slice before calling the fix stable.
- For Unity suites that use static state, global callbacks, `LogAssert`, singleton services, or persisted local files, explicitly check for order-dependent failures by running more than one test from the file in the same process.
- Use `EditMode` for deterministic logic, mapping rules, merge behavior, and small runtime-independent invariants.
- Use `PlayMode` for frame progression, dispatch-to-main-thread behavior, scene or lifecycle-sensitive flows, and runtime target execution paths.
- For package-style Unity code, keep test discovery compatible with Unity Test Runner by using dedicated `Tests/` asmdefs for `EditMode`, `PlayMode`, and performance suites where needed.
- Do not assume plain NUnit `[Test]` methods can safely return `async Task` in every Unity test environment.
- If the runner reports `Method has non-void return value, but no result is expected`, treat that as a runner-compatibility issue rather than a production-code failure.
- In that case, prefer one of these shapes:
  - synchronous `[Test]` with explicit waiting such as `GetAwaiter().GetResult()` when the caller contract is effectively synchronous
  - `[UnityTest]` with `IEnumerator` for frame-driven async behavior
  - `UniTask.ToCoroutine(...)` when the project flow is `UniTask`-based and needs Unity-runner-compatible async execution
- When a test depends on synchronously waiting for async teardown or disposal, treat Unity `SynchronizationContext` capture as a deadlock risk.
- If the test or teardown path may block synchronously, internal awaited tasks should avoid resuming onto the blocked Unity context.
- Do not describe `Stopwatch`, `Time.realtimeSinceStartup`, or `GC.GetAllocatedBytesForCurrentThread()` checks as full performance evidence when the Unity performance package is absent.
- If real performance metrics are required, install and use `com.unity.test-framework.performance` and report that the evidence is package-based performance measurement rather than smoke timing.
- Keep the confidence level honest:
  - helper or pure logic tests are not runtime-path proof
  - `EditMode` and `PlayMode` proof are not physical device or native observability proof
  - fake-backed target tests are not equivalent to real Android or iOS bridge validation
- Keep assertion channels honest:
  - a Unity console assertion is not the same as a logger-target assertion
  - a callback capture is not the same as a persisted side effect
  - a custom recording target is not the same as `LogAssert`
- When a test starts failing after review cleanup, verify whether the code path still works but now emits through a different observation channel before rewriting production code or weakening the test.
- When Unity validation cannot be executed representatively, make the validation gap explicit instead of silently hanging, downgrading the claim, or substituting weaker proof without saying so.

## Reviewer Focus
- was the blocked runner cause diagnosed clearly
- was the narrowest representative suite used first
- was the suite widened appropriately after shared harness changes
- is the evidence level matched to the claim
- are performance claims backed by the correct measurement layer
