# AppLovin MAX Mediator Profile: Moloco

## Names
- Canonical: `Moloco`
- Aliases: `Moloco Ads`
- AppLovin directory: `Moloco`
- Unity package suffix: `moloco`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.moloco.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.moloco.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Moloco/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Moloco/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:moloco-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationMolocoAdapter`

## Research Checks
- Extract actual native Moloco SDK versions from Maven POM and CocoaPods spec.
- Treat bidding behavior, privacy declarations, Android manifest changes, and
  iOS framework linkage changes as high-risk.
- Confirm adapter compatibility with the installed MAX core before recommending
  a mediator-only update.
- Device smoke must verify ad load/show callbacks and revenue callback
  continuity.

