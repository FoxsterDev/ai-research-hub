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

## Additional Context
- Load `knowledge/severity_matrix.md` when release findings need explicit shared severity or release-blocker framing.

## Output
When the review is output or saved as a report, include review metadata at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`

- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate release-validation test cases when evidence is sufficient
