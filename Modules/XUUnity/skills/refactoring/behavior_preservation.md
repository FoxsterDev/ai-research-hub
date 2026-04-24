# Skill: Behavior Preservation

## Use For
- no-behavior-change refactors
- legacy cleanup
- safety-first structural work

## Rules
- Product behavior and public contract stability are higher priority than local structural elegance.
- Preserve observable behavior before improving structure.
- Identify lifecycle order, side effects, callback timing, persistence expectations, and degraded-mode behavior before moving code.
- Keep public method shape, callback timing, threading guarantees, and failure semantics stable unless a contract change is explicitly part of the task.
- Prefer minimal-diff changes on critical paths unless a larger redesign is required for safety.
- Keep refactor scope narrow enough that regressions can be localized quickly.
- Delete or merge helpers only when the resulting flow keeps behavior easier to verify, not just shorter.
- When simplifying signatures, remove parameters only if the remaining call site still makes ownership and failure behavior clearer than before.
- Do not mix structural cleanup with feature changes unless the user explicitly wants both.
- Maintain a clear rollback path for critical-flow refactors.
