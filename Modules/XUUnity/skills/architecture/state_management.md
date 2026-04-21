# Skill: State Management

## Use For
- game state
- UI state
- async state transitions

## Rules
- Make state ownership and transitions explicit.
- Avoid hidden cross-system mutation on critical flows.
- Keep one clear owner for mutable runtime state on critical paths; prefer reducer-owned or state-machine-owned history over helper-owned mutable fields.
- If a helper needs mutable history to compute scores or derived state, make the helper stateless and pass the state explicitly, ideally by `ref` on hot paths.
- For bounded hot-path history, prefer preallocated ring buffers over repeated list trimming and other allocation-heavy maintenance patterns.
- Prefer predictable transitions over scattered flags and callbacks.
- Expose intent-oriented behavior such as `CanStartAction(...)` when callers need an availability decision, instead of leaking transient pending or confirmation flags.
- Keep derived availability and re-interaction rules in the state owner. Keep timeouts, cancellation, and refresh orchestration in the coordinating layer unless the state object truly owns the external workflow.
- Design for pause, resume, retry, and interrupted external flows.
