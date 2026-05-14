# AppLovin MAX Mediator Profile: Unity Ads

## Names
- Canonical: `Unity Ads`
- Aliases: `UnityAds`, `Unity LevelPlay Ads`
- AppLovin directory: `UnityAds`
- Unity package suffix: `unityads`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.unityads.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.unityads.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/UnityAds/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/UnityAds/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:unityads-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationUnityAdsAdapter`

### Native Producer
- Unity Ads docs: `https://docs.unity.com/ads/`
- Unity Ads SDK changelog:
  `https://docs.unity.com/en-us/grow/ads/Changelog`
- Android package metadata: verify Unity Ads artifacts from Maven POM evidence.
- iOS package metadata: verify Unity Ads pods, min iOS version, privacy
  manifest, and framework linkage from CocoaPods spec evidence.

### Cross-Mediation / Canary
- Google AdMob Unity Ads mediation Android:
  `https://developers.google.com/admob/android/mediation/unity`
- Google AdMob Unity Ads mediation iOS:
  `https://developers.google.com/admob/ios/mediation/unity`
- Unity-owned Unity Ads Unity package notes are a strong canary when they wrap
  the same native SDK version.

### Stability Signals
- Treat duplicate Unity Ads integrations, Unity Services package conflicts,
  initialization behavior, rewarded callbacks, privacy manifest, and paid
  revenue callback continuity as high-risk.
- Check whether the project already includes Unity Ads through Unity Services
  before approving an AppLovin-mediated update.

## Research Checks
- Verify native Unity Ads SDK version from Maven POM and CocoaPods spec.
- Pay special attention to Unity package conflicts, native Unity Ads SDK
  compatibility, privacy changes, and initialization behavior.
- Check whether project already includes Unity Services or Unity Ads through a
  separate integration path.
- Device smoke must verify rewarded callbacks and revenue callback continuity.
