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

Do not recommend a mediator update from AppLovin package versions alone. The
actual native adapter and underlying network SDK must be extracted from
`Dependencies.xml`, Maven POM, and CocoaPods spec evidence.

## Required Mediator Report Columns
Use these columns for every mediator:

`Platform | Current Unity Package | Candidate Unity Package | AppLovin Native Adapter | Underlying Network SDK | MAX Core Requirement | Source Confidence | Decision`

## Hard Rules
- Android and iOS are separate candidates.
- A mediator update may be Android-only or iOS-only.
- Native SDK major-line changes require explicit changelog and runtime smoke
  coverage.
- Adapter updates must be checked against MAX core compatibility.
- Mediation Debugger evidence is required before release confidence.
- Revenue callbacks, ad load/show/reward callbacks, consent state, privacy
  manifests, SKAdNetwork IDs, and dashboard metrics are business-critical.

