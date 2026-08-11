# Task

Production reports `ObjectDisposedException: the cancellation scope has been disposed.` — 19.9% of
daily users, 25 events per affected user. Every captured sample carries an identical stack:

```
CancellationScope.ThrowIfDisposed
CancellationScope.Cancel
FrameScheduler.Tick
SchedulerLoop.RunCore
```

A previous fix wave already shipped and the error is still reported, so those fixes did not close
the class. The residual must come from a site that wave did not touch.

Start from these candidates and patch them:

- `src/Retry.cs` — the shared retry helper; every caller inherits its timer, highest suspicion
- `src/Session.cs` — scope torn down from two paths
- `src/Prefetch.cs` — known to cancel during teardown

Bucket the samples by the first non-framework frame and fix the sites that produce the residual
volume.
