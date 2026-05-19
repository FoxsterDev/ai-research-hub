# Skill: Base Async Rules

## Use For
- all Unity async implementation and review work

## Rules
- Choose one async primitive deliberately. Do not mix `UniTask`, `Awaitable`, and `.NET Task` in the same flow without a clear boundary.
- Before adding custom duplicate-call suppression, freshness guards, or request-sharing state, search for existing project async coordination primitives and prefer them when their semantics match.
- Keep async ownership explicit. Treat cancellation ownership as part of the API contract.
- Do not add pass-through `async`/`await` wrappers that only await and return another async call unchanged. Keep the direct return unless the wrapper adds real behavior such as ownership, cancellation shaping, exception translation, result mapping, or context guarantees.
- If the caller owns lifetime, UI validity, or user-facing decisions, prefer keeping the final await and post-await state checks in the caller unless a lower layer truly owns the callback or event contract.
- Do not add callback parameters, wrapper result structs, or other async contract surface unless they reduce real ownership complexity or encode stable semantics the caller genuinely needs.
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
