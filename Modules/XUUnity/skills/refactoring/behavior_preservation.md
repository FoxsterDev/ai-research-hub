# Skill: Behavior Preservation

## Use For
- no-behavior-change refactors
- legacy cleanup
- safety-first structural work

## Rules
- Product behavior and public contract stability are higher priority than local structural elegance.
- Preserve observable behavior before improving structure.
- Before refactoring a critical flow, explicitly freeze the non-negotiable invariants first.
  - include lifecycle order, identity or state semantics, persistence expectations, fallback boundaries, and failure severity when those affect backend or product contracts
  - do not start extracting helpers or simplifying structure until those invariants are clear
- Diagnostic or logging improvements must not move creation ownership or lifecycle boundaries of critical request, transport, or callback objects.
- Identify lifecycle order, side effects, callback timing, persistence expectations, and degraded-mode behavior before moving code.
- Keep public method shape, callback timing, threading guarantees, and failure semantics stable unless a contract change is explicitly part of the task.
- If a proposed fallback changes the semantic class of the contract rather than only degrading availability, treat that as a behavior change, not as a safe refactor.
- Prefer minimal-diff changes on critical paths unless a larger redesign is required for safety.
- Keep refactor scope narrow enough that regressions can be localized quickly.
- Delete or merge helpers only when the resulting flow keeps behavior easier to verify, not just shorter.
- When simplifying signatures, remove parameters only if the remaining call site still makes ownership and failure behavior clearer than before.
- Do not mix structural cleanup with feature changes unless the user explicitly wants both.
- Maintain a clear rollback path for critical-flow refactors.
