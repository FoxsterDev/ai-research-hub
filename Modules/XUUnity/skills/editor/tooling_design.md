# Skill: Tooling Design

## Use For
- internal workflow tools
- content and configuration helpers
- editor-loop background services (bridges, watchers, pollers)

## Rules
- Build tools that reduce human error in content, build, and release flows.
- Prefer explicit workflows over magic automation.
- Make destructive actions obvious and reversible.
- Keep editor tools fast enough for daily use on large projects.

## Destructive Actions
- Choose the failure *direction* deliberately, independently of accuracy. When a detector's output authorizes deletion, every failure path — source unreachable, unparseable, empty, or a partial read — must resolve to *nothing to delete*, never to *everything is unreferenced*.
- Re-derive the authority at the moment of the destructive call, not from the list computed for display. Between the scan and the click another actor can publish; delete only the intersection of the fresh authority with the requested set, and log what was skipped.
- A paginated listing that callers treat as "the complete contents" must refuse to return a partial page. A truncated success is more dangerous than a slow failure.
- Name the environment and the concrete items in the confirmation, and require a second confirmation for the environment that reaches end users.

## Long Operations And Feedback
- Do not treat a rendered progress overlay as permission to block the editor main thread. Structure long work as asynchronous I/O plus main-thread Unity API steps, or as bounded chunks that return control between updates; keep progress and cancellation responsive throughout. Yielding a frame after showing an overlay is only a presentation aid for short, bounded synchronous work, not a fix for a long blocking operation.
- Publish refreshed state at the *end* of a refresh. Clearing the backing collections up front renders a genuinely empty model for the whole fetch, which reads to the user as "nothing found" rather than "loading".
- Make a running refresh visible as its own state, distinct from the empty state, and make long operations cancellable when a partially applied result is recoverable — say plainly in the status what a cancelled operation left behind.

## Background Service Loops
- Work driven from `EditorApplication.update` runs on the editor main thread even when throttled to an interval; a throttled tick still cannot afford to block.
- No `Thread.Sleep`, no unbounded blocking I/O, no synchronous socket send without a send timeout anywhere tick-reachable code can go.
- On resource contention, degrade instead of waiting: attempt the preferred path, retry immediately a bounded number of times, then fall back to a legacy behavior the other side of the contract tolerates (see `knowledge/file_ipc_atomicity.md` for the IPC instance of this ladder).
- Throttle by interval, early-out on idle before any I/O, and keep per-tick allocations near zero (cache what cannot change within a domain, e.g. the process id).
- Enforce the no-sleep rule with a package-wide contract test plus an explicit allowlist for documented on-demand exceptions; reviewer vigilance does not survive the next contributor.
