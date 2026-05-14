# AppLovin MAX Mediator Profile: Pangle / ByteDance

## Names
- Canonical: `Pangle`
- Aliases: `ByteDance`, `CSJ`, `TikTok Audience Network`
- AppLovin directory: `ByteDance`
- Unity package suffix: `bytedance`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bytedance.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bytedance.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/ByteDance/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/ByteDance/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:bytedance-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationByteDanceAdapter`
- Android underlying SDK indicator: `com.pangle.global:pag-sdk`
- iOS underlying SDK indicator: `Ads-Global`

### Native Producer
- Pangle global docs: `https://www.pangleglobal.com/`
- Pangle SDK integration docs / help center: use the official Pangle Android
  and iOS SDK release notes or integration pages for the exact `pag-sdk` and
  `Ads-Global` versions when available.
- Android package metadata: verify `com.pangle.global:pag-sdk` from Maven POM
  evidence and inspect transitive dependencies.
- iOS package metadata: verify `Ads-Global` from CocoaPods spec evidence,
  including min iOS version, privacy manifest, and SKAdNetwork requirements.
- Native producer changelog confidence is `weak` unless an official Pangle note
  maps to the exact native SDK version.

### Cross-Mediation / Canary
- Google AdMob Pangle mediation Android:
  `https://developers.google.com/admob/android/mediation/pangle`
- Google AdMob Pangle mediation iOS:
  `https://developers.google.com/admob/ios/mediation/pangle`
- Compare Unity LevelPlay Pangle network notes when they reference the same
  Pangle native SDK line.
- Treat Flutter/React Native Pangle evidence as useful only when it confirms
  the same `pag-sdk` or `Ads-Global` native version.

### Stability Signals
- Treat regional SDK variant, ATT/consent, SKAdNetwork IDs, privacy manifest,
  Android manifest/provider changes, duplicate classes, and ad revenue callback
  continuity as release blockers when unclear.
- Because AppLovin package versions encode wrapper versions differently from
  native SDK versions, no Pangle recommendation is valid without
  `Dependencies.xml` extraction.

## Research Checks
- Unity package versions are encoded differently from native adapter versions.
  Always map them through `Editor/Dependencies.xml`.
- Compare Android POM transitive dependency changes for `pag-sdk`.
- Compare iOS podspec dependency changes for `Ads-Global`.
- Treat SKAdNetwork IDs, privacy manifests, ATT/consent behavior, and regional
  SDK variants as release blockers unless evidence is explicit.
- Do not merge Android and iOS recommendations when one platform satisfies the
  target version differently.
