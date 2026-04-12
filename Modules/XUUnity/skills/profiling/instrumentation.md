# Skill: Instrumentation

## Use For
- profiler markers
- custom timing
- targeted diagnostics

## Rules
- Instrument critical flows with names that match real user-visible operations.
- Prefer low-overhead instrumentation suitable for development and controlled diagnostics.
- Avoid noisy logs as a substitute for structured profiling.
- Remove or gate diagnostic code that risks runtime cost in release builds.
