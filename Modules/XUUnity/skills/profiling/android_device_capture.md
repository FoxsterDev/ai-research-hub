# Skill: Android Device Capture

## Use For
- capturing attributable CPU timelines from a real Android device
- deciding whether a spike is a real user-visible freeze
- agent-driven profiling without a human operating the Profiler window

## Capture
- Prefer the Editor Profiler connected to the device over `-profiler-log-file`. On some low-end devices the `.raw` log stops growing after a few seconds with no error; if a log file is used, confirm its size keeps growing for the whole flow.
- Connect from editor code: `ProfilerDriver.GetAvailableProfilers()` → match `ProfilerDriver.GetConnectionIdentifier(id)` → `ProfilerDriver.connectedProfiler = id`. Wi‑Fi players appear in that list; ADB-forwarded targets may appear only in the Profiler window dropdown, so select them there once.
- Drive the session with `ClearAllFrames()`, `enabled = true/false`, `SaveProfile(path)` and keep the `.data` so the capture reopens in the Profiler window for review.
- Raise frame history before recording (the Preferences value; up to 2000 frames), or long flows drop their beginning.
- Stop on an app signal (a logcat marker plus a fixed tail), not on a guessed duration.
- Deep profiling needs a build with deep-profiling support. Read relative shares from it; its absolute milliseconds are inflated.

## Attribution
- Read call trees per frame through `HierarchyFrameDataView` for the slow frames, not only frame totals.
- Periodic hitches (every N frames) only show in consecutive-frame tables; averages hide them.
- Discount development-only paths before attributing: assertion-gated debug features, stack-trace capture, verbose logging. Check whether the spike exists in a release-like build.

## User-Visible Truth
- Real on-screen pacing: sample `adb shell dumpsys SurfaceFlinger --latency "<app SurfaceView layer>"` in a loop (layer name from `dumpsys SurfaceFlinger --list`), or the vendor `hwcomposer` fps lines in logcat.
- `adb shell screenrecord` plus frame extraction around the event shows what the user actually saw. A long frame under a splash or loading cover is not a visible freeze; a half-built screen after it is.
- Decide visibility first, then optimize: the visible freeze, not the largest profiler number, sets priority.

## Related
- `profiler_workflow.md` for hypothesis discipline and baselines.
- `regression_detection.md` for before/after comparison.
