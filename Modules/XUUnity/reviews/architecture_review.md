# XUUnity Review: Architecture

## Load First
- `knowledge/review_quality_scoring.md`
- `knowledge/change_complexity_budget.md`
- `knowledge/review_evidence_provenance.md` for change reviews

## Check
- Clear subsystem boundaries
- platform abstraction quality
- lifecycle ownership
- testability
- startup and runtime cost
- one owner per product invariant and journey-level flow
- whether application-shell, screen-root, navigation, or bootstrap owners absorbed feature business logic
- project-native lifecycle, binding, shared-operation, cache, and coordination capability discovery by semantics
- concurrency classification and writer/thread evidence for synchronization
- duplicated lifecycle, guards, thread normalization, wrappers, static globals, and cross-layer callback round trips
- complexity delta from `knowledge/change_complexity_budget.md`

## Output
For any saved review artifact, include the base metadata from `reviews/review_artifact_metadata.md`.

`Category | Issue | Severity | Remediation`

Also include a quality score section using `knowledge/review_quality_scoring.md`.

## Review Artifact Contract
- Follow `reviews/review_artifact_contract.md`.
- Use `utilities/report_export.md` for the destination map.
