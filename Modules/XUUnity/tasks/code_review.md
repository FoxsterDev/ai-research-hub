# XUUnity Task: Code Review

## Goal
Review code for production risk in Unity and native integration paths.

If the primary review target is the quality of tests themselves rather than the runtime code they accompany, route to `reviews/test_quality_review.md` instead of staying on this generic review task.

Load `knowledge/review_quality_scoring.md` for any review that reaches a concrete verdict.
Load `knowledge/review_evidence_provenance.md` for any diff, branch, PR, or commit review.
Load `knowledge/change_complexity_budget.md` for any concrete change or architecture verdict.

## Focus
- Bugs and regressions first
- Threading and ownership risk
- Allocation and performance cost
- Missing tests or missing validation coverage
- Feature and core-flow breakage risk
- QA validation needs for changed user journeys
- Callback ownership, dispatch ownership, and cleanup ownership
- Single-flight request-state ownership, duplicate-in-flight handling, and separation of scheduling failure versus posted-thread execution failure
- Policy or launch-mode decisions living at the wrong layer
- Strategy-versus-platform boundary drift in SDK and native wrapper code
- Redundant thread-normalization layers and compile-flagged variant duplication that increase maintenance without changing the real public contract
- Distinction between main-thread confinement, temporal reentrancy, cross-thread shared state, and unknown thread origin
- Project-native capability discovery before custom lifecycle, binding, request-sharing, caching, or synchronization state
- Complexity delta and whether added mechanisms consolidate or multiply owners

## Concurrency Evidence Gate
When the reviewed surface contains synchronization primitives, atomics, thread hops, callback-driven shared state, or thread-safety claims, load `skills/async/concurrency_classification.md` and require its evidence record. Do not call a temporal ordering collision a thread race, and do not award safety credit for synchronization whose cross-thread writer or any-thread contract is unproven.

## Complexity Budget Gate
Apply `knowledge/change_complexity_budget.md` before scoring. A concrete change review must account for new state owners, coordination primitives, wrappers, root-owner growth, cross-layer call-hopping, duplicated lifecycle, and test-driven production seams. Use project-local exemplars by capability; do not assume one public primitive catalog fits every project.

## Review Checklist
### What To Delete Before Extracting
- one-line wrapper methods that only forward the same parameters
- helper layers that do not change ownership, policy, or failure handling
- parameters that are passed through unchanged and unused by the callee
- generic dispatch helpers that hide operation-specific behavior on critical flows
- duplicated guards whose behavior is already owned by one clearer guard
- test-only runtime branches that should be replaced by a seam or test double
- speculative thread-safety for future callers with no public any-thread contract
- branch-local lifecycle, single-flight, or shared-operation machinery already owned by a matching project capability

### What Must Survive Extraction
- the one method or seam that owns callback adaptation, thread dispatch, or cleanup
- the boundary where synchronous validation ends and async or posted work begins
- the owner of shared mutable state such as in-flight request tracking
- operation-specific seams that keep critical flows auditable without string-based indirection
- test seams that replace production branching without widening the public contract

### Final Deletion And Collapse Pass
- identify the smallest mechanism that preserves each confirmed invariant
- consolidate multiple guards for the same invariant into one owner
- remove redundant dispatch after one boundary establishes thread ownership
- reject wrappers or interfaces whose only value is implementation-shaped mockability
- re-run scoring after simplification; do not score the pre-cleanup defensive machinery as the final architecture

## Output
- Findings ordered by severity
- Open questions
- Quality score summary using `knowledge/review_quality_scoring.md`
- Feature and core-flow risk assessment with breakage probability
- QA manual validation recommendations
- Candidate test cases when the reviewer has enough evidence
- Residual risk

## Review Artifact Rule
- Follow `reviews/review_artifact_contract.md` for the default save-by-default behavior.
- Use `utilities/report_export.md` for the default review-type destination mapping instead of picking an ad hoc folder.
