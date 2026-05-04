# XUUnity Review: Native Plugin

## Load First
- `knowledge/review_quality_scoring.md`

## Check
- Ownership and memory lifetime
- JNI or ARC correctness
- thread affinity
- callback deregistration
- listener registration failure handling
- marshaling cost
- startup snapshot threading and main-thread cost
- API validity for the supported platform range
- permission-prompt presentation state and lifecycle readiness
- duplicate direct request entrypoints versus single-flight protection
- ownership boundaries between privacy bridge responsibilities and ad-stack attribution responsibilities
- deterministic cleanup for native string and buffer handoff into managed code
- core-flow breakage probability for the user journeys that depend on the bridge
- deterministic bug versus probabilistic bridge instability
- manual QA scenarios for lifecycle, backgrounding, resume, permissions, and callback timing

Review expectations for these checks:
- OS listener or callback registration failure must fail closed, clean up any worker resources created for the listener path, and must not leave a false-ready managed or native state.
- If the bridge already has an async native event path, the initial snapshot path should not hide avoidable synchronous native work on the Unity main thread during startup unless the product flow explicitly requires that blocking read.

## Output
For any saved review artifact, include the base metadata from `reviews/review_artifact_metadata.md`.

- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate device or integration test cases when evidence is sufficient
- Quality score section using `knowledge/review_quality_scoring.md`

## Review Artifact Contract
- Follow `reviews/review_artifact_contract.md`.
- Use `utilities/report_export.md` for the destination map.
