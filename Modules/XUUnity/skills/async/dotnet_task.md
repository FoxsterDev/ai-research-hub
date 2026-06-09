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
- Awaiting a `.NET Task` (e.g. `File.*Async`) with `ConfigureAwait(true)` resumes on the Unity main thread only if the await *started* on it — it re-captures the current `SynchronizationContext`, which is `UnitySynchronizationContext` only on the main thread. A UWR/UniTask (PlayerLoop) await self-corrects to main regardless of the starting thread. So before a Unity-native call reached after a `.NET Task` await, keep an explicit main-thread hop (or guarantee the caller is on main); after a UWR/UniTask await you do not need one. Enforce the "returns on main" promise at the wrapper's public boundary (see `main_thread.md`).

## Review Focus
- background boundary safety
- blocking risk
- thread handoff correctness
