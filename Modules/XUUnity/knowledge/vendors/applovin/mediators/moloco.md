# AppLovin MAX Mediator Profile: Moloco

## Names
- Canonical: `Moloco`
- Aliases: `Moloco Ads`
- AppLovin directory: `Moloco`
- Unity package suffix: `moloco`

## Source Of Truth
### AppLovin Wrapper
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.moloco.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.moloco.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Moloco/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Moloco/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:moloco-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationMolocoAdapter`

### Native Producer
- Moloco Ads docs / help center: `https://help.moloco.com/`
- Native Android and iOS package metadata must be treated as primary evidence
  when Moloco does not publish a precise public changelog for the exact SDK
  version.
- Android package metadata: verify Moloco artifacts and dependency graph from
  Maven POM evidence.
- iOS package metadata: verify Moloco pods, min iOS version, and framework
  linkage from CocoaPods spec evidence.
- Native producer changelog confidence is `weak` unless an official Moloco
  release note maps to the exact native SDK.

### Cross-Mediation / Canary
- Use Google AdMob or Google Ad Manager Moloco mediation adapter pages only when
  Google publishes a current page for the platform and the native SDK version
  can be mapped.
- Compare Unity LevelPlay Moloco notes when they expose the same native SDK line
  or platform requirement.
- Treat public canary coverage as weaker for Moloco than for Google, Unity Ads,
  ironSource, or BidMachine unless the exact native SDK line is visible.

### Stability Signals
- Treat bidding behavior, privacy declarations, Android manifest changes, iOS
  framework linkage, and revenue callbacks as high-risk.
- If native producer evidence is weak, recommendation confidence must stay
  below `high` until device smoke and dashboard observation pass.

## Research Checks
- Extract actual native Moloco SDK versions from Maven POM and CocoaPods spec.
- Treat bidding behavior, privacy declarations, Android manifest changes, and
  iOS framework linkage changes as high-risk.
- Confirm adapter compatibility with the installed MAX core before recommending
  a mediator-only update.
- Device smoke must verify ad load/show callbacks and revenue callback
  continuity.
