# Skill: Popup And Screen Flows

## Use For
- modal dialogs
- reward popups
- offer screens
- transition-heavy UI

## Rules
- Protect critical flows from popup timing races and duplicate open or close calls.
- For staged popup or modal flows, separate:
  - entry contract
  - deeper-step progression contract
  - data that is only required after the first visible screen
- If the first screen is non-authoritative and can be shown truthfully from already-known local state, prefer degraded or blocked progression over suppressing the entire popup because later-step data is unavailable.
- Keep screen transitions free of blocking asset loads on the main thread.
- Fail safely if remote content or SDK-backed UI data is late or unavailable.
- Validate resume, interruption, and ad return paths on real devices.
