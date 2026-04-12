# Store Compliance Guidance

## Use For
- platform-specific submission checks after shared compliance skills are loaded

## Load First
- `skills/sdk/privacy_compliance.md`
- `skills/sdk/store_compliance.md`

## Platform-Specific Checks
- Add a date-aware policy checkpoint before any submission-ready conclusion:
  - verify current Apple and Google policy pages at review time
  - record exact effective dates in the output (for example `April 28, 2026`, not "soon")
  - treat unknown or unverified policy dates as a release-readiness gap
- Validate App Store specific plist, entitlement, ATT, and background mode declarations.
- Validate Play Store specific manifest, permission, data-safety, and SDK disclosure alignment.
- Re-check implemented runtime behavior against the final store questionnaire answers before submission.

## Review Output
- platform-specific submission blockers
- remaining disclosure mismatches
- remediation before release
