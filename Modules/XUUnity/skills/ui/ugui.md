# Skill: UGUI

## Use For
- Canvas-based UI
- TextMeshPro screens
- button, list, popup, and HUD flows

## Rules
- Keep Canvas hierarchy stable on hot flows.
- Prefer partial updates over full tree refresh.
- Avoid enabling or disabling large UI trees every frame.
- Pool repeated list items and transient popups when churn is measurable.
- Treat localization, safe area, and dynamic text growth as layout risks on mobile.
- For mobile dashboards or status-heavy sample screens, split hero status, summary, and detailed diagnostics into separate visual regions instead of packing all live state into one rich-text block.
- Apply safe area to the readable and interactive content layer, not to full-bleed background visuals.
- Reserve separate vertical zones for independently changing hero status and secondary summary blocks; do not rely on best-fit text to resolve collisions after the fact.
- Choose semantic success, warning, and error colors against the real card or panel background; avoid light or neon success colors on light cards.
- For `UnityEngine.UI.Text` sample UI that must survive Unity-version drift, prefer a lightweight built-in font remap path over trusting serialized built-in font references alone.
- When switching between screen modes, switch the visible content root as well as the driver behavior so inactive-mode UI cannot remain on-screen and collide with the active layout.
- For capability demos and sample scenes, prefer a small number of visually separated cards over one diagnostics wall of text; this preserves readability on narrow phones and makes layout failures easier to localize.
