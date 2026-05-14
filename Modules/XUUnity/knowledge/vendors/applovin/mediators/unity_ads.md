# AppLovin MAX Mediator Profile: Unity Ads

## Names
- Canonical: `Unity Ads`
- Aliases: `UnityAds`, `Unity LevelPlay Ads`
- AppLovin directory: `UnityAds`
- Unity package suffix: `unityads`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.unityads.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.unityads.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/UnityAds/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/UnityAds/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:unityads-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationUnityAdsAdapter`

## Research Checks
- Verify native Unity Ads SDK version from Maven POM and CocoaPods spec.
- Pay special attention to Unity package conflicts, native Unity Ads SDK
  compatibility, privacy changes, and initialization behavior.
- Check whether project already includes Unity Services or Unity Ads through a
  separate integration path.
- Device smoke must verify rewarded callbacks and revenue callback continuity.

