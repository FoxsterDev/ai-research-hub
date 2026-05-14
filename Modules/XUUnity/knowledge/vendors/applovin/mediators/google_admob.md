# AppLovin MAX Mediator Profile: Google AdMob

## Names
- Canonical: `Google AdMob`
- Aliases: `Google`, `AdMob`, `Google Mobile Ads`
- AppLovin directory: `Google`
- Unity package suffix: `google`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.google.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.google.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Google/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Google/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:google-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationGoogleAdapter`

## Research Checks
- Verify Google Mobile Ads SDK version through Maven POM and CocoaPods spec.
- Treat Android target SDK, Play services dependency shifts, Gradle plugin
  requirements, privacy manifest, SKAdNetwork IDs, and AdMob policy changes as
  release blockers when unclear.
- Check whether Google adapter version brackets or pins native SDK versions.
- Device smoke must verify interstitial, rewarded, banner, paid revenue
  callbacks, and consent propagation.

