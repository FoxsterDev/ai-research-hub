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

## Review Focus
- unhandled exception risk
- silent failure risk
- fault-attribution clarity across async boundaries
- containment quality
- logging quality
