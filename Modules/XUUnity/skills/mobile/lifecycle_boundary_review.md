# Skill: Lifecycle Boundary Review

## Use For
- reviewing Unity runtime services that wrap focus, pause, resume, and background behavior
- reviewing mobile save-on-background ownership
- reviewing lifecycle enums and lifecycle-facing consumer APIs

## Review Workflow
- Check whether raw Unity signals are separated from derived high-level app state.
- Check whether the derived lifecycle enum exposes product meaning instead of raw callback-order combinations.
- Check Android transient focus-loss cases so keyboard, overlays, and dialogs do not look like true backgrounding.
- Check iOS save behavior so persistence does not rely on `OnApplicationQuit`.
- Check whether save-now heuristics are centralized behind a lifecycle-owned boundary instead of repeated across consumers.
- Check `Application.lowMemory` handling for bounded repeated behavior, idempotency, and acceptable persistence cost.
- Check that `DontDestroyOnLoad` and engine-message integration tests live in PlayMode when engine behavior matters.
- Check whether testability was achieved without unnecessary test-only production APIs.

## Output Focus
- misleading lifecycle contracts
- platform-specific lifecycle risks
- save-boundary ownership problems
- missing lifecycle tests
- unnecessary production API pollution for tests
