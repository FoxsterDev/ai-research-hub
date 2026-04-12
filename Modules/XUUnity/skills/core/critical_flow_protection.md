# Skill: Critical Flow Protection

## Use For
- startup
- scene loading
- IAP
- ads
- save/load
- rewards
- remote config
- account, session, and progression-sensitive flows

## Rules
- Identify critical flows before implementation or review.
- Prefer minimal-diff changes on critical paths unless a larger redesign is required for safety.
- Add fallbacks, timeouts, and safe default behavior where external systems can fail.
- Avoid introducing extra awaits, allocations, layout rebuilds, asset loads, or logging spam on critical flows.
- Validate rollback or degraded behavior, not only the happy path.

## Review Focus
- regressions on critical flows
- fallback behavior
- degraded-mode correctness
- latency and hitch risk
