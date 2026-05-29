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

## Multi-Gate User-Data Reuse
When a flow has two or more sequential gates that each need the same user-provided data (location, age, identity, payment method), the second-and-later gate must NOT re-prompt for data the first gate already collected.
- Persist resolved data on the flow model the moment it lands; do not store only in the step that collected it.
- Each later step reads the model first. If the data is present, re-validate against the live source (OS permission, session, expiry) and proceed without prompting.
- A single boolean flag like `userGaveData = true` is insufficient — it cannot detect that the underlying source changed. Store the data itself.
- Do not pre-collect at the first gate "just in case" a later gate needs it. Prompt at the earliest step that genuinely needs it.

Failure signal during QA: open the flow once and count how many times each prompt UI appears. The second occurrence of the same prompt within one flow is a bug.
