# XUUnity SDK Stability Scoring

## Purpose
Reusable guidance for comparing third-party SDK versions in Unity mobile projects.

## Use For
- SDK upgrade decisions
- stability-first version comparison
- production-readiness review for SDK updates

## Rules
- Prefer the safest compatible version, not the newest version.
- Use weighted evidence instead of version recency alone.
- Treat dependency compatibility, native stability, and store compliance as first-class inputs.
- Treat hard compatibility mismatches as blockers, not tradeoffs.
- Compare bundled native SDK and connector versions, not only wrapper tags.
- Treat hidden branch splits and compatibility options as separate candidates when the same release line ships different dependency tracks.

## Suggested Scoring Inputs

### Stability Signals
- release maturity
- official non-beta status
- explicit stability fixes
- parity with the strongest relevant native benchmark available
- exact compatibility with the project's dependency track

### Bonus Signals
- native SDK upgrades that fix critical crashes, ANRs, or memory leaks
- compliance or security improvements

### Hard Rejection Signals
- dependency or billing mismatch
- unresolved crash or ANR evidence above the accepted bar
- target SDK or privacy compliance failure
- hidden downgrade in bundled native SDKs
- wrong branch or connector track for the current project environment

## Note
Scoring supports engineering judgment.
It does not replace compatibility checks, staged rollout, or critical-flow validation.
