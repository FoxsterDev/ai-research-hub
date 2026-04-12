# Skill: State Management

## Use For
- game state
- UI state
- async state transitions

## Rules
- Make state ownership and transitions explicit.
- Avoid hidden cross-system mutation on critical flows.
- Prefer predictable transitions over scattered flags and callbacks.
- Design for pause, resume, retry, and interrupted external flows.
