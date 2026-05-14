# AppLovin MAX Mediator Profile: Mintegral

## Names
- Canonical: `Mintegral`
- Aliases: `MTG`
- AppLovin directory: `Mintegral`
- Unity package suffix: `mintegral`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.mintegral.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.mintegral.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Mintegral/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Mintegral/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:mintegral-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationMintegralAdapter`

### Native Producer
- Mintegral developer docs: `https://dev.mintegral.com/`
- Mintegral SDK changelog / release notes: use the official Mintegral
  changelog page for the exact Android/iOS SDK line when available.
- Android package metadata: verify Mintegral artifacts and transitive AndroidX
  dependencies from Maven POM evidence.
- iOS package metadata: verify Mintegral pods, min iOS platform, and framework
  linkage from CocoaPods spec evidence.
- Native producer changelog confidence is `weak` when the exact version cannot
  be mapped to an official Mintegral release note.

### Cross-Mediation / Canary
- Google AdMob Mintegral mediation Android:
  `https://developers.google.com/admob/android/mediation/mintegral`
- Google AdMob Mintegral mediation iOS:
  `https://developers.google.com/admob/ios/mediation/mintegral`
- Compare Unity LevelPlay Mintegral network notes when they reference the same
  native SDK version.

### Stability Signals
- Treat privacy, regional behavior, manifest permissions, network security
  config, SKAdNetwork IDs, rewarded integrity, and revenue callbacks as
  high-risk.
- If producer notes are weak, require exact package metadata plus at least one
  cross-mediation canary before recommending broad rollout.

## Research Checks
- Verify transitive Android dependencies because Mintegral adapter packages may
  add AndroidX dependencies in addition to the native ad SDK.
- Compare iOS podspec dependencies and min iOS platform.
- Treat privacy, regional SDK behavior, manifest permissions, network security,
  and SKAdNetwork changes as high-risk.
- Device smoke must cover rewarded integrity and paid revenue callbacks.
