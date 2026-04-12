# Skill: Cancellation

## Use For
- `CancellationToken`
- timeouts
- shutdown and destroy-safe async flows

## Rules
- The owner of cancellation must be clear from the API shape.
- Propagate cancellation through nested async calls unless there is a deliberate containment boundary.
- Tie async lifetime to object, scene, or app lifecycle where relevant.
- Timeouts must protect user-facing flows and external dependencies without masking root-cause failures.
- Black-box SDK operations that can hang should have a bounded timeout or equivalent escape path.
- Timeout policy should allow the app to recover control of the critical flow instead of waiting indefinitely on vendor behavior.
- Cooperative cancellation alone is not enough when the lower layer may ignore cancellation or hang outside your control.
- Native or external calls that can block, deadlock, or wait on non-cooperative systems should have a bounded recovery path beyond the caller token alone.

## Review Focus
- token ownership
- propagation correctness
- lifecycle cleanup
- timeout behavior
