# AppLovin MAX Mediator Profile: BidMachine

## Names
- Canonical: `BidMachine`
- Aliases: `bidmachine`
- AppLovin directory: `BidMachine`
- Unity package suffix: `bidmachine`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bidmachine.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bidmachine.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/BidMachine/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/BidMachine/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:bidmachine-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationBidMachineAdapter`

### Native Producer
- BidMachine SDK docs: `https://developers.bidmachine.io/sdk`
- Android SDK changelog: `https://developers.bidmachine.io/sdk/general/android/android-changelog`
- iOS SDK changelog: `https://developers.bidmachine.io/sdk/general/ios/ios-changelog`
- Android package metadata: verify native BidMachine SDK artifacts from the
  AppLovin adapter POM and any transitive POM dependencies.
- iOS package metadata: verify native BidMachine SDK pods from the AppLovin
  adapter podspec and its dependency graph.

### Cross-Mediation / Canary
- Google AdMob BidMachine mediation docs and adapter changelog when available:
  use the Android and iOS BidMachine mediation pages as an independent wrapper
  canary for the same native SDK line.
- Compare Unity LevelPlay or other major mediation adapter notes when they wrap
  the same BidMachine Android/iOS SDK version.

### Stability Signals
- Treat native bidding, auction timeout, consent propagation, and paid revenue
  callback changes as high-risk even when the AppLovin wrapper changelog is
  small.
- If BidMachine producer notes do not cover the exact native SDK version,
  confidence is `medium` at best until package metadata and device smoke agree.

## Research Checks
- Extract native adapter versions from both Unity package tarballs.
- Compare Android Maven POM transitive dependencies for the current and
  candidate adapter versions.
- Compare iOS podspec dependencies for the current and candidate adapter
  versions.
- Check underlying BidMachine SDK release notes when the adapter crosses a
  native SDK major or privacy-sensitive version line.
- Validate bidding behavior, paid revenue callbacks, consent propagation, and
  ad load/show callbacks before release confidence.
