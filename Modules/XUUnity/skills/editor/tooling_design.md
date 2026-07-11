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

## Background Service Loops
- Work driven from `EditorApplication.update` runs on the editor main thread even when throttled to an interval; a throttled tick still cannot afford to block.
- No `Thread.Sleep`, no unbounded blocking I/O, no synchronous socket send without a send timeout anywhere tick-reachable code can go.
- On resource contention, degrade instead of waiting: attempt the preferred path, retry immediately a bounded number of times, then fall back to a legacy behavior the other side of the contract tolerates (see `knowledge/file_ipc_atomicity.md` for the IPC instance of this ladder).
- Throttle by interval, early-out on idle before any I/O, and keep per-tick allocations near zero (cache what cannot change within a domain, e.g. the process id).
- Enforce the no-sleep rule with a package-wide contract test plus an explicit allowlist for documented on-demand exceptions; reviewer vigilance does not survive the next contributor.
