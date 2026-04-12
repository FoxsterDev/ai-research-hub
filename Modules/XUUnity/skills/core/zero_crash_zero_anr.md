# Skill: Zero Crash Zero ANR

## Use For
- all runtime code
- SDK callbacks
- native bridge code
- async work

## Rules
- No unhandled exceptions in runtime, startup, callback, async, or shutdown paths.
- Catch only where recovery, fallback, logging, or escalation is explicit.
- Do not introduce waits, locks, sync-over-async, or blocking I/O on the main thread.
- Treat ANR risk as a release blocker for startup, scene loading, monetization, and resume flows.
- If a failure cannot be fully prevented, contain it and protect the critical flow.
- Do not assume lower native, OS, driver, or network layers will honor cooperative cancellation in a timely way.
- On hang-prone external paths, prefer bounded recovery and control return over waiting indefinitely for perfect cleanup.

## Review Focus
- unhandled exception risk
- ANR risk
- blocking work on main thread
- failure containment
