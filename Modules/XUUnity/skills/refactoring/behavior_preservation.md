# Skill: Behavior Preservation

## Use For
- no-behavior-change refactors
- legacy cleanup
- safety-first structural work

## Rules
- Preserve observable behavior before improving structure.
- Identify lifecycle order, side effects, callback timing, persistence expectations, and degraded-mode behavior before moving code.
- Prefer minimal-diff changes on critical paths unless a larger redesign is required for safety.
- Keep refactor scope narrow enough that regressions can be localized quickly.
- Do not mix structural cleanup with feature changes unless the user explicitly wants both.
- Maintain a clear rollback path for critical-flow refactors.
