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
- Use `EditMode` for deterministic logic, mapping rules, merge behavior, and small runtime-independent invariants.
- Use `PlayMode` for frame progression, dispatch-to-main-thread behavior, scene or lifecycle-sensitive flows, and runtime target execution paths.
- For package-style Unity code, keep test discovery compatible with Unity Test Runner by using dedicated `Tests/` asmdefs for `EditMode`, `PlayMode`, and performance suites where needed.
- When a test depends on synchronously waiting for async teardown or disposal, treat Unity `SynchronizationContext` capture as a deadlock risk.
- If the test or teardown path may block synchronously, internal awaited tasks should avoid resuming onto the blocked Unity context.
- Do not describe `Stopwatch`, `Time.realtimeSinceStartup`, or `GC.GetAllocatedBytesForCurrentThread()` checks as full performance evidence when the Unity performance package is absent.
- If real performance metrics are required, install and use `com.unity.test-framework.performance` and report that the evidence is package-based performance measurement rather than smoke timing.
- Keep the confidence level honest:
  - helper or pure logic tests are not runtime-path proof
  - `EditMode` and `PlayMode` proof are not physical device or native observability proof
  - fake-backed target tests are not equivalent to real Android or iOS bridge validation
- When Unity validation cannot be executed representatively, make the validation gap explicit instead of silently hanging, downgrading the claim, or substituting weaker proof without saying so.

## Reviewer Focus
- was the blocked runner cause diagnosed clearly
- was the narrowest representative suite used first
- is the evidence level matched to the claim
- are performance claims backed by the correct measurement layer
