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
- Separate raw Unity lifecycle signals from derived consumer-facing app state when wrapping focus, pause, resume, and background behavior.
- Keep the high-level lifecycle model product-meaningful. If most consumers only need foreground versus background, expose one clear background state instead of multiple raw callback-order combinations.
- Keep mobile save heuristics behind the lifecycle boundary rather than scattering iOS and Android persistence branches across feature consumers.
- Treat `Application.lowMemory` as a bounded pressure signal, not as an instruction to run unbounded repeated heavy persistence.
- Gate low-memory-driven persistence through dirty state, cooldown, or recent-save suppression where appropriate.

## Review Focus
- frame stability
- allocation pressure
- lifecycle correctness
- callback ownership
- mobile save-path correctness
