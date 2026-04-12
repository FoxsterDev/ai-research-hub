# Skill: Main Thread

## Use For
- Unity object access
- callback handoff
- background-to-main-thread continuation review

## Rules
- Assume Unity objects require main-thread access unless project memory documents a safe exception.
- Be explicit about where thread hops happen.
- Keep main-thread continuations short and allocation-light.
- Do not move expensive parsing, deserialization, or synchronization back onto the main thread without evidence.

## Review Focus
- thread affinity correctness
- continuation size
- main-thread stall risk
