# Skill: Integration Tests

## Use For
- subsystem boundaries
- SDK wrappers
- async orchestration
- save/load and remote-config flows

## Rules
- Test boundaries where failures are expensive and easy to miss in isolated unit tests.
- Cover callback ordering, retries, fallback paths, and invalid external data.
- Use integration tests to protect critical flows from regressions during refactors.
- Keep external dependency behavior controlled and explicit.
- Include failure-path coverage for hanging SDK calls, thrown exceptions, malformed data, and background-thread callbacks.
- Verify retry behavior after failed initialization and verify concurrency protection when the same init flow is triggered more than once.
- For consent and compliance-sensitive integrations, verify partial-accept and partial-deny paths instead of testing only all-accept and all-deny cases.
