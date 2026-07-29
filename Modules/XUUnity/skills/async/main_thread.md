# Skill: Main Thread

## Use For
- Unity object access
- callback handoff
- background-to-main-thread continuation review

## Rules
- Assume Unity objects require main-thread access unless project memory documents a safe exception.
- Be explicit about where thread hops happen.
- When an async API promises main-thread completion, enforce that promise at the final returned task completion boundary, not only at an intermediate callback or inner await point.
- For `await using (UniTask.ReturnToMainThread())`, the hop to main happens when the async-using
  scope is disposed. If an awaited inner operation resumes on a background thread, code still inside
  the scope can run there; put Unity-bound finalization after the scope or explicitly hop before it.
- Keep main-thread continuations short and allocation-light.
- Do not move expensive parsing, deserialization, or synchronization back onto the main thread without evidence.
- When a background pipeline fans back into Unity main-thread callbacks under potentially bursty load, bound each queue stage explicitly instead of relying on one unbounded backlog and one catch-up drain.
- When the component is core enough that callback floods can threaten frame stability, or when the requirements explicitly call for it, budget main-thread callback dispatch independently from background preparation.
  - do not add queue stages and dispatch budgets by default for tiny or low-risk flows
  - do add them when burst load, fan-out, or delayed catch-up can realistically stall the main thread or grow memory
- For best-effort or snapshot-like flows, prefer dropping old or stale queued work over letting backlog growth create long main-thread spikes.
- When the value a Unity API returns is stable for the session (device identifier, permission status, app version, build metadata), prefer publishing it once from a known main-thread point and reading plain fields at the call site over hopping to main at the touch point. Reserve hops for values that must be read live. A published snapshot also removes the thread precondition from every future caller, and it is testable from a background thread.
- Adding the first Unity API read to a method that previously touched none silently changes the thread contract of every caller. Map the resumption thread of the call path you attach to, not of the code you write: an upstream `SwitchToThreadPool`, or a `.NET Task` await with `ConfigureAwait(false)`, can leave even a UI-facing presenter chain on a pool thread. Tracing one producer and generalizing to the rest is not a trace.
- An exception thrown before an orchestration layer's return-to-main scope propagates on the foreign thread, so downstream disposal and UI teardown run there too. Adding one new throw site can turn a latent off-main teardown path into a reproducible crash.

## Review Focus
- thread affinity correctness
- final completion ownership for async wrappers
- continuation size
- main-thread stall risk
- queue and dispatch backpressure risk when callback load can burst
- session-stable values read live on a path whose thread affinity the caller does not own
