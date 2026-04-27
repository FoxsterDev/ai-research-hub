# Skill: Mobile UX Quality

## Use For
- product-facing mobile screens
- adaptive UIs that must survive safe areas, font scaling, and localization
- touch-heavy screens, cards, and collections
- mobile UI review for UX and readability risk

## Rules
- Keep primary content usable on phones without horizontal scrolling or user zoom. If content density breaks this rule, reflow or split the surface instead of shrinking it into illegibility.
- Respect safe areas and display cutouts on the interactive and readable content layers. Do not place critical text or fine-touch controls into notch, camera, or system-gesture conflict zones.
- Keep interactive targets at or above platform-safe minimums after scaling:
  - iOS-style touch targets: at least `44x44 pt`
  - Android-style touch targets: at least `48x48 dp`
- If the visible affordance must stay smaller, enlarge the invisible hit area instead of shrinking the effective target.
- Every custom interactive control needs visible state feedback:
  - pressed
  - selected if stateful
  - disabled when unavailable
  - loading or busy when action completion is delayed
- Preserve platform navigation expectations. On Android, do not replace standard system back behavior with custom onscreen back-only flows.
- Validate readability in both light and dark themes. For text and foreground content, keep contrast at least:
  - `4.5:1` for small text
  - `3:1` for large text and graphics
- For text-heavy or commerce-heavy screens, test larger text and font scaling as a first-class layout mode, not as an afterthought. Prefer wrap, vertical reflow, and content reprioritization over overlap or ambiguous truncation.
- When a UI claims larger-text support, treat `200%` text scaling as the minimum serious validation point.
- Test longer localizations and RTL layouts. Use leading and trailing semantics instead of hardcoded left and right assumptions, and mirror directional affordances where meaning depends on reading order.
- On wider mobile windows, foldables, and tablets, do not merely stretch phone cards, buttons, or dialogs across the extra width. Constrain readable widths and switch to panes, columns, or supporting surfaces when that improves comprehension and ergonomics.
- Keep controls close to the content they modify so dense screens remain understandable even when space gets tighter from scaling or localization.

## Validation Focus
- safe area and cutout devices, including both landscape directions
- effective hit target size after scaling
- max supported font scale and larger-text mode
- light and dark themes plus contrast-sensitive screens
- longest localization and RTL pass
- back gesture, restore, rotate, and resume behavior
