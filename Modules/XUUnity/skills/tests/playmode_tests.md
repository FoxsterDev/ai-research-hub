# Skill: PlayMode Tests

## Use For
- scene flows
- runtime object interactions
- UI and gameplay integration

## Rules
- Use PlayMode tests for runtime behavior that cannot be trusted in pure unit tests.
- Target critical user flows rather than broad shallow coverage.
- Keep setup cost low enough that tests remain maintainable.
- Validate pause, resume, scene reload, and lifecycle-sensitive behavior where relevant.
- For package-based code, keep test discovery compatible with Unity Test Runner by placing package tests under the package root `Tests/` area and using a dedicated PlayMode test asmdef.
- For package or SDK contract coverage, fake-backed PlayMode tests are valid for public contract verification, but do not treat them as proof of real native/device bridge correctness.
- For `UniTask`-driven runtime behavior, prefer `UnityTest` with `IEnumerator` and `UniTask.ToCoroutine(...)` instead of `async Task` test methods.
- Keep test-only helpers in test assemblies rather than production assemblies, and avoid redundant compile guards inside files that already live behind a test asmdef.
