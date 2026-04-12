# Skill: Dependency Boundaries

## Use For
- service boundaries
- SDK wrappers
- feature layering

## Rules
- Isolate external SDKs and platform APIs behind stable boundaries.
- Keep gameplay, UI, monetization, analytics, and persistence responsibilities separated.
- Prefer narrow interfaces over broad global access patterns.
- Make high-risk dependencies replaceable and testable.
