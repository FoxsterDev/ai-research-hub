# Skill: Integration Tests

## Use For
- subsystem boundaries
- SDK wrappers
- async orchestration
- save/load and remote-config flows

## Rules
- Follow `testing_doctrine.md` as the baseline testing policy.
- Test boundaries where failures are expensive and easy to miss in isolated unit tests.
- For SDK wrappers, prefer contract-first integration tests over implementation-detail mirroring.
- Keep owned production orchestration real and use fakes only at true external boundaries.
- Cover callback ordering, retries, fallback paths, and invalid external data.
- Use integration tests to protect critical flows from regressions during refactors.
- Keep external dependency behavior controlled and explicit.
- Include failure-path coverage for hanging SDK calls, thrown exceptions, malformed data, and background-thread callbacks.
- Verify retry behavior after failed initialization and verify concurrency protection when the same init flow is triggered more than once.
- For SDK wrappers with mirrored state, verify rollback or state preservation after failed mirror updates instead of testing only happy-path mutation.
- For SDK wrappers with multiple launch paths, verify path separation explicitly so native and browser flows cannot silently collapse into the same orchestration path.
- Distinguish public-contract validation from real device/native bridge validation. Controlled fake-backed coverage is valid for contract checks but is not equivalent to proof of real bridge correctness on device.
- Prefer test doubles and fake-backed boundary tests over adding broad runtime fake branches into shipping production paths.
- Native components may be mocked in Unity EditMode or PlayMode integration tests, but the Unity-side orchestration above that native boundary should remain real.
- For wrappers and platform facades, assert the real default contract of the wrapper boundary rather than a nearby custom-configured storage or adapter instance.
- For request-shaped native bridges, test failure phases separately: duplicate in-flight rejection, scheduling failure before the platform thread accepts work, and execution failure after the platform thread starts the accepted request.
- For callback-driven SDK wrappers, lock stable guarantees first:
  - early validation failures follow the documented public thread contract
  - accepted async completions arrive on the documented thread
  - accepted async failure completions caused after platform-thread handoff still arrive on the documented thread
  - callback lifetime matches actual launch registration rather than speculative pre-registration
- Prefer explicit device-validation coverage or manual validation protocol for real Android/iOS bridge behavior instead of treating shipping runtime test seams as the default answer.
- For mobile-sensitive changes, use the mobile validation ladder from `testing_doctrine.md` instead of stopping at fake-backed integration success.
- For consent and compliance-sensitive integrations, verify partial-accept and partial-deny paths instead of testing only all-accept and all-deny cases.
