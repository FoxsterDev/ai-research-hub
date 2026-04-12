# Skill: .NET Task

## Use For
- background compute
- interop-heavy async work
- libraries that expose `.NET Task`

## Rules
- Use `.NET Task` for true background or library-driven async, not as a default replacement for Unity-centric async.
- Keep Unity object access outside background task execution.
- Avoid `Task.Result`, `Wait`, or other blocking patterns on the main thread.
- Be explicit about thread switching when returning from background work.

## Review Focus
- background boundary safety
- blocking risk
- thread handoff correctness
