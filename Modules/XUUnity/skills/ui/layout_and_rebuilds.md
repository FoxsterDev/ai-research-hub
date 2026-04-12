# Skill: Layout And Rebuilds

## Use For
- auto-layout heavy screens
- scroll views
- dynamic content

## Rules
- Treat layout rebuilds as performance-sensitive work.
- Avoid nested layout groups on hot or frequently refreshed screens.
- Batch content changes before forcing layout-sensitive updates.
- Do not trigger avoidable `ContentSizeFitter` and layout recalculations in loops.
- Profile slow device behavior, not only desktop editor behavior.
- Audit `RaycastTarget` on non-interactive graphics when touch handling or UI traversal cost becomes measurable.
- Prefer clipping and masking choices that do not explode draw calls or stencil passes on scroll-heavy UI.
