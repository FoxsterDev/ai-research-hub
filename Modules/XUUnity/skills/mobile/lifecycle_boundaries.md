# Skill: Mobile Lifecycle Boundaries

## Use For
- Unity runtime services that wrap focus, pause, resume, and background behavior
- mobile foreground/background state modeling
- mobile save-on-background or interruption-safe persistence design

## Rules
- Separate raw Unity lifecycle signals from derived consumer-facing app state.
- Keep the high-level lifecycle model product-meaningful. Avoid exposing raw callback-order combinations unless product logic truly needs them.
- Treat Android transient `focus=false` carefully because keyboard, overlays, and dialogs can trigger focus loss without true backgrounding.
- Treat iOS focus loss as an early save-sensitive signal. Do not rely on `OnApplicationQuit` as the main persistence boundary on mobile.
- Centralize mobile persistence heuristics behind a lifecycle-owned save signal instead of repeating platform branches across consumers.
- Keep `Application.lowMemory` handling bounded through dirty-state awareness and repeated-call suppression when heavy persistence would otherwise spam.

## Review Focus
- lifecycle contract clarity
- Android interruption behavior
- iOS suspend and save behavior
- save-boundary ownership
- low-memory resilience
