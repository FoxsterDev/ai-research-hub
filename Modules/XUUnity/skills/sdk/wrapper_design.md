# Skill: SDK Wrapper Design

## Use For
- third-party SDK wrapper APIs
- consent, analytics, attribution, ads, push, and monetization wrappers
- black-box SDK integration boundaries

## Rules
- Treat third-party SDKs as zero-trust boundaries.
- Do not leak third-party data structures into core application logic.
- Map SDK models to internal safe structs or DTOs immediately at the wrapper boundary.
- Keep public wrapper interfaces stateless where possible.
- Prefer explicit current-state reads such as `TryGet...(...)` plus future-change events over replay-on-subscribe or other subscription-side side effects.
- Do not expose convenience properties that collapse `unknown`, `not started`, and real negative state into the same public value.
- For cross-platform wrapper diagnostics, prefer one explicit verbosity threshold such as `MinLogLevel` over several loosely coupled platform-specific debug booleans when the intent is global logging control.
- If preserving current SDK behavior requires version counters, replay bookkeeping, or accessor-side branching, stop and present a simpler public contract alternative before implementing the more complex path.
- Before designing a wrapper API, explicitly confirm whether the API is main-thread-only or required to be fully thread-safe. Do not assume full thread safety unless the requirement is stated.
- If an async SDK call returns meaningful metadata, return it as a result struct instead of exposing mutable state flags.
- Prefer small top-level result or status types over nested public contract types when the result is reused or part of the stable wrapper surface.
- Avoid `partial` and nested public API shape unless language tooling or generation actually requires it.
- Keep editor helpers, test hooks, and platform-specific support classes out of the main production wrapper folder when they are not part of the runtime contract.
- Contain malformed data, nulls, parsing failures, and vendor exceptions inside the wrapper layer.
- Keep SDK-specific assumptions and vendor quirks out of core gameplay, UI, and business logic.

## Review Focus
- third-party type leakage
- stateless wrapper contract quality
- malformed-data containment
- boundary clarity
