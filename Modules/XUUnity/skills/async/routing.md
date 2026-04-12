# Async Routing

## Base Rule
If async-related signals are present, load:
- `base_async_rules.md`

Then refine:
- `unitask.md` for `UniTask`, `Forget`, PlayerLoop integration, or gameplay async
- `awaitable.md` for Unity `Awaitable`
- `dotnet_task.md` for `.NET Task`, `TaskCompletionSource`, or background compute
- `cancellation.md` for `CancellationToken`, timeouts, shutdown, or ownership
- `main_thread.md` for Unity object access or thread switching
- `exception_handling.md` for callbacks, fire-and-forget, or failure propagation

## Mandatory Rule
If the task is routed to async, the implementation or review is incomplete without the async skill layer.
