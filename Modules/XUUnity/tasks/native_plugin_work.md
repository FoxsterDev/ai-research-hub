# XUUnity Task: Native Plugin Work

## Goal
Implement or review Android and iOS bridge code safely.

## Focus
- JNI, ARC, callback lifetime, threading, and ownership
- marshaling cost and startup impact
- minimum OS support constraints
- platform-specific implementation split and ownership boundaries
- prompt, permission, and app-lifecycle readiness for startup-sensitive native calls
- test strategy for direct bridge entrypoints, lifecycle timing, and delayed callbacks
- explicit API threading contract:
  - main-thread-only by design
  - or fully thread-safe if the user requires it

## Output
- Boundary design
- Platform-specific hazards
- Test plan
- Release risks
