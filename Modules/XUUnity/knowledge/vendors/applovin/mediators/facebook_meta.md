# AppLovin MAX Mediator Profile: Meta / Facebook Audience Network

## Names
- Canonical: `Meta Audience Network`
- Aliases: `Facebook`, `FAN`, `Meta`
- AppLovin directory: `Facebook`
- Unity package suffix: `facebook`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.facebook.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.facebook.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Facebook/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Facebook/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:facebook-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationFacebookAdapter`

### Native Producer
- Meta Audience Network docs: `https://developers.facebook.com/docs/audience-network/`
- Native Android package metadata: verify Audience Network SDK artifacts from
  Maven POM evidence, including transitive AndroidX and Google dependencies.
- Native iOS package metadata: verify Audience Network SDK podspec dependency,
  minimum iOS version, static/dynamic framework behavior, and privacy metadata.
- Native producer changelog confidence is often `weak` unless Meta publishes a
  release note for the exact Audience Network SDK version; do not substitute
  AppLovin wrapper notes for this gap.

### Cross-Mediation / Canary
- Google AdMob Meta mediation Android:
  `https://developers.google.com/admob/android/mediation/meta`
- Google AdMob Meta mediation iOS:
  `https://developers.google.com/admob/ios/mediation/meta`
- Compare Unity LevelPlay Meta/Facebook network notes when they reference the
  same native Audience Network SDK line.

### Stability Signals
- Treat ATT, Limited Data Use, bidding-only behavior, SKAdNetwork IDs, privacy
  manifest, and paid revenue callback changes as release blockers when unclear.
- If Meta producer notes are missing, require exact Maven/CocoaPods version
  extraction plus cross-mediation canary evidence and device smoke.

## Research Checks
- Verify Meta Audience Network native SDK compatibility from Maven POM and
  CocoaPods spec, not only AppLovin package versions.
- Treat iOS Swift/module import errors, privacy manifests, SKAdNetwork IDs, ATT,
  and Meta policy changes as high-risk.
- Check adapter and native SDK changelogs for bidding, initialization,
  threading, callback, and revenue-event changes.
- Device smoke must cover ad load/show callbacks and paid revenue callback
  continuity.
