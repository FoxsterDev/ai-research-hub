# AppLovin MAX Mediator Profile: Mintegral

## Names
- Canonical: `Mintegral`
- Aliases: `MTG`
- AppLovin directory: `Mintegral`
- Unity package suffix: `mintegral`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.mintegral.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.mintegral.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Mintegral/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Mintegral/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:mintegral-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationMintegralAdapter`

## Research Checks
- Verify transitive Android dependencies because Mintegral adapter packages may
  add AndroidX dependencies in addition to the native ad SDK.
- Compare iOS podspec dependencies and min iOS platform.
- Treat privacy, regional SDK behavior, manifest permissions, network security,
  and SKAdNetwork changes as high-risk.
- Device smoke must cover rewarded integrity and paid revenue callbacks.

