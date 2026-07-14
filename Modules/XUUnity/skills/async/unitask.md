# Skill: UniTask

## Use For
- gameplay-facing async flows
- PlayerLoop-integrated async
- low-allocation Unity async work

## Rules
- Prefer `UniTask` for Unity-centric async flows when project memory does not require another primitive.
- Keep `UniTask` boundaries explicit when interacting with `.NET Task` or SDK callbacks.
- If outer coordination already owns multi-caller semantics, keep inner callback latches on `UniTask` primitives too unless a `Task` boundary is truly required.
- For shared single-flight work, a caller's cancellation must stop only that caller's wait; only the owning coordinator may cancel the shared operation.
- Use `Forget` only when the flow is intentionally detached and exception handling is explicit.
- Avoid unnecessary conversions between `UniTask` and `.NET Task`.
- A `.Timeout()` on a scoped/`using` `UnityWebRequest` `ToUniTask` does not cancel the inner operation. On timeout the method returns and disposes the request while the poller is still registered, which then reads `.result`/`Abort()` on a disposed request (NRE). Drive the timeout from a linked `CancellationTokenSource` that cancels the awaited op, so the request aborts while still alive.
- Schedule that timeout cancel with UniTask `CancelAfterSlim` (fires `Cancel()` on the PlayerLoop / main thread), not `CancellationTokenSource.CancelAfter` (thread-pool `Timer`). Dispose the `CancelAfterSlim` handle to stop the timer. Keep `cancelImmediately:false` (default): the source observes cancellation in its main-thread `MoveNext`, aborts the live op, and unsubscribes via `TryReturn`; `cancelImmediately:true` runs abort + continuation on the canceller's thread and can leave the source registered for a post-dispose re-poll.

## Review Focus
- correct use of `UniTask`
- `Forget` safety
- conversion boundaries
- allocation discipline
