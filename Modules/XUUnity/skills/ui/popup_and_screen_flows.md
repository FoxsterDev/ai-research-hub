# Skill: Popup And Screen Flows

## Use For
- modal dialogs
- reward popups
- offer screens
- transition-heavy UI

## Rules
- Protect critical flows from popup timing races and duplicate open or close calls.
- Keep screen transitions free of blocking asset loads on the main thread.
- Fail safely if remote content or SDK-backed UI data is late or unavailable.
- Validate resume, interruption, and ad return paths on real devices.
