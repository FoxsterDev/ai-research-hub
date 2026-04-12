# XUUnity Async Skills

## Purpose
`skills/async/` contains shared best practices for async work in Unity mobile projects.
Load it when the task touches `async`, `await`, `UniTask`, `Awaitable`, `.NET Task`, cancellation, callbacks, or thread affinity.

## Routing
Always start with:
- `base_async_rules.md`

Then add only the needed topic files:
- `unitask.md`
- `awaitable.md`
- `dotnet_task.md`
- `cancellation.md`
- `main_thread.md`
- `exception_handling.md`

## Mobile Safety
Async work must respect:
- zero crash
- zero ANR
- no microfreezes on critical flows
- minimal allocation and synchronization overhead
