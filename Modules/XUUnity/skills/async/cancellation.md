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
- Do not tear a `CancellationTokenSource` field down with the `_cts?.Cancel(); _cts?.Dispose();` idiom when more than one proven execution context can reach it. For confirmed cross-thread teardown, take ownership atomically with `Interlocked.Exchange(ref _cts, null)`, then cancel and dispose the taken instance while containing `ObjectDisposedException`.
- Do not copy that atomic teardown recipe onto unrelated UI flags or main-thread-confined presenter state. For same-thread reentrant teardown, transfer ownership through one plain owner state and make completion idempotent.
- Capture the token as a local before publishing a freshly created CTS to a shared field, and await on that local. Never re-read `_field.Token` after publishing — a concurrent teardown can null or dispose the field between publish and read.

## Review Focus
- token ownership
- propagation correctness
- lifecycle cleanup
- timeout behavior
