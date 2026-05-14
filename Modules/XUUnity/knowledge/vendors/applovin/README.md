# AppLovin MAX Knowledge Pack

## Use For
Mediator-specific AppLovin MAX update research.

Load `../applovin_max.md` first for the global MAX research contract, then load
the mediator profile that matches the requested network.

## Mediator Profiles
- `mediators/bidmachine.md`
- `mediators/pangle_bytedance.md`
- `mediators/facebook_meta.md`
- `mediators/google_admob.md`
- `mediators/ironsource.md`
- `mediators/mintegral.md`
- `mediators/moloco.md`
- `mediators/unity_ads.md`
- `mediators/vungle_liftoff.md`

## Shared Source Ladder
Every mediator profile follows the same evidence order:

1. AppLovin Unity package registry:
   - `https://unity.packages.applovin.com/com.applovin.mediation.adapters.<name>.android`
   - `https://unity.packages.applovin.com/com.applovin.mediation.adapters.<name>.ios`
2. Unity package tarball `Editor/Dependencies.xml`.
3. AppLovin adapter changelog:
   - Android: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/<Directory>/CHANGELOG.md`
   - iOS: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/<Directory>/CHANGELOG.md`
4. AppLovin adapter native dependency metadata:
   - Android Maven metadata and POM under `https://repo1.maven.org/maven2/com/applovin/mediation/`
   - iOS CocoaPods trunk spec under `https://trunk.cocoapods.org/api/v1/pods/`
5. Underlying network SDK release notes and policy docs when native SDK versions
   change or when privacy, store, Gradle, CocoaPods, or lifecycle behavior may
   have changed.
6. Cross-mediation and cross-platform canaries:
   - Google AdMob / Google Ad Manager mediation adapter changelogs
   - Unity LevelPlay network changelogs
   - official Flutter, React Native, Unity, or native SDK changelogs that wrap
     the same Android/iOS native SDK versions
7. Ecosystem stability signals:
   - Google Play SDK Index for Android SDK policy and version advisories
   - Apple privacy manifest / required-reason API requirements
   - Maven metadata, Maven POM dependency graph, and artifact age
   - CocoaPods trunk specs, pod dependency graph, min iOS platform, and pod age
   - public GitHub issues or vendor help-center known issues when the SDK or
     adapter is open enough to inspect

Do not recommend a mediator update from AppLovin package versions alone. The
actual native adapter and underlying network SDK must be extracted from
`Dependencies.xml`, Maven POM, and CocoaPods spec evidence.

## Native Producer Evidence Rule
AppLovin changelogs are adapter-wrapper evidence. They are not sufficient by
themselves for runtime safety because the production code path includes native
SDKs owned by the mediated network.

For every recommendation, capture:
- AppLovin adapter wrapper delta
- native network SDK delta from the producer or native package metadata
- cross-mediation canary delta when available
- platform policy delta
- runtime validation plan

If the native producer does not publish a reliable changelog, explicitly mark the
native changelog confidence as `weak`, require package-metadata evidence, and
raise the device smoke requirement.

## Stability Signal Ranking
Use this ranking when sources disagree:

1. Native producer release notes or changelog for the exact Android/iOS SDK.
2. Maven POM / CocoaPods spec for the exact SDK and transitive dependencies.
3. AppLovin adapter changelog for the exact wrapper version.
4. Cross-mediation canary that wraps the same native SDK version.
5. Official issue/known-problem page or public GitHub issue with maintainer
   confirmation.
6. Community reports. Use only as risk signals, never as the sole reason to
   approve or reject.

Useful ecosystem checks:
- Google Play SDK Index: `https://play.google.com/sdks`
- Apple third-party SDK privacy requirements:
  `https://developer.apple.com/support/third-party-SDK-requirements/`
- Apple privacy manifests:
  `https://developer.apple.com/documentation/bundleresources/privacy_manifest_files`

## Canary Pattern
For ad mediation there is no single universal "Perfect Flutter Match" equivalent.
Use a canary only when it wraps the same native SDK version or reveals the same
platform constraint.

Good canaries:
- LevelPlay Flutter / React Native changelog wrapping the same native SDK.
- Google AdMob Flutter mediation adapter changelog for the same network.
- Vendor-owned Unity/Flutter/React Native plugin changelog wrapping the same
  Android/iOS SDKs.
- Another major mediation stack's network changelog showing the same SDK version
  plus a bugfix or breaking-change note AppLovin did not mention.

Do not treat a canary as approval. Treat it as a signal that must be reconciled
with native producer notes and project constraints.

## Required Mediator Report Columns
Use these columns for every mediator:

`Platform | Current Unity Package | Candidate Unity Package | AppLovin Native Adapter | Underlying Network SDK | MAX Core Requirement | Source Confidence | Decision`

Add this source table when the mediator is business-critical:

`Source Layer | Android Evidence | iOS Evidence | Stability Signal | Confidence | Follow-up`

## Hard Rules
- Android and iOS are separate candidates.
- A mediator update may be Android-only or iOS-only.
- Native SDK major-line changes require explicit changelog and runtime smoke
  coverage.
- Adapter updates must be checked against MAX core compatibility.
- Mediation Debugger evidence is required before release confidence.
- Revenue callbacks, ad load/show/reward callbacks, consent state, privacy
  manifests, SKAdNetwork IDs, and dashboard metrics are business-critical.
