# Skill: PlayMode Tests

## Use For
- scene flows
- runtime object interactions
- UI and gameplay integration

## Rules
- Follow `testing_doctrine.md` as the baseline testing policy.
- Use PlayMode tests for runtime behavior that cannot be trusted in pure unit tests.
- Target critical user flows rather than broad shallow coverage.
- Keep setup cost low enough that tests remain maintainable.
- Validate pause, resume, scene reload, and lifecycle-sensitive behavior where relevant.
- When a runtime service uses `DontDestroyOnLoad`, engine message methods, or runtime-managed object lifetime, default lifecycle integration coverage to PlayMode instead of forcing it into EditMode.
- For package-based code, keep test discovery compatible with Unity Test Runner by placing package tests under the package root `Tests/` area and using a dedicated PlayMode test asmdef.
- For package or SDK contract coverage, fake-backed PlayMode tests are valid for public contract verification, but do not treat them as proof of real native/device bridge correctness.
- Native components may be mocked in PlayMode tests, but keep the owned Unity orchestration above that boundary real.
- For `UniTask`-driven runtime behavior, prefer `UnityTest` with `IEnumerator` and `UniTask.ToCoroutine(...)` instead of `async Task` test methods.
- Keep test-only helpers in test assemblies rather than production assemblies, and avoid redundant compile guards inside files that already live behind a test asmdef.
- PlayMode lifecycle coverage should still leave pure policy and state-machine logic in EditMode tests when those parts can be exercised without engine object setup.

## Runtime Evidence Loop
Use this loop when a user-visible claim depends on live scene wiring, real input routing, Unity object lifetime, lifecycle transitions, async ordering, or rendered runtime state, and the fix is expected to change it. It is not mandatory for copy-only or static visual claims that a narrower representative check can prove.

- Execute the red in the lane that owns the claim. `testing_doctrine.md` requires proving a regression guard by executing its red; when the claim depends on live runtime behavior, use a failing PlayMode reproduction. When controlled external input or a payload is required, inject it through an existing production-valid boundary; otherwise drive the real user or input path. An EditMode mutation red proves only the behavior that lane can express.
- Keep the same reproduction as the green. The artifact of record is that test passing after the fix, in the same lane, plus the evidence class the validation contract named for it - scene snapshot, screenshot, console marker, or hook payload (`knowledge/validation_contract.md`).
- Record where that evidence can be retrieved next to the claim. An evidence class with no retrievable artifact is a validation gap, not a pass.
- Bound the iteration before starting: a fixed number of fix-then-reverify cycles, then stop and report the ranked hypotheses the runs ruled out and what each would have shown. Repeating the same failing cycle past that budget produces no new evidence.
- Authorization is owned by the selected validation path. For a newly designed UI smoke, follow `reviews/policy_packs/ui_heavy_changes.md`; an explicit user request to execute validation satisfies first-run authorization unless the proposed smoke materially expands the requested scope or risk. Non-UI PlayMode work does not inherit that UI-specific gate and follows the active repo or project execution contract.
- The loop does not upgrade the lane. An editor-integrated green stays editor-integrated evidence, and device-native behavior remains unproven unless a device lane ran (`knowledge/unity_validation_boundaries.md`).
