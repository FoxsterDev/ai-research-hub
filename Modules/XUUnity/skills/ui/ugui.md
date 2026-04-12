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
