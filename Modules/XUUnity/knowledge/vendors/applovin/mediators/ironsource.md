# AppLovin MAX Mediator Profile: ironSource

## Names
- Canonical: `ironSource`
- Aliases: `IronSource`, `Unity LevelPlay`
- AppLovin directory: `IronSource`
- Unity package suffix: `ironsource`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.ironsource.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.ironsource.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/IronSource/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/IronSource/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:ironsource-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationIronSourceAdapter`

### Native Producer
- LevelPlay / ironSource Android SDK changelog:
  `https://developers.is.com/ironsource-mobile/general/android-sdk-change-log/`
- LevelPlay / ironSource iOS SDK changelog:
  `https://developers.is.com/ironsource-mobile/general/ios-sdk-change-log/`
- Unity LevelPlay SDK changelog:
  `https://developers.is.com/ironsource-mobile/unity/sdk-change-log/`
- Android package metadata: verify native ironSource / LevelPlay artifacts from
  Maven POM evidence.
- iOS package metadata: verify native ironSource / LevelPlay pods from
  CocoaPods spec evidence.

### Cross-Mediation / Canary
- Google AdMob ironSource mediation Android:
  `https://developers.google.com/admob/android/mediation/ironsource`
- Google AdMob ironSource mediation iOS:
  `https://developers.google.com/admob/ios/mediation/ironsource`
- LevelPlay Unity/Flutter/React Native plugin changelogs are useful canaries
  when they wrap the same native SDK version.

### Stability Signals
- Treat initialization order, bidding/waterfall changes, COPPA/age flags,
  consent propagation, and revenue callbacks as high-risk.
- Because Unity owns LevelPlay/ironSource, native LevelPlay notes can reveal
  issues AppLovin wrapper notes do not mention.

## Research Checks
- Validate native ironSource / LevelPlay SDK version from Maven POM and
  CocoaPods spec.
- Treat bidding, waterfall, consent, COPPA/age restriction, revenue callbacks,
  and initialization order as high-risk.
- Check if adapter updates imply a MAX core update or native SDK major-line
  transition.
- Device smoke must verify load/show/reward callbacks and revenue callback
  continuity.
