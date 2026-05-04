# XUUnity Review: Release Readiness

## Check
- Critical bug risk
- crash and ANR exposure
- store compliance blockers
- date-aware store policy checkpoints:
  - confirm current Apple App Store and Google Play requirement dates from official pages at review time
  - include concrete dates in findings when policies affect go/no-go
  - flag missing date verification as a release-readiness issue
- rollback readiness
- missing release validation
- staged rollout necessity for SDK, manifest, or lifecycle-sensitive changes
- merged build artifact verification when source declarations can drift at build time
- feature and core-flow breakage probability
- whether any issue is already a confirmed bug
- manual QA scope required before release confidence is credible
- for package or SDK repos with tracked sample or consumer workspaces, whether sample assembly wiring and compile health are still green enough to count as release-ready integration evidence

## Additional Context
- Load `knowledge/review_quality_scoring.md` for the final score section.
- Load `knowledge/severity_matrix.md` when release findings need explicit shared severity or release-blocker framing.

## Output
For any saved review artifact, include the base metadata from `reviews/review_artifact_metadata.md`.

- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate release-validation test cases when evidence is sufficient
- Quality score section using `knowledge/review_quality_scoring.md`

## Review Artifact Contract
- Follow `reviews/review_artifact_contract.md`.
- Use `utilities/report_export.md` for the destination map.
