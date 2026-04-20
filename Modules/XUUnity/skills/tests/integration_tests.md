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
- For callback-driven SDK wrappers, lock stable guarantees first:
  - early validation failures stay synchronous on the caller thread
  - accepted async completions arrive on the correct thread
  - callback lifetime matches actual launch registration rather than speculative pre-registration
- For consent and compliance-sensitive integrations, verify partial-accept and partial-deny paths instead of testing only all-accept and all-deny cases.
