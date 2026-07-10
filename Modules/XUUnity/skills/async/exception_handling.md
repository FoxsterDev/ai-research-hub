# Skill: Async Exception Handling

## Use For
- fire-and-forget review
- callback safety
- background continuation failures
- crash containment

## Rules
- No async path may fail silently on a critical flow.
- Fire-and-forget requires explicit exception handling, logging, and failure containment.
- Exceptions from external callbacks must not crash the app or break the main user flow.
- Prefer structured propagation over scattered try-catch blocks.
- When both an awaited operation and its immediate consumer may fail, prefer separating the `await` from the next call if that keeps fault attribution, stack traces, and operational logs clearer.
- Logging should preserve diagnosis without spamming hot paths.
- Under IL2CPP, never put side effects (e.g. field writes) inside an exception filter (`catch when (...)`): IL2CPP implements managed exceptions as C++ exceptions, so filter/`catch` execution order differs from Mono and the write can land at the wrong time — Unity's documented rule is to move state changes into the `catch`. Filters are otherwise supported and a pure-read filter is low-risk, but a tracked iOS `when()`-filter bug plus the exec-order difference make plain `catch` + `if` the safer default on shipping iOS/Android. Ref: Unity manual, IL2CPP exception-filter limitations.

## Review Focus
- unhandled exception risk
- silent failure risk
- fault-attribution clarity across async boundaries
- containment quality
- logging quality
