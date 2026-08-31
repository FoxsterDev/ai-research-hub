# XUUnity Vendor Profile: AppsFlyer

## Use For
AppsFlyer Unity plugin update research, candidate scoring, and pre-upgrade risk review.

Load this profile with `tasks/sdk_update_research.md` when the vendor is AppsFlyer.

## Primary Sources
- Unity plugin releases: `https://github.com/AppsFlyerSDK/appsflyer-unity-plugin/releases`
- Flutter plugin releases for native canary comparison: `https://github.com/AppsFlyerSDK/appsflyer-flutter-plugin/releases`
- Android SDK release notes: `https://dev.appsflyer.com/hc/docs/android-release-notes`
- iOS SDK release notes: `https://dev.appsflyer.com/hc/docs/ios-release-notes`
- Android Purchase Connector releases: `https://github.com/AppsFlyerSDK/appsflyer-android-purchase-connector`
- Google Play target SDK requirements: `https://developer.android.com/google/play/requirements/target-sdk`

## Candidate Identity
Use the exact GitHub `tag_name` as the candidate identity.

Do not recommend a version by approximate release line when AppsFlyer publishes more than one compatibility branch in the same release family.

## Mandatory Extraction
For every analyzed Unity plugin release, extract when present:
- Unity plugin tag
- publish date
- prerelease flag
- Android native SDK version
- iOS native SDK version
- Android Purchase Connector version
- branch or option label
- min Android SDK change
- iOS deployment target change
- release-note claims for crash, ANR, memory, startup, attribution, deep linking, privacy, DMA, or purchase behavior

If a value cannot be extracted automatically, keep the field as `unknown` and require manual verification before final approval.

## Branch And Purchase Connector Rules
AppsFlyer can ship separate compatibility options in nearby or same release lines. Treat these as separate candidates.

Known branch mapping:
- Purchase Connector `2.2.0` means Billing v8 track, often labeled Option A.
- Purchase Connector `2.1.2` means Billing v6 or v7 track, often labeled Option B.

Unity IAP compatibility gates:
- Unity IAP below `5.0.0` must not use the Billing v8 or Purchase Connector `2.2.0` track.
- Unity IAP `5.0.0` or newer should prefer the Billing v8 track unless project memory declares a different purchasing constraint.
- Unity IAP `4.12` through `4.13.x` should prefer the Purchase Connector `2.1.2` lineage unless project memory proves a safe migration to IAP 5.

Hard reject:
- Unity IAP below `5.0.0` plus Purchase Connector `2.2.0`.
- Any candidate whose connector track cannot be verified when purchases are business-critical.

## Native SDK Rules
Compare bundled native SDK versions, not only the Unity wrapper tag.

Flag as high risk:
- newer Unity wrapper with older Android or iOS native SDK than the current project or nearby candidate
- native SDK line that lacks required Android target SDK support
- iOS native line without a verifiable privacy manifest when the project targets App Store distribution
- release notes that mention purchase, attribution, deep linking, consent, or revenue behavior changes without a matching validation plan

Give positive weight to:
- native SDK updates that explicitly fix ANR, crash, memory, startup, deep-linking, attribution, purchase connector, or privacy defects
- exact parity with the AppsFlyer Flutter plugin native Android and iOS versions when Flutter is a useful public canary for the same native lines

Do not treat older as automatically more stable. A newer native SDK with explicit ANR, crash, memory, or compliance fixes can be the safer production candidate.

## Flutter Benchmark Stability Canary
This checkpoint preserves the original AppsFlyer discovery script behavior:

`STEP 1: Flutter Benchmark (Stability Canary)`

Before scoring Unity candidates, fetch the latest
`appsflyer-flutter-plugin` release and extract its bundled native Android and
iOS SDK versions. Treat exact Android plus iOS parity with Flutter as a positive
stability signal, not as automatic approval.

Hard rules:
- Record the Flutter release tag, publish date, Android SDK, iOS SDK, and source
  URL in the saved report.
- Mark every Unity candidate with `flutter_canary_match` when both native SDKs
  match the Flutter baseline exactly.
- If Flutter points to a newer native SDK line with ANR, crash, memory, privacy,
  or purchase fixes, explain why an older Unity wrapper is still safer before
  recommending it.
- If Flutter evidence conflicts with Unity release notes, native changelogs, or
  Purchase Connector compatibility, keep the candidate below high confidence
  until the conflict is manually verified.

## Breaking-Change And Migration Checkpoint
This checkpoint is mandatory for every AppsFlyer recommendation.

Compare the current Unity plugin and candidate across:
- AppsFlyer Unity plugin release notes
- Android SDK release notes for the bundled native Android line
- iOS SDK release notes for the bundled native iOS line
- Purchase Connector release notes and branch identity
- Flutter plugin releases when they help confirm native SDK behavior as a public canary
- project usage of AppsFlyer initialization, start timing, customer user id, deep linking, deferred deep linking, custom events, revenue events, purchase validation, consent, DMA, and privacy APIs

Hard reject or require an implementation plan when:
- a used AppsFlyer Unity, Android, iOS, or Purchase Connector API is removed, renamed, deprecated, or changes required parameters
- initialization timing, attribution readiness, customer user id, deep-link callback, purchase validation, consent, DMA, or revenue event behavior changes without explicit QA coverage
- the candidate switches Purchase Connector or Billing branch in a way that conflicts with the project's Unity IAP version
- Android manifest, iOS plist, privacy manifest, min OS, target SDK, Gradle, CocoaPods, or dependency behavior changes are not verified
- native Android and iOS SDK lines differ in a way that creates attribution, purchase, or privacy behavior asymmetry not covered by rollout validation

Classify each delta as `not used`, `used-safe`, `used-needs-change`, `unknown`, or `blocking` in the saved report.

## Compliance Gates
Android:
- Verify target SDK compatibility for the project's target API level.
- Verify dependency and billing compatibility with the current Gradle and Google Play Billing stack.
- Flag minSdkVersion increases as churn risk and require product approval if the project still serves affected users.

iOS:
- Verify `PrivacyInfo.xcprivacy` coverage for the native SDK line.
- Verify iOS deployment target changes.
- Flag ATT, DMA, consent, deep-linking, and attribution behavior changes for explicit QA validation.

## Issue Health Check
Search the Unity plugin issue tracker for the exact candidate tag or version plus:
- crash
- ANR
- memory
- purchase
- billing
- deeplink
- attribution
- consent

Do not hard reject solely because an issue exists. Hard reject only when there are multiple relevant, credible, unresolved reports or one deterministic release-blocking defect that matches the project's usage.

## AppsFlyer-Specific Validation
Before production rollout, require validation for:
- SDK initialization and attribution readiness
- custom event delivery
- revenue or purchase event delivery when used
- deep linking and deferred deep linking when used
- consent and privacy data transfer
- Android ANR and crash monitoring
- iOS crash and privacy-manifest checks
- dashboard-side verification for events that are business-critical

## Rollout Rule
Do not recommend an immediate full rollout for high-traffic production apps.

The report should recommend staged rollout with monitoring gates for:
- crash-free sessions
- ANR rate
- startup time
- purchase success or revenue event delivery
- attribution event continuity
- marketing campaign continuity

## OneLink Runtime Deep-Link Delivery (observed 2026-08-31, iOS SDK 6.17.x / Unity plugin 6.17.80)
Field-verified behavior for user-invite OneLink SHORT links (`generateUserInviteLink`); long links and
non-invite links were not covered by this evidence.

- iOS UDL (`didResolveDeepLink`) delivered `deep_link_value` and `media_source` but NOT
  `deep_link_sub1`/`af_sub1` — in both direct (universal link, app installed) and deferred (fresh
  install) flows, 100% of observed clicks — while the short link's stored payload demonstrably
  contained the sub params. Android delivered the full payload via the Play install referrer.
  Where the params are lost (vendor response filtering vs iOS SDK payload surface) is an unproven
  hypothesis; the observation itself is log-verified. Known-unfixed: AppsFlyerFramework#270.
- Query params APPENDED to an existing short link are ignored by the iOS in-app resolution path;
  only params STORED at link generation arrive. Do not design fixes around appending.
- Consequence: on iOS, payload that must survive end-to-end belongs in `deep_link_value` (dual-carry
  it in a sub param for Android/back-compat). Beware the analytics cost: per-user values in
  `deep_link_value` raise its cardinality in dashboards — group by `media_source` instead.
- UDL deferred deep linking has a 15-minute click-to-first-launch lookback. For owned invite flows,
  implement the eDDL fallback (`onConversionDataSuccess`, non-organic + first launch) which retains
  the deep-link payload for the full attribution window.
- Diagnostic: fetch the short link with an Android browser User-Agent; the Google Play redirect
  exposes the full stored parameter set in the `referrer` query param — the fastest proof of what a
  link actually carries, with no dashboard access.
- Dashboard interaction: OneLink template "Secure Shortlinks" treats any appended param as attribution
  manipulation and drops the click's attribution entirely; leave it off if links are ever extended.
