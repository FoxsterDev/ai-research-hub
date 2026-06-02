# Skill: Allocation Control

## Use For
- GC reduction
- hot-path reviews
- pooling and cache decisions

## Rules
- Treat repeated allocations on hot paths as bugs unless proven irrelevant.
- Avoid per-frame LINQ, boxing, closures, string churn, and hidden list growth in runtime-critical flows.
- On mobile production runtime, extend that review beyond obvious per-frame code: repeated lookup, filtering, presenter update, SDK callback, and service query paths should not allocate through LINQ chains, iterator state machines, closure captures, or avoidable `ToArray`/temporary-list churn by default.
- Prefer simple loops over already-materialized arrays or lists, with exact-size outputs when an output collection is required.
- Do not overbuild the fix. Add dictionaries, secondary indexes, pools, or cache layers only when data size, call frequency, or measured evidence justifies the extra invalidation and state ownership.
- For editor-only tooling, importers, reports, and one-shot validation utilities, readable LINQ is acceptable when it is not shared with production runtime paths.
- Pool or reuse buffers and transient objects where the lifetime is predictable.
- Balance pooling against memory pressure and stale-state risk.
