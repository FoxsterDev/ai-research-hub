# Skill: Regression Detection

## Use For
- performance regression reviews
- release validation

## Rules
- Compare before and after data for frame time, memory, startup, and hitch count.
- For build-size regressions, compare named byte surfaces separately: final artifact bytes, `BuildReport.summary.totalSize`, packed asset bytes, and native/managed artifact deltas. Use `knowledge/unity_build_size_measurement.md` for the measurement doctrine.
- Treat regressions on critical mobile flows as release blockers when user-visible.
- Separate measurement noise from reproducible regressions.
- Tie findings to concrete code paths or assets whenever possible.
