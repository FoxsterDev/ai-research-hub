# Skill: Mobile Runtime Safety

## Use For
- any runtime implementation on mobile
- startup, resume, pause, and interruption-sensitive work

## Rules
- Prefer predictable runtime behavior over clever abstractions.
- Avoid blocking main-thread work in startup, UI transitions, scene changes, ads, rewards, and save/load.
- Keep allocations, reflection, and hidden synchronization out of hot paths.
- Treat battery, thermal, and low-memory behavior as production constraints, not edge cases.
- Any callback path must be null-safe, ownership-safe, and failure-tolerant.

## Review Focus
- frame stability
- allocation pressure
- lifecycle correctness
- callback ownership
