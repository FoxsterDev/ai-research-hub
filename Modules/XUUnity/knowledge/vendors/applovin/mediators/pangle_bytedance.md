# AppLovin MAX Mediator Profile: Pangle / ByteDance

## Names
- Canonical: `Pangle`
- Aliases: `ByteDance`, `CSJ`, `TikTok Audience Network`
- AppLovin directory: `ByteDance`
- Unity package suffix: `bytedance`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bytedance.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bytedance.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/ByteDance/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/ByteDance/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:bytedance-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationByteDanceAdapter`
- Android underlying SDK indicator: `com.pangle.global:pag-sdk`
- iOS underlying SDK indicator: `Ads-Global`

## Research Checks
- Unity package versions are encoded differently from native adapter versions.
  Always map them through `Editor/Dependencies.xml`.
- Compare Android POM transitive dependency changes for `pag-sdk`.
- Compare iOS podspec dependency changes for `Ads-Global`.
- Treat SKAdNetwork IDs, privacy manifests, ATT/consent behavior, and regional
  SDK variants as release blockers unless evidence is explicit.
- Do not merge Android and iOS recommendations when one platform satisfies the
  target version differently.

