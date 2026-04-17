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
- Do not let an ATT or privacy plugin take ownership of unrelated ad-stack attribution behavior or ad-network plist population.
- Validate platform-specific behavior for iOS privacy and Android data collection settings.
- Keep protected-resource purpose strings, entitlements, and privacy manifests as separate reporting and review surfaces. Do not treat one as evidence that another is correct.
- Require privacy-manifest validity checks for iOS submissions that include third-party SDK bundles:
  - verify manifests are present where required
  - verify manifest content and signatures are valid in the submission artifact set
  - treat invalid or missing manifest evidence as a release blocker
- If a third-party SDK uses required-reason APIs in its own code, require the SDK to declare them in its own `PrivacyInfo.xcprivacy` instead of assuming the host app can report them on the SDK's behalf.
- Do not infer camera, location, microphone, or similar purpose-string duties from unrelated passive networking APIs unless the inspected platform documentation explicitly ties the API to a protected resource prompt.
- Cross-check SDK startup behavior and data collection with actual store questionnaire answers.
- Treat privacy and disclosure mismatches as release blockers, not post-release cleanup.
- Do not collapse partial consent into an all-or-nothing result when downstream SDK behavior must reflect per-purpose user choices.
