# AppLovin MAX Mediator Profile: Liftoff Monetize / Vungle

## Names
- Canonical: `Liftoff Monetize`
- Aliases: `Vungle`, `Liftoff`
- AppLovin directory: `Vungle`
- Unity package suffix: `vungle`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.vungle.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.vungle.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Vungle/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Vungle/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:vungle-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationVungleAdapter`

### Native Producer
- Liftoff Monetize support docs: `https://support.vungle.com/`
- Android SDK download and changelog:
  `https://support.vungle.com/hc/en-us/articles/15722228922395`
- iOS SDK download and changelog:
  `https://support.vungle.com/hc/en-us/articles/15718672681883-Download-Vungle-SDK-for-iOS`
- SDK integration FAQ:
  `https://support.vungle.com/hc/en-us/articles/43640580780315-SDK-Integration-FAQ`
- Android package metadata: verify Vungle/Liftoff artifacts and dependency
  graph from Maven POM evidence.
- iOS package metadata: verify Vungle/Liftoff pods, min iOS platform, privacy
  manifest, and framework linkage from CocoaPods spec evidence.

### Cross-Mediation / Canary
- Google AdMob Liftoff Monetize mediation Android:
  `https://developers.google.com/admob/android/mediation/vungle`
- Google AdMob Liftoff Monetize mediation iOS:
  `https://developers.google.com/admob/ios/mediation/vungle`
- Compare Unity LevelPlay Liftoff/Vungle notes when they expose the same native
  SDK line or platform requirement.

### Stability Signals
- Treat privacy manifest, SKAdNetwork IDs, consent behavior, native framework
  linkage, Android manifest changes, rewarded integrity, and paid revenue
  callbacks as high-risk.
- Verify naming carefully: AppLovin package suffix remains `vungle` even when
  public docs and dashboards use Liftoff Monetize.

## Research Checks
- Extract native Liftoff/Vungle SDK version from Maven POM and CocoaPods spec.
- Treat privacy manifest, SKAdNetwork IDs, consent behavior, native framework
  linkage, and Android manifest changes as high-risk.
- Verify adapter naming carefully: Unity package suffix is still `vungle` even
  when display names use Liftoff Monetize.
- Device smoke must cover rewarded integrity, interstitial callbacks, and paid
  revenue callbacks.
