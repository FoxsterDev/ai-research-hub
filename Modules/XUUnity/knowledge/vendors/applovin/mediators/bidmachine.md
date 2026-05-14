# AppLovin MAX Mediator Profile: BidMachine

## Names
- Canonical: `BidMachine`
- Aliases: `bidmachine`
- AppLovin directory: `BidMachine`
- Unity package suffix: `bidmachine`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bidmachine.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.bidmachine.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/BidMachine/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/BidMachine/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:bidmachine-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationBidMachineAdapter`

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

