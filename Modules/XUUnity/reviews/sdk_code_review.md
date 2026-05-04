# XUUnity Review: SDK Integration

## Load First
- `knowledge/review_quality_scoring.md`

## Check
- Initialization order
- Threading model
- callback ownership
- callback dispatch ownership
- cleanup ownership
- request-shaped native flow phase split: duplicate-in-flight rejection, scheduling failure, and posted-thread execution failure
- strategy-versus-platform responsibility split
- redundant ingress or egress thread normalization across facade, dispatch, and platform layers
- compile-flagged duplicate wrapper variants without dedicated coverage or a shared core
- launch or policy decisions implemented too low in the stack
- privacy and store declarations
- dependency version risk
- version and connector inventory accuracy
- startup cost and repeated bridge crossings
- public API misuse risk
- wrapper contract quality
- lifecycle and order-of-operations misuse
- test coverage for hangs, malformed data, retries, and callback-thread issues
- merged manifest or plist drift when build tooling can rewrite declarations
- feature and core-flow risk for startup, consent, ads, IAP, attribution, auth, notifications, or resume flows touched by the SDK
- deterministic bug versus probabilistic breakage assessment
- manual QA scenarios needed for risky integration paths

## Review Checklist
### What To Delete Before Extracting
- forwarding wrappers that do not preserve a real SDK or platform boundary
- pass-through parameters that widen signatures without affecting decisions
- generic bridge dispatch helpers that hide distinct native operations behind strings
- duplicated callback, disposal, or guard logic that should have one owner
- fake-path production branches that belong in test doubles or dedicated test support

### What Must Survive Extraction
- boundaries that make SDK versus platform responsibility obvious
- the single owner of callback completion, dispatch, and teardown
- explicit seams for operations with different native behavior or failure phases
- the state owner for single-flight, retry, or listener-lifetime coordination
- seams that keep device-risky paths testable without shipping fake execution branches

## Output
For any saved review artifact, include the base metadata from `reviews/review_artifact_metadata.md`.

- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate manual or automation test cases when evidence is sufficient
- Quality score section using `knowledge/review_quality_scoring.md`

## Review Artifact Contract
- Follow `reviews/review_artifact_contract.md`.
- Use `utilities/report_export.md` for the destination map.

## Escalate To
If the integration is high-risk or breakage-prone, also load:
- `reviews/sdk_breakage_review.md`

Also load `knowledge/sdk_stability_scoring.md` when the review compares SDK versions, wrapper releases, bundled native SDKs, or connector-track choices.
