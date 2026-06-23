# Skill: State Management

## Use For
- game state
- UI state
- async state transitions

## Rules
- Make state ownership and transitions explicit.
- Avoid hidden cross-system mutation on critical flows.
- Keep one clear owner for mutable runtime state on critical paths; prefer reducer-owned or state-machine-owned history over helper-owned mutable fields.
- Before adding new mutable state, name the product invariant and allowed concurrency. Choose the simplest state shape that preserves that invariant, then place it in the existing owner.
- Put mutable flow state in the narrowest durable state owner that other readers already use. A presenter, coordinator, or helper may toggle that state while orchestrating an operation, but should not become the source of truth just because it owns the current call site.
- Prefer a boolean for single-entry-in-flight guards. Use counters, queues, or nesting depth only when overlapping operations are an intentional product contract and the owner can define how they drain.
- If a helper needs mutable history to compute scores or derived state, make the helper stateless and pass the state explicitly, ideally by `ref` on hot paths.
- For bounded hot-path history, prefer preallocated ring buffers over repeated list trimming and other allocation-heavy maintenance patterns.
- Prefer predictable transitions over scattered flags and callbacks.
- Expose intent-oriented behavior such as `CanStartAction(...)` when callers need an availability decision, instead of leaking transient pending or confirmation flags.
- When several state bits answer one availability or gating decision, expose a derived predicate from the state owner instead of duplicating the boolean expression across presenters, views, or popup systems.
- Keep derived availability and re-interaction rules in the state owner. Keep timeouts, cancellation, and refresh orchestration in the coordinating layer unless the state object truly owns the external workflow.
- Once an owned state/model layer has validated and normalized a transport value, downstream code must use that normalized value for the same decision or behavior. Do not keep parallel raw and normalized representations of the same field alive in coordinators or views.
- Design for pause, resume, retry, and interrupted external flows.
