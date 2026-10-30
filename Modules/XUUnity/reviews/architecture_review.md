# XUUnity Review: Architecture

## Load First
- `knowledge/review_quality_scoring.md`
- `knowledge/change_complexity_budget.md`
- `knowledge/review_evidence_provenance.md` for change reviews

## Review The Premise First
- Start from the original requirements and independently approved decisions, not only the author's latest design summary. Check event meaning, execution order, ownership, and the scope of each approval through `knowledge/execution_contract.md`.
- For a new owner, transport seam, or storage mechanism, evaluate a direct sequence under the existing owner and name the concrete semantic mismatch if that alternative fails. The reviewer may reject the proposed decomposition rather than only check its internal consistency.
- Separate source fact-checking, document consistency, architecture judgment, and runtime validation in the verdict. A bounded factual worker or a consistency score is not independent architecture approval.
- For a material ownership/transport/storage redesign, use a reviewer independent of the design author when the available authorized workflow supports it. Give that reviewer the requirements, comparison base and complete candidate diff (including new files), without requiring agreement with the design. If no independent reviewer is available, label the result self-review and preserve that limitation.

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
