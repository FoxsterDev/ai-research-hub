# Skill: Store Compliance

## Use For
- App Store and Play Store submission readiness
- privacy-sensitive API review
- manifest, plist, entitlement, and permission audits
- third-party SDK compliance

## Rules
- Runtime behavior must match store disclosures and consent flows.
- Protected APIs require correct declarations and purpose strings.
- Do not rely on restricted or undocumented APIs.
- Verify `Info.plist`, entitlements, `AndroidManifest.xml`, and runtime permission flows against the implemented feature set.
- On Apple platforms, review `Info.plist` purpose strings, entitlements or capabilities, and `PrivacyInfo.xcprivacy` as distinct compliance surfaces with separate failure modes.
- Do not treat passive observation APIs as automatic proof that protected-resource declarations or capability entitlements are required. Check the actual documented obligation of the API family in use.
- Review tracking, attribution, notifications, location, and background execution explicitly.
- Verify third-party SDK startup behavior and data collection against store questionnaire answers.
- On Android, require explicit exported and deep-link exposure rules for components that can be reached by external intents.
- Verify the final merged manifest or plist output, not only source templates, when SDKs or the build pipeline can rewrite declarations.

## Review Focus
- rejection risks
- missing declarations
- disclosure mismatches
- remediation before submission
