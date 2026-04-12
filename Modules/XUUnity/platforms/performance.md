# Performance Platform Guidance

## Use For
- platform-specific performance checks after shared optimization and profiling skills are loaded

## Load First
- `skills/optimization/frame_budgeting.md`
- `skills/optimization/allocation_control.md`
- `skills/optimization/loading_and_microfreeze_prevention.md`
- `skills/optimization/bridge_performance.md`
- `skills/profiling/profiler_workflow.md`

## Platform-Specific Checks
- Validate CPU, GPU, thermal, and memory behavior on representative iOS and Android devices.
- Re-check bridge-heavy paths when JNI or native callbacks are involved.
- Prefer Burst or Job System over native plugins for pure compute work unless project constraints say otherwise.
- Check whether platform-specific startup work inflates first interactive time.
- When Android graphics API choice is under review, separate graphics API cost from SDK init, shader setup, and content-loading cost before attributing startup regressions.

## Review Output
- platform-specific hotspots
- thermal and battery risk areas
- device-only regressions

## Extracted Rules

### Timer Lifecycle Determinism
Problem: reusable timer primitives can look correct at call sites while still breaking on edge transitions such as `Start -> Pause -> Start`, `Stop -> Resume`, or repeated `Pause/Resume`.

Solution: make lifecycle transitions idempotent and deterministic, then add dedicated tests for `Start`, `Pause`, `Resume`, `Stop`, `Restart`, and completion semantics before reusing the timer in gameplay or ads code.

Rule: any reusable timer primitive used by gameplay, ads, or cooldown systems must guarantee deterministic lifecycle transitions and must have explicit lifecycle test coverage before reuse.

Confidence: high

### Timer Integration Test Semantics
Problem: integration tests can create false confidence when they simulate elapsed time with lifecycle control APIs such as `Stop(false)` instead of real completion.

Solution: wait for real timer completion or use test-only observation access for timer state, but do not treat control methods as substitutes for elapsed-time behavior.

Rule: integration tests for timer-driven systems must not use lifecycle control methods like `Stop(false)` as a proxy for elapsed-time completion.

Confidence: high
