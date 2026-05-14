# AppLovin MAX Mediator Profile: ironSource

## Names
- Canonical: `ironSource`
- Aliases: `IronSource`, `Unity LevelPlay`
- AppLovin directory: `IronSource`
- Unity package suffix: `ironsource`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.ironsource.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.ironsource.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/IronSource/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/IronSource/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:ironsource-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationIronSourceAdapter`

## Research Checks
- Validate native ironSource / LevelPlay SDK version from Maven POM and
  CocoaPods spec.
- Treat bidding, waterfall, consent, COPPA/age restriction, revenue callbacks,
  and initialization order as high-risk.
- Check if adapter updates imply a MAX core update or native SDK major-line
  transition.
- Device smoke must verify load/show/reward callbacks and revenue callback
  continuity.

