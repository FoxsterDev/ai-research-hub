# Skill: Dependency Boundaries

## Use For
- service boundaries
- SDK wrappers
- feature layering

## Rules
- Isolate external SDKs and platform APIs behind stable boundaries.
- Keep gameplay, UI, monetization, analytics, and persistence responsibilities separated.
- Prefer narrow dependency boundaries that are testable and easy to reason about over broad global access patterns.
- Make high-risk dependencies replaceable without blurring ownership.
- Delete or collapse layers that only relay the same parameters and return the same result without changing ownership, policy, or failure handling.
- Prefer narrower callee signatures over broad pass-through parameter sets when a boundary only needs one small slice of upstream context.
- When a proposed simplification creates a second near-duplicate implementation, prefer extracting a shared core or deleting the old path instead of carrying two subtly diverging variants.
