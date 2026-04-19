# XUUnity Task: SDK Integration

## Goal
Integrate or update a third-party SDK without destabilizing startup, privacy posture, or platform bridges.

## Focus
- Initialization order
- Threading model
- dependency and version risk
- privacy and store declarations
- rollback and observability plan
- build-time ownership of manifests, plist keys, Gradle, pods, and postprocessors
- same-build log evidence for resolver and postprocess execution before attributing a manifest gap to SDK breakage
- distinction between stale generated outputs and reproducible current build failures
- whether a required declaration is source-owned, wrapper-owned, or vendor-postprocess-owned before recommending a fix

## Output
- Integration shape
- Risk areas
- Required platform declarations
- Validation plan
