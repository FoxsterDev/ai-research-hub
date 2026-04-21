# Skill: Base Async Rules

## Use For
- all Unity async implementation and review work

## Rules
- Choose one async primitive deliberately. Do not mix `UniTask`, `Awaitable`, and `.NET Task` in the same flow without a clear boundary.
- Keep async ownership explicit. Treat cancellation ownership as part of the API contract.
- Do not use fire-and-forget on critical flows unless failure handling is explicit and safe.
- Never assume background continuations may touch Unity objects.
- If state may be touched across callbacks, threads, or async continuations, make single-thread ownership or synchronization explicit.
- Avoid sync-over-async, blocking waits, and hidden main-thread stalls.
- Prefer designs that are observable, cancellable, and failure-contained.

## Review Focus
- primitive choice
- cancellation ownership
- exception propagation
- main-thread safety
- hitch and allocation risk
