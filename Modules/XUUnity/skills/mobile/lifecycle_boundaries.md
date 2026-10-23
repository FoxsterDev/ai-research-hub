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
- Do not rely on the relative order of `OnApplicationPause` / `OnApplicationFocus` across unrelated MonoBehaviours, such as third-party or vendor scripts you do not control. A consumer that reacts in its own callback and reads another component's lifecycle-derived state can see it before or after that component's update; subscribe consumers to the lifecycle owner's events instead.
- Publish transition facts, such as how long the app was away and whether it was backgrounded, as the payload of a lifecycle event raised at the transition, rather than as queryable "last value" state that later readers must validate for freshness.

## Review Focus
- lifecycle contract clarity
- Android interruption behavior
- iOS suspend and save behavior
- save-boundary ownership
- low-memory resilience
