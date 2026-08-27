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
- Verify that floor in screen pixels rather than reading it off the authored rect. A serialized `sizeDelta` is a physical target only when the canvas scale mode and its factor are known: `Canvas.scaleFactor` is the composed canvas-unit-to-pixel multiplier, while a `CanvasScaler`'s own `scaleFactor` is only its input and stays `1` under reference-resolution modes. Dividing by the wrong one rescales the target by the DPI factor, and a failed read that falls back to `1` hides the error instead of raising it.
- When a target must be resolution-independent, express it as anchor fractions instead of converting pixels; no scale factor enters the calculation, so none can be misread. Scene and prefab assets still own anchors by default (`ugui.md`) — drive them from code only when the component's own owner rewrites them at runtime, which authoring cannot hold.
- Minimize raycast surface area on touch-heavy flows; non-interactive graphics should not participate in hit-testing.
- For composite controls, prefer one intentional root hit target instead of many child graphics competing for raycasts.
- Every custom control needs an obvious press state; stateful controls also need clear selected and disabled feedback.
- Define Android back behavior explicitly for every modal or screen layer.
- Preserve standard Android back and back-gesture expectations instead of forcing custom onscreen back-only navigation.
- Keep UI state transitions predictable when app focus changes or interruptions happen.
