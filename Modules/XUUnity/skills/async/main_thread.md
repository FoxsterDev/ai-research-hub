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

## Review Focus
- thread affinity correctness
- final completion ownership for async wrappers
- continuation size
- main-thread stall risk
