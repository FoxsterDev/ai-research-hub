# Thread safety (public family)

Rules for code that actually moves work across threads. The routing
selector for this family targets real API usage in inspected content —
`UniTask.SwitchToThreadPool(` / `ConfigureAwait(false)` call syntax —
because vocabulary in comments must never route an unrelated task here.
