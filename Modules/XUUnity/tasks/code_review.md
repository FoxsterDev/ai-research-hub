# XUUnity Task: Code Review

## Goal
Review code for production risk in Unity and native integration paths.

If the primary review target is the quality of tests themselves rather than the runtime code they accompany, route to `reviews/test_quality_review.md` instead of staying on this generic review task.

Load `knowledge/review_quality_scoring.md` for any review that reaches a concrete verdict.

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

## Review Checklist
### What To Delete Before Extracting
- one-line wrapper methods that only forward the same parameters
- helper layers that do not change ownership, policy, or failure handling
- parameters that are passed through unchanged and unused by the callee
- generic dispatch helpers that hide operation-specific behavior on critical flows
- duplicated guards whose behavior is already owned by one clearer guard
- test-only runtime branches that should be replaced by a seam or test double

### What Must Survive Extraction
- the one method or seam that owns callback adaptation, thread dispatch, or cleanup
- the boundary where synchronous validation ends and async or posted work begins
- the owner of shared mutable state such as in-flight request tracking
- operation-specific seams that keep critical flows auditable without string-based indirection
- test seams that replace production branching without widening the public contract

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
