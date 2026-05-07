# Skill: Behavior Preservation

## Use For
- no-behavior-change refactors
- legacy cleanup
- safety-first structural work

## Rules
- Behavior wins over structural elegance.
- In preservation and refactor work, do not change reviewed behavior unless the task explicitly requires it.
- Before refactoring a critical flow, write down the invariants first. Minimum set:
  - lifecycle order
  - callback timing
  - persistence expectations
  - fallback boundaries
  - failure severity
  - reviewed trigger ownership and delivery-channel boundaries for user-visible flows
- Do not start helper extraction or structural cleanup until those invariants are fixed.
- Keep public method shape, callback timing, threading guarantees, and failure semantics unchanged unless contract change is part of the task.
- A fallback that changes the semantic class of the contract is a behavior change, not a safe refactor.
- Logging or diagnostics work must not move creation ownership or lifecycle boundaries of request, transport, or callback objects.
- On critical paths, default to minimal-diff changes. Use a larger redesign only when safety requires it.
- Delete or merge helpers only when verification becomes easier after the change.
- Remove parameters only when ownership and failure behavior become clearer, not just shorter.
- Do not mix feature work and structural cleanup unless the task explicitly asks for both.
- Keep a rollback path for critical-flow refactors.
