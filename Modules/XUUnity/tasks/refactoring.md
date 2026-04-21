# XUUnity Task: Refactoring

## Goal
Improve structure without changing intended behavior or weakening Unity mobile production safety.

## Focus
- Preserve observable behavior first, especially on startup, resume, save/load, rewards, ads, IAP, and SDK-backed flows.
- Prefer minimal-diff structural cleanup on critical paths unless a larger redesign is required for safety.
- Reduce unsafe lifecycle handling, ownership ambiguity, coupling, duplicated orchestration, or allocation churn.
- Make state ownership, callback ownership, and dependency seams more explicit.
- Keep Unity-facing contracts stable while moving platform, SDK, async, or bridge details behind narrower boundaries.
- Prefer staged migration, thin adapters, and reversible steps over one-shot rewrites on high-risk flows.
- Do not introduce new waits, blocking work, hidden main-thread stalls, or unhandled exception paths during refactor work.
- Add regression protection where breakage is expensive, especially before deleting the old path.

## Output
- Refactor target
- Behavior-preservation risks
- Ownership and boundary changes
- Migration steps
- Validation plan
