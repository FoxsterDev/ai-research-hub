# Skill: Base Async Rules

## Use For
- all Unity async implementation and review work

## Rules
- Choose one async primitive deliberately. Do not mix `UniTask`, `Awaitable`, and `.NET Task` in the same flow without a clear boundary.
- Before adding custom duplicate-call suppression, freshness guards, request-sharing state, or lifecycle state, search the resolved project's core/framework layer for matching capabilities and inspect their actual semantics. Record what matched or the concrete semantic gap; do not assume a public-core primitive name exists in every project.
- Keep async ownership explicit. Treat cancellation ownership as part of the API contract.
- Do not add pass-through `async`/`await` wrappers that only await and return another async call unchanged. Keep the direct return unless the wrapper adds real behavior such as ownership, cancellation shaping, exception translation, result mapping, or context guarantees.
- If the caller owns lifetime, UI validity, or user-facing decisions, prefer keeping the final await and post-await state checks in the caller unless a lower layer truly owns the callback or event contract.
- Do not add callback parameters, wrapper result structs, or other async contract surface unless they reduce real ownership complexity or encode stable semantics the caller genuinely needs.
- Do not use fire-and-forget on critical flows unless failure handling is explicit and safe.
- Never assume background continuations may touch Unity objects.
- A callback or async continuation is not evidence of cross-thread shared state. Classify the path with `concurrency_classification.md`, make one-thread ownership explicit where it exists, and synchronize only when a concrete cross-thread reader or writer or an explicit any-thread contract requires it.
- Avoid sync-over-async, blocking waits, and hidden main-thread stalls.
- Prefer designs that are observable, cancellable, and failure-contained.

## Review Focus
- primitive choice
- cancellation ownership
- exception propagation
- main-thread safety
- hitch and allocation risk
