# Skill: UGUI

## Use For
- Canvas-based UI
- TextMeshPro screens
- button, list, popup, and HUD flows

## Rules
- Keep Canvas hierarchy stable on hot flows.
- Prefer partial updates over full tree refresh.
- Avoid enabling or disabling large UI trees every frame.
- Keep initial UI visibility and active-state ownership explicit; do not rely on the last scene state saved in the Editor.
- Do not hide inactive UI by alpha alone when the product means "inactive"; hidden-but-active graphics still consume rendering work.
- Honor safe areas and cutouts on the readable and interactive content layers; do not let notch or gesture-zone conflicts become accepted layout debt.
- Pool repeated list items and transient popups when churn is measurable.
- Prefer TMP over legacy `UnityEngine.UI.Text` only when the minimum supported Unity version is `6000+`; even there, treat auto-size and fallback-font setup as measured performance and memory choices rather than free defaults.
- For SDKs, samples, or validation projects that support Unity `2021` or `2022+`, prefer `UnityEngine.UI.Text` unless project memory or the task explicitly says otherwise.
- For sample or debug-only utility UI, favor the cheapest authoring path that keeps the screen readable; do not force production-grade text fitting discipline onto non-critical internal surfaces.
- Treat localization, safe area, and dynamic text growth as layout risks on mobile.
- Validate long localizations and RTL before hard-freezing card widths, badge positions, or directional iconography in scene-authored UI.
- For mobile dashboards or status-heavy sample screens, split hero status, summary, and detailed diagnostics into separate visual regions instead of packing all live state into one rich-text block.
- Apply safe area to the readable and interactive content layer, not to full-bleed background visuals.
- Reserve separate vertical zones for independently changing hero status and secondary summary blocks; do not rely on best-fit text to resolve collisions after the fact.
- Choose semantic success, warning, and error colors against the real card or panel background; avoid light or neon success colors on light cards.
- For `UnityEngine.UI.Text` sample UI that must survive Unity-version drift, prefer a lightweight built-in font remap path over trusting serialized built-in font references alone.
- When switching between screen modes, switch the visible content root as well as the driver behavior so inactive-mode UI cannot remain on-screen and collide with the active layout.
- For capability demos and sample scenes, prefer a small number of visually separated cards over one diagnostics wall of text; this preserves readability on narrow phones and makes layout failures easier to localize.
- When a Unity user explicitly wants to hand-edit a validation or demo screen in the Editor, prefer a scene-authored UGUI hierarchy with a thin binder over runtime-generated layout trees.
- Keep scene ownership of cards, anchors, color, spacing, and hierarchy; use code to populate content and wire actions, not to synthesize the full visual structure by default.
