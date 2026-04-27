# Skill: Input And Navigation

## Use For
- touch input
- back navigation
- modal flows
- runtime focus rules

## Rules
- Keep tap handling idempotent on slow or repeated input.
- Guard against double-submit, multi-tap, and stale callback races.
- Keep effective touch targets at least `44x44 pt` or `48x48 dp` after scaling and safe-area padding are applied.
- Minimize raycast surface area on touch-heavy flows; non-interactive graphics should not participate in hit-testing.
- For composite controls, prefer one intentional root hit target instead of many child graphics competing for raycasts.
- Every custom control needs an obvious press state; stateful controls also need clear selected and disabled feedback.
- Define Android back behavior explicitly for every modal or screen layer.
- Preserve standard Android back and back-gesture expectations instead of forcing custom onscreen back-only navigation.
- Keep UI state transitions predictable when app focus changes or interruptions happen.
