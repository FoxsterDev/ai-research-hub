# AppLovin MAX Mediator Profile: Google AdMob

## Names
- Canonical: `Google AdMob`
- Aliases: `Google`, `AdMob`, `Google Mobile Ads`
- AppLovin directory: `Google`
- Unity package suffix: `google`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.google.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.google.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Google/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Google/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:google-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationGoogleAdapter`

### Native Producer
- Google Mobile Ads Android release notes:
  `https://developers.google.com/admob/android/rel-notes`
- Google Mobile Ads iOS release notes:
  `https://developers.google.com/admob/ios/rel-notes`
- Google Mobile Ads Unity plugin releases:
  `https://github.com/googleads/googleads-mobile-unity/releases`
- Google Mobile Ads Flutter plugin releases:
  `https://github.com/googleads/googleads-mobile-flutter/releases`
- Android package metadata: verify `play-services-ads` and related Google Play
  services artifacts from Maven POM evidence.
- iOS package metadata: verify `Google-Mobile-Ads-SDK` and dependency changes
  from CocoaPods trunk podspec evidence.

### Cross-Mediation / Canary
- The Google-owned Unity and Flutter plugins are strong canaries because they
  wrap the same native Google Mobile Ads SDK families.
- Google AdMob and Google Ad Manager policy pages are mandatory when native SDK
  changes mention target SDK, privacy, consent, or serving restrictions.

### Stability Signals
- Treat Android target SDK, Gradle/AGP requirements, Play services dependency
  shifts, UMP/consent behavior, privacy manifests, SKAdNetwork IDs, and paid
  event changes as high-risk.
- Native Google release notes outrank AppLovin wrapper notes for runtime risk.

## Research Checks
- Verify Google Mobile Ads SDK version through Maven POM and CocoaPods spec.
- Treat Android target SDK, Play services dependency shifts, Gradle plugin
  requirements, privacy manifest, SKAdNetwork IDs, and AdMob policy changes as
  release blockers when unclear.
- Check whether Google adapter version brackets or pins native SDK versions.
- Device smoke must verify interstitial, rewarded, banner, paid revenue
  callbacks, and consent propagation.
