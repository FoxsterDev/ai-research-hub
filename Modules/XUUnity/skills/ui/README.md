# XUUnity UI Skills — Family Sub-Router

Reached via the coarse UI hint in `tasks/start_session.md`. Load only the narrow file(s) below that match the actual task.

## Files
- `adaptive_grids.md` — `GridLayoutGroup`, inventory / store / gallery / card-collection layouts, mobile cell sizing.
- `input_and_navigation.md` — touch input, double-tap guards, raycast surface, custom controls, Android back button, focus rules, modal-input gating.
- `layout_and_rebuilds.md` — `Canvas` rebuild costs, nested `LayoutGroup`, `ContentSizeFitter` loops, scroll-view layout spikes, UI frame-spike investigation.
- `mobile_ux_quality.md` — safe areas, cutouts, font scaling, larger-text mode, light/dark contrast, RTL / localization-safe layout.
- `popup_and_screen_flows.md` — modal dialogs, reward popups, offer screens, staged popups, timing races, duplicate open/close, multi-gate user-data reuse across flow steps.
- `ugui.md` — Canvas hierarchy stability, partial UI updates, pooled list items, safe-area, hidden-but-active graphics.
- `ui_toolkit.md` — UI Toolkit (UIElements), USS/UXML, editor-facing panels, retained-mode runtime UI, UI Toolkit vs UGUI choice.
- `virtualized_scrollrect.md` — large `ScrollRect` lists or grids, virtualization, pooled cells, viewport-window math.
- `textmeshpro/rich_text_rendering.md` — HTML-shaped strings into TMP labels; converting `<a>`, `<br>`, `<p>` and entities into the closed TMP rich-text tag set; survey of FancyTextRendering / tmpro-custom-tags.
- `textmeshpro/glyph_coverage.md` — `TMP_FontAsset.HasCharacter` / `HasCharacters` across TMP versions; sanitizer recipe for missing-glyph `□`.
- `textmeshpro/emoji_rendering.md` — five rendering options (TMP Sprite Asset / color emoji font / UI Image badge / replace-at-parse / OS font fallback) with decision rubric.

## Narrow Routing
- `GridLayoutGroup`, adaptive cell sizing, store/gallery/inventory collections → `adaptive_grids.md`.
- touch input, double-tap / multi-tap guards, custom controls, raycast surface, Android back, focus, modal-input gating → `input_and_navigation.md`.
- Canvas rebuild, nested `LayoutGroup`, `ContentSizeFitter`, scroll-view spikes, dynamic content reflow, UI frame-spike investigation → `layout_and_rebuilds.md`.
- safe area, cutout, touch-target sizing, font scaling, larger-text, contrast, RTL, localization → `mobile_ux_quality.md`.
- modal dialogs, popup races, duplicate open/close, staged popups, non-authoritative first-screen progression, multi-step flow data reuse, double location/age/identity prompt → `popup_and_screen_flows.md`.
- Canvas-based UGUI hierarchy work, partial UI updates, pooled list items, hidden-but-active graphics → `ugui.md`.
- UI Toolkit / UIElements / USS / UXML / retained-mode runtime UI → `ui_toolkit.md`.
- `ScrollRect` virtualization, infinite scroll, pooled cells → `virtualized_scrollrect.md`.
- `<p>`, `<a>`, `<br>`, `&amp;`, `&nbsp;`, HTML markup in TMP labels, disclaimer or terms text, "user sees literal markup" bug → `textmeshpro/rich_text_rendering.md`.
- `TMP_FontAsset.HasCharacter`, `HasCharacters`, font fallback chain, missing-glyph `□`, supplementary-plane codepoints, cross-TMP-version API question → `textmeshpro/glyph_coverage.md`.
- rendering emoji / country flags / symbols the font does not cover, choosing between TMP Sprite Asset / color emoji font / UI Image badge / text-equivalent replacement → `textmeshpro/emoji_rendering.md`.

When in doubt within the TMP subset, all three TMP files are short and cross-link to each other; loading them together is acceptable.
