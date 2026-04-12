# Skill: Bridge Performance

## Use For
- JNI hot paths
- P/Invoke-heavy paths
- native-to-managed throughput review

## Rules
- Batch native calls where possible.
- Avoid repeated immutable lookups and per-call marshaling on hot paths.
- Cache immutable bridge results that are reused across the session.
- Preserve explicit ownership when native memory crosses the managed boundary.
- Prefer zero-copy or bounded-copy exchange patterns only when ownership is clear.
- Do not cache transient error state; keep concurrency-safe coordination explicit.

## Review Focus
- bridge crossing hotspots
- marshaling overhead
- caching opportunities
- allocation and throughput risk
