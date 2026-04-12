# Skill: Input And Navigation

## Use For
- touch input
- back navigation
- modal flows
- runtime focus rules

## Rules
- Keep tap handling idempotent on slow or repeated input.
- Guard against double-submit, multi-tap, and stale callback races.
- Define Android back behavior explicitly for every modal or screen layer.
- Keep UI state transitions predictable when app focus changes or interruptions happen.
