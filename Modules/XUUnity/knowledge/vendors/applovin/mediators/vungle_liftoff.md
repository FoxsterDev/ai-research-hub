# AppLovin MAX Mediator Profile: Liftoff Monetize / Vungle

## Names
- Canonical: `Liftoff Monetize`
- Aliases: `Vungle`, `Liftoff`
- AppLovin directory: `Vungle`
- Unity package suffix: `vungle`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.vungle.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.vungle.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Vungle/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Vungle/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:vungle-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationVungleAdapter`

## Research Checks
- Extract native Liftoff/Vungle SDK version from Maven POM and CocoaPods spec.
- Treat privacy manifest, SKAdNetwork IDs, consent behavior, native framework
  linkage, and Android manifest changes as high-risk.
- Verify adapter naming carefully: Unity package suffix is still `vungle` even
  when display names use Liftoff Monetize.
- Device smoke must cover rewarded integrity, interstitial callbacks, and paid
  revenue callbacks.

