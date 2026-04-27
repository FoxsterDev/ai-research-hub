# Skill: Layout And Rebuilds

## Use For
- auto-layout heavy screens
- scroll views
- dynamic content

## Rules
- Profile UI spikes first and classify whether the cost is fill-rate, Canvas rebuild work, over-dirtying, or text generation before restructuring the hierarchy.
- Treat layout rebuilds as performance-sensitive work.
- Split non-trivial UI into static and dynamic Canvases by synchronized change cadence; keep elements that update together on the same Canvas when possible.
- Avoid nested layout groups on hot or frequently refreshed screens.
- Batch content changes before forcing layout-sensitive updates.
- Do not trigger avoidable `ContentSizeFitter` and layout recalculations in loops.
- Profile slow device behavior, not only desktop editor behavior.
- Avoid `Best Fit` on legacy UGUI `Text` for production or performance-sensitive UI; prefer fixed sizing or measured TMP auto-sizing there.
- For sample, debug, SDK-validation, or other low-scale utility UI, `Best Fit` is acceptable when it clearly saves authoring time and the screen is not a runtime performance hotspot.
- Re-enabling large text-heavy UI trees can cause rebuild and rebatch spikes; isolate frequently toggled regions behind narrower Canvases when show or hide churn is measurable.
- Audit `RaycastTarget` on non-interactive graphics when touch handling or UI traversal cost becomes measurable.
- Prefer clipping and masking choices that do not explode draw calls or stencil passes on scroll-heavy UI.
- For dynamic lists inside scene-authored editable UGUI screens, prefer a pre-authored hidden template plus pooling over runtime `AddComponent` hierarchy synthesis.
- Batch pooled-item population first, then perform the smallest necessary layout rebuild pass once the content tree is stable.
- For substantial scroll views, prefer pooling plus `RectMask2D`; keep hierarchy churn low because reparenting pooled items dirties graphics and can widen rebuild scope.
- When the total data count greatly exceeds the visible item count, use a virtualized window instead of instantiating one UI object per entry. A list that shows `10` cells at once usually needs only the visible cells plus a small buffer, not all `100+` item views.
