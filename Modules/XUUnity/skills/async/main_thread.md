# Skill: Main Thread

## Use For
- Unity object access
- callback handoff
- background-to-main-thread continuation review

## Rules
- Assume Unity objects require main-thread access unless project memory documents a safe exception.
- Be explicit about where thread hops happen.
- When an async API promises main-thread completion, enforce that promise at the final returned task completion boundary, not only at an intermediate callback or inner await point.
- Keep main-thread continuations short and allocation-light.
- Do not move expensive parsing, deserialization, or synchronization back onto the main thread without evidence.
- When a background pipeline fans back into Unity main-thread callbacks under potentially bursty load, bound each queue stage explicitly instead of relying on one unbounded backlog and one catch-up drain.
- When the component is core enough that callback floods can threaten frame stability, or when the requirements explicitly call for it, budget main-thread callback dispatch independently from background preparation.
  - do not add queue stages and dispatch budgets by default for tiny or low-risk flows
  - do add them when burst load, fan-out, or delayed catch-up can realistically stall the main thread or grow memory
- For best-effort or snapshot-like flows, prefer dropping old or stale queued work over letting backlog growth create long main-thread spikes.

## Review Focus
- thread affinity correctness
- final completion ownership for async wrappers
- continuation size
- main-thread stall risk
- queue and dispatch backpressure risk when callback load can burst
