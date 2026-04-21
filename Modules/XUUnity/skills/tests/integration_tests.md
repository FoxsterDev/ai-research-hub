# Skill: Integration Tests

## Use For
- subsystem boundaries
- SDK wrappers
- async orchestration
- save/load and remote-config flows

## Rules
- Test boundaries where failures are expensive and easy to miss in isolated unit tests.
- For SDK wrappers, prefer contract-first integration tests over implementation-detail mirroring.
- Cover callback ordering, retries, fallback paths, and invalid external data.
- Use integration tests to protect critical flows from regressions during refactors.
- Keep external dependency behavior controlled and explicit.
- Include failure-path coverage for hanging SDK calls, thrown exceptions, malformed data, and background-thread callbacks.
- Verify retry behavior after failed initialization and verify concurrency protection when the same init flow is triggered more than once.
- For SDK wrappers with mirrored state, verify rollback or state preservation after failed mirror updates instead of testing only happy-path mutation.
- For SDK wrappers with multiple launch paths, verify path separation explicitly so native and browser flows cannot silently collapse into the same orchestration path.
- Distinguish public-contract validation from real device/native bridge validation. Controlled fake-backed coverage is valid for contract checks but is not equivalent to proof of real bridge correctness on device.
- Prefer test doubles and fake-backed boundary tests over adding broad runtime fake branches into shipping production paths.
- For callback-driven SDK wrappers, lock stable guarantees first:
  - early validation failures follow the documented public thread contract
  - accepted async completions arrive on the documented thread
  - callback lifetime matches actual launch registration rather than speculative pre-registration
- Prefer explicit device-validation coverage or manual validation protocol for real Android/iOS bridge behavior instead of treating shipping runtime test seams as the default answer.
- For consent and compliance-sensitive integrations, verify partial-accept and partial-deny paths instead of testing only all-accept and all-deny cases.
