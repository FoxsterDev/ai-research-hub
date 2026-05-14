# XUUnity Vendor Profile: AppLovin MAX

## Use For
AppLovin MAX Unity plugin and mediation-adapter update research.

Load this profile with `tasks/sdk_update_research.md` when the vendor is AppLovin, AppLovin MAX, MAX, or any MAX-mediated network.

Canonical commands:
- `xuunity sdk discover AppLovin`
- `xuunity sdk discover AppLovin <Mediator>`
- `xuunity sdk discover AppLovin <Mediator> for all apps`
- `xuunity sdk discover AppLovin Pangle`
- `xuunity sdk discover AppLovin Google`
- `xuunity sdk discover AppLovin Liftoff`

## Context Routing
This file is the global AppLovin MAX profile. For mediator-specific research,
also load the matching profile from:

- `knowledge/vendors/applovin/README.md`
- `knowledge/vendors/applovin/mediators/bidmachine.md`
- `knowledge/vendors/applovin/mediators/pangle_bytedance.md`
- `knowledge/vendors/applovin/mediators/facebook_meta.md`
- `knowledge/vendors/applovin/mediators/google_admob.md`
- `knowledge/vendors/applovin/mediators/ironsource.md`
- `knowledge/vendors/applovin/mediators/mintegral.md`
- `knowledge/vendors/applovin/mediators/moloco.md`
- `knowledge/vendors/applovin/mediators/unity_ads.md`
- `knowledge/vendors/applovin/mediators/vungle_liftoff.md`

When a mediator is named, this profile defines the common MAX contract and the
mediator profile defines package names, AppLovin changelog directories, and
source-of-truth URLs.

## Research Modes
### MAX Core
Use when the command targets AppLovin without a mediator component.

Research:
- `com.applovin.mediation.ads`
- AppLovin MAX Unity plugin releases
- bundled Android and iOS MAX SDK versions
- Unity minimum version
- Android target SDK, Jetifier, Gradle, and dependency changes
- iOS CocoaPods, privacy, ATT, SKAdNetwork, and bitcode constraints
- main-thread API and startup initialization contract

### Mediation Stack
Use when the task asks for full AppLovin health or "upgrade all".

Research every installed package under:
- `com.applovin.mediation.adapters.*.android`
- `com.applovin.mediation.adapters.*.ios`

Do not recommend `Upgrade All` by default. Produce the smallest candidate set that reduces risk without destabilizing revenue.

### Single Mediator
Use when the command names a mediated network, for example `Pangle`, `Google`, `Unity Ads`, `ironSource`, `BidMachine`, `Mintegral`, `Moloco`, `Meta`, or `Liftoff`.

Research Android and iOS separately. The final recommendation may be Android-only, iOS-only, both platforms, MAX-core-only, or no update.

## Primary Source Ladder
Use this order and record conflicts.

1. Unity package source:
   - `https://unity.packages.applovin.com/<package-name>`
   - `dist-tags.latest`
   - package tarball `package.json`
   - package tarball `Editor/Dependencies.xml`
2. Native Android source:
   - Maven metadata: `https://repo1.maven.org/maven2/com/applovin/mediation/<artifact>/maven-metadata.xml`
   - Maven POM dependency graph for the selected adapter version
3. Native iOS source:
   - CocoaPods trunk latest spec: `https://trunk.cocoapods.org/api/v1/pods/<PodName>/specs/latest`
   - Pod dependencies and minimum iOS platform
4. Official AppLovin changelog source:
   - Android adapter changelog in `AppLovin-MAX-SDK-Android`
   - iOS adapter changelog in `AppLovin-MAX-SDK-iOS`
   - MAX Unity plugin GitHub releases
   - MAX Android and iOS SDK GitHub releases
5. Runtime validation source:
   - AppLovin Integration Manager current/latest view
   - AppLovin Mediation Debugger on device or representative build

If the source ladder conflicts, do not recommend the update until the conflict is explained or manually verified.

## Known Source Templates
MAX core:
- Unity package: `https://unity.packages.applovin.com/com.applovin.mediation.ads`
- Unity releases: `https://github.com/AppLovin/AppLovin-MAX-Unity-Plugin/releases`
- Android native releases: `https://github.com/AppLovin/AppLovin-MAX-SDK-Android/releases`
- iOS native releases: `https://github.com/AppLovin/AppLovin-MAX-SDK-iOS/releases`

Mediator-specific source templates live under `knowledge/vendors/applovin/mediators/`.

## Naming Map
- `BidMachine` maps to the BidMachine adapter packages.
- `Pangle`, `ByteDance`, and `CSJ` map to AppLovin package directory `ByteDance`.
- `Google`, `AdMob`, and `Google AdMob` map to AppLovin package directory `Google`.
- `Facebook`, `Meta`, and `FAN` map to Meta Audience Network.
- `ironSource`, `IronSource`, and `Unity LevelPlay` map to the IronSource adapter packages.
- `Mintegral` and `MTG` map to the Mintegral adapter packages.
- `Moloco` maps to the Moloco adapter packages.
- `Vungle` and `Liftoff Monetize` map to the Vungle adapter packages.
- `Unity`, `Unity Ads`, and `UnityAds` map to the Unity Ads adapter packages.

## AppLovin-Specific Gates
- MAX APIs must be called from the Unity main thread.
- MAX should initialize at startup so mediated networks can cache ads.
- Android builds require Jetifier.
- iOS builds require CocoaPods.
- Bitcode is no longer supported on iOS.
- SKAdNetwork IDs, privacy manifests, Info.plist, and consent behavior are adapter-sensitive.
- The Mediation Debugger must be used to detect adapter/SDK mismatches and missing SKAdNetwork IDs before release confidence.
- Do not accept an adapter update if the native network SDK major version changes and no validation plan covers ad load, show, reward, callback, privacy, and revenue telemetry.

## Breaking-Change And Migration Checkpoint
This checkpoint is mandatory for every MAX core or mediator recommendation.

For MAX core updates, compare the current and candidate versions across:
- MAX Unity plugin GitHub release notes
- MAX Android and iOS native SDK release notes
- Unity package `package.json` and `Editor/Dependencies.xml`
- project usage of MAX initialization, ad load, show, callbacks, reward, paid revenue callbacks, privacy, consent, and debugger APIs

For mediator updates, compare Android and iOS separately across:
- AppLovin adapter changelog interval from current native adapter to candidate native adapter
- Maven POM or CocoaPods spec dependency deltas
- underlying network SDK release notes when the adapter crosses a native SDK major or behavior-sensitive line
- SKAdNetwork, Info.plist, privacy manifest, Android manifest, permission, min OS, and Gradle/CocoaPods deltas

Hard reject or require an implementation plan when:
- a used MAX or adapter API is removed, renamed, deprecated, or changes callback signature
- ad load, show, close, reward, failure, or paid revenue callback semantics change
- initialization order, Unity main-thread requirements, or lifecycle rules change
- consent, ATT, TCF, COPPA, age restriction, privacy, SKAdNetwork, or revenue telemetry behavior changes without explicit QA coverage
- the native network SDK major line changes and no source confirms compatibility with the current MAX core and project platform constraints

Classify each delta as `not used`, `used-safe`, `used-needs-change`, `unknown`, or `blocking` in the saved report.

## Platform Split Rules
Android and iOS are separate candidates.

Valid recommendation outcomes:
- `update MAX core only`
- `update mediator Android only`
- `update mediator iOS only`
- `update mediator both platforms`
- `update MAX core + mediator`
- `hold current`
- `reject target`
- `needs portfolio split`

Use platform split when:
- Android and iOS latest versions differ
- one platform has weaker source evidence
- one platform changes privacy, SKAdNetwork, CocoaPods, Gradle, min OS, or native SDK major version more aggressively
- the requested target, such as `7.9.1.X+`, is satisfied differently on Android and iOS

## Mediator Version Evidence Pattern
For all MAX mediators, the Unity package version can be encoded differently from
the native adapter and underlying network SDK version.

Use the package tarball `Editor/Dependencies.xml`, Maven POM, and CocoaPods spec
to confirm:
- AppLovin Unity package version
- AppLovin native adapter version
- underlying network SDK version
- MAX core version requirements
- Gradle/CocoaPods/min OS/privacy deltas

## Portfolio Mode
When the user says `for all apps`, do not produce one global update until every project is inventoried.

Required portfolio checks:
- installed AppLovin MAX core package per project
- installed adapter set per project
- Android and iOS adapter versions per project
- Unity version per project
- Android target and min SDK per project
- iOS deployment target per project
- whether the mediator is actually installed on each platform
- whether a shared update would force a project-specific MAX core update

Portfolio output must group projects into:
- safe shared update
- platform-specific update
- needs MAX core first
- hold current
- not installed
- blocked by missing evidence

## Report Requirements
Add an AppLovin source-ladder table:

`Source | Android Evidence | iOS Evidence | Confidence | Conflict`

Add a mediator decision table:

`Platform | Current Package | Latest Package | Native Adapter | Native SDK | Required Core | Decision`

Add revenue-risk analysis:
- ad fill
- bidding and waterfall behavior
- ad load/show callbacks
- reward integrity
- paid ad revenue callbacks
- dashboard placement and ad unit compatibility
- ATT, consent, SKAdNetwork, and privacy declarations

Add a breaking-change table:

`Area | Android Delta | iOS Delta | Project Usage | Decision | Validation`
