# Skill: Scheduler Timers

## Rules
- `IFrameScheduler.CancelAfter` returns an `IDisposable` handle. Binding that handle to the same
  scope as the scope it cancels is a correctness requirement, not cleanup.
- Discarding the handle leaves a live timer holding a disposed scope. The **success path is the
  dangerous one**: an operation that completes before its deadline exits the scope and disposes it
  while the timer still runs, and the timer then cancels a disposed scope and throws
  `ObjectDisposedException`.
- Declare the handle after the scope (`using var scope = …; using var timeout = …;`) so
  reverse-order disposal stops the timer first.
- The throw surfaces from the scheduler's own loop with no application frame in the stack, so it
  cannot be traced back to the leaking call site from telemetry alone.
