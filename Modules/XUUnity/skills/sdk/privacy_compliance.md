# Skill: Privacy Compliance

## Use For
- ATT
- consent
- privacy-sensitive SDK behavior
- store compliance

## Rules
- Keep consent state and privacy gating explicit.
- Do not initialize or enable restricted SDK behavior before required consent gates.
- Separate compliance decisions from vendor-specific implementation details.
- Validate platform-specific behavior for iOS privacy and Android data collection settings.
- Require privacy-manifest validity checks for iOS submissions that include third-party SDK bundles:
  - verify manifests are present where required
  - verify manifest content and signatures are valid in the submission artifact set
  - treat invalid or missing manifest evidence as a release blocker
- Cross-check SDK startup behavior and data collection with actual store questionnaire answers.
- Treat privacy and disclosure mismatches as release blockers, not post-release cleanup.
- Do not collapse partial consent into an all-or-nothing result when downstream SDK behavior must reflect per-purpose user choices.
