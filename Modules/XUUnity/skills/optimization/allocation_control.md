# Skill: Allocation Control

## Use For
- GC reduction
- hot-path reviews
- pooling and cache decisions

## Rules
- Treat repeated allocations on hot paths as bugs unless proven irrelevant.
- Avoid per-frame LINQ, boxing, closures, string churn, and hidden list growth in runtime-critical flows.
- Pool or reuse buffers and transient objects where the lifetime is predictable.
- Balance pooling against memory pressure and stale-state risk.
