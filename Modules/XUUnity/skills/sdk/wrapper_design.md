# Skill: SDK Wrapper Design

## Use For
- third-party SDK wrapper APIs
- consent, analytics, attribution, ads, push, and monetization wrappers
- black-box SDK integration boundaries

## Rules
- Treat third-party SDKs as zero-trust boundaries.
- Keep the public wrapper facade thin: explicit contract checks, required ingress normalization, and delegation only. Do early synchronous validation only when it does not violate the documented public thread contract. Put orchestration below the facade.
- Do not leak third-party data structures into core application logic.
- Map SDK models to internal safe structs or DTOs immediately at the wrapper boundary.
- Keep public wrapper interfaces stateless where possible.
- Prefer explicit current-state reads such as `TryGet...(...)` plus future-change events over replay-on-subscribe or other subscription-side side effects.
- Do not expose convenience properties that collapse `unknown`, `not started`, and real negative state into the same public value.
- For cross-platform wrapper diagnostics, prefer one explicit verbosity threshold such as `MinLogLevel` over several loosely coupled platform-specific debug booleans when the intent is global logging control.
- If preserving current SDK behavior requires version counters, replay bookkeeping, or accessor-side branching, stop and present a simpler public contract alternative before implementing the more complex path.
- Before designing a wrapper API, explicitly confirm whether the API is main-thread-only or required to be fully thread-safe. Do not assume full thread safety unless the requirement is stated.
- If a wrapper promises any-thread public entry, normalize thread ingress at the public facade boundary before Unity-dependent work, Unity networking, or platform bridge code begins.
- If initialization is the single main-thread-only public entry point, state that explicitly and do not invent pre-init any-thread queue semantics unless product requirements clearly demand them.
- When a family of public wrapper APIs shares the same threading and error contract, prefer one consistent internal execution path instead of helper stacks that diverge by method.
- If an async SDK call returns meaningful metadata, return it as a result struct instead of exposing mutable state flags.
- Prefer small top-level result or status types over nested public contract types when the result is reused or part of the stable wrapper surface.
- Avoid `partial` and nested public API shape unless language tooling or generation actually requires it.
- Keep canonical mirrored state in one owner only. If platform or vendor mirroring fails, preserve the previous canonical value instead of partially applying the mutation.
- When launch behavior materially differs across modes such as native vs browser, prefer strategy split over a broad capability-probing interface with methods that some implementations should never use.
- Keep editor helpers, test hooks, and platform-specific support classes out of the main production wrapper folder when they are not part of the runtime contract.
- Do not add permanent runtime test seams to shipping wrapper code unless automated device validation is regular, trusted, and release-gating.
- Contain malformed data, nulls, parsing failures, and vendor exceptions inside the wrapper layer.
- Keep SDK-specific assumptions and vendor quirks out of core gameplay, UI, and business logic.

## Review Focus
- third-party type leakage
- stateless wrapper contract quality
- malformed-data containment
- boundary clarity
