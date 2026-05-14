# AppLovin MAX Mediator Profile: Meta / Facebook Audience Network

## Names
- Canonical: `Meta Audience Network`
- Aliases: `Facebook`, `FAN`, `Meta`
- AppLovin directory: `Facebook`
- Unity package suffix: `facebook`

## Source Of Truth
- Android Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.facebook.android`
- iOS Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.adapters.facebook.ios`
- Android changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-Android/master/Facebook/CHANGELOG.md`
- iOS changelog: `https://raw.githubusercontent.com/AppLovin/AppLovin-MAX-SDK-iOS/master/Facebook/CHANGELOG.md`
- Android AppLovin Maven artifact: `com.applovin.mediation:facebook-adapter`
- iOS AppLovin CocoaPod: `AppLovinMediationFacebookAdapter`

## Research Checks
- Verify Meta Audience Network native SDK compatibility from Maven POM and
  CocoaPods spec, not only AppLovin package versions.
- Treat iOS Swift/module import errors, privacy manifests, SKAdNetwork IDs, ATT,
  and Meta policy changes as high-risk.
- Check adapter and native SDK changelogs for bidding, initialization,
  threading, callback, and revenue-event changes.
- Device smoke must cover ad load/show callbacks and paid revenue callback
  continuity.

