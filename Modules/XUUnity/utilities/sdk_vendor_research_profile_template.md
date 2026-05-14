# XUUnity Utility: SDK Vendor Research Profile Template

## Goal
Create a production-grade `xuunity sdk discover <Vendor>` research profile for a new third-party Unity/mobile SDK.

Use this when adding support for vendors such as Unity services, Mixpanel, Firebase, Zendesk, OneSignal, or another SDK where a wrong update can break attribution, analytics, ads, purchases, push, auth, startup, privacy, or runtime stability.

Canonical command:
- `xuunity sdk profile design <Vendor>`

Alternative commands:
- `xuunity sdk research profile <Vendor>`
- `xuunity system design sdk research profile <Vendor>`

The output should be a concrete vendor profile proposal, and when approved or explicitly requested, an integrated file under:
- `AIRoot/Modules/XUUnity/knowledge/vendors/<vendor>.md`

## Load First
- `tasks/sdk_update_research.md`
- `knowledge/sdk_stability_scoring.md`
- `knowledge/risk_classification.md`
- `reviews/policy_packs/sdk_changes.md`
- `skills/sdk/discovery_and_inventory.md`
- `skills/sdk/privacy_compliance.md`
- `skills/sdk/store_compliance.md`
- `skills/tests/smoke_and_release_checks.md`
- `platforms/android.md` and `platforms/ios.md` when the SDK ships native mobile code
- existing vendor profiles for comparison:
  - `knowledge/vendors/appsflyer.md`
  - `knowledge/vendors/applovin_max.md`

## Development Prompt
Use this prompt shape for new vendor protocol work:

```text
xuunity sdk profile design <Vendor>

Goal:
Design and integrate a full SDK update-candidate research profile for <Vendor> so
`xuunity sdk discover <Vendor> [Component] [for <Project>]` can find the safest
stable update candidate, not simply the newest version.

Context:
- SDK business role: <attribution | analytics | ads | mediation | push | auth | support | IAP | engine service | other>
- Unity package or integration shape: <UPM | .unitypackage | native bridge | EDM4U | Gradle | CocoaPods | custom wrapper>
- Platforms: <Android | iOS | both>
- Optional components/adapters/modules: <list or unknown>
- Current project constraints to respect: <Unity version, Android target/min SDK, iOS target, IAP/Billing, consent, privacy, startup constraints>

Required work:
1. Identify source-of-truth ladder for the vendor:
   - Unity wrapper/package releases
   - native Android SDK source
   - native iOS SDK source
   - dependency metadata such as Maven POM, CocoaPods spec, UPM package, Gradle dependency, EDM4U XML, or package manifest
   - official changelog, migration guide, breaking-change notes, upgrade guide
   - official compliance docs for privacy, permissions, target SDK, ATT, SKAdNetwork, required-reason APIs, billing, or store policy
   - issue tracker only as supporting health signal
2. Define candidate identity:
   - exact tag/package/version used for recommendation
   - how wrapper versions map to native Android/iOS versions
   - how prerelease, beta, branch, LTS, or compatibility-track versions are identified
3. Define mandatory extraction:
   - wrapper version/date/prerelease
   - bundled native Android/iOS versions
   - connector/adapter/module versions
   - minimum Unity, Android, iOS, Gradle, CocoaPods, Xcode, or OS changes
   - manifest/plist/permission/privacy declaration changes
   - crash, ANR, memory, startup, callback, telemetry, attribution, analytics, purchase, ad, push, auth, or consent claims
4. Define breaking-change and API migration checkpoint:
   - official migration and breaking-change sources to inspect
   - changelog interval from current version to candidate
   - current project API usage grep targets
   - removed/renamed/deprecated APIs
   - callback signatures and threading changes
   - initialization, lifecycle, identity, consent, privacy, revenue, purchase, analytics, push, or auth behavior changes
   - classification: not used, used-safe, used-needs-change, unknown, blocking
5. Define hard gates:
   - incompatible Unity/native tooling/platform requirements
   - dependency-track mismatch
   - hidden native downgrade
   - unresolved high-confidence crash/ANR or data-integrity defect
   - missing migration proof for a used API or behavior change
   - compliance mismatch for app-store or Google Play submission
6. Define scoring and recommendation rules:
   - safest stable candidate beats newest candidate
   - no update is a valid recommendation
   - platform split is allowed when Android and iOS evidence differs
   - component split is allowed for graph-shaped SDKs
7. Define report additions:
   - source-of-truth ladder
   - candidate comparison
   - breaking-change/API migration table
   - native dependency table
   - business/runtime risk analysis
   - required validation before rollout
   - residual unknowns and manual verification anchors
8. Decide whether `scripts/sdk_update_research.py` should support this vendor:
   - add collector support only when source metadata is stable enough for repeatable evidence collection
   - keep script output as evidence, not final authority

Deliver:
- proposed `knowledge/vendors/<vendor>.md`
- optional script collector design for `scripts/sdk_update_research.py`
- command examples for full vendor, component, platform-specific, and portfolio research
- top risks that remain human/manual validation only
```

## Vendor Profile Skeleton
Use this structure for the new `knowledge/vendors/<vendor>.md` file:

```markdown
# XUUnity Vendor Profile: <Vendor>

## Use For
<Vendor> Unity/mobile SDK update research, candidate scoring, and pre-upgrade risk review.

## Research Modes
- Core SDK
- Optional modules/components/adapters
- Platform-specific Android/iOS mode
- Portfolio mode when `for all apps` is requested

## Primary Source Ladder
1. Unity wrapper/package source
2. Native Android source
3. Native iOS source
4. Official changelog, migration guide, breaking-change notes, upgrade guide
5. Compliance docs
6. Runtime validation source
7. Issue tracker as supporting signal only

If the source ladder conflicts, do not recommend the update until the conflict is explained or manually verified.

## Known Source Templates
- Unity wrapper:
- Android native:
- iOS native:
- Dependency metadata:
- Changelog:
- Migration guide:
- Compliance:

## Candidate Identity
Define the exact version/tag/package identity that must appear in reports.

## Mandatory Extraction
For every analyzed candidate, extract:
- wrapper version/date/prerelease
- native Android/iOS versions
- module/connector/adapter versions
- minimum platform/tooling changes
- compliance deltas
- crash/ANR/memory/startup fixes
- data-integrity or business-flow behavior changes

Unknown fields require manual verification before final approval.

## Breaking-Change And Migration Checkpoint
This checkpoint is mandatory for every recommendation.

Compare current and candidate versions across:
- official migration guide and breaking-change notes
- changelog interval from current version to candidate
- Unity wrapper API
- Android native API
- iOS native API
- dependency metadata
- project usage of public APIs, callbacks, wrappers, manifest entries, plist entries, and consent/privacy/revenue/analytics/push/auth flows

Hard reject or require an implementation plan when:
- a used API is removed, renamed, deprecated, or changes required parameters
- callback threading, lifecycle, initialization, identity, consent, privacy, telemetry, purchase, revenue, push, auth, or analytics semantics change without QA coverage
- platform or store-compliance requirements change without validation proof

Classify each delta as `not used`, `used-safe`, `used-needs-change`, `unknown`, or `blocking`.

## Hard Gates
- incompatible Unity, Gradle, CocoaPods, Xcode, OS, Android target/min SDK, or iOS deployment target
- missing privacy manifest, required declaration, permission proof, or store-policy compatibility
- dependency-track mismatch
- hidden native downgrade
- unresolved high-confidence crash/ANR/data-integrity defect for the exact candidate
- missing validation plan for a business-critical behavior change

## Scoring Rules
- prefer the safest compatible candidate, not the newest version by default
- score rejected candidates so the report explains why they lost
- allow platform split when Android and iOS differ
- allow no-update recommendation

## Validation Before Rollout
- compile/build validation
- representative device validation
- dashboard/backend verification when data delivery matters
- crash/ANR/startup monitoring
- staged rollout gates

## Report Requirements
Add vendor-specific tables and risk sections required beyond `tasks/sdk_update_research.md`.
```

## Completion Criteria
The vendor research profile is not complete unless it:
- names primary sources for wrapper, Android, iOS, dependency metadata, changelog, migration, compliance, and runtime validation
- defines exact candidate identity
- defines wrapper-to-native version mapping
- defines mandatory extraction fields
- defines the breaking-change and API migration checkpoint
- defines hard gates and no-update conditions
- defines Android/iOS split behavior
- defines business and runtime risk checks
- includes command examples
- states whether automation support is available, useful, or intentionally deferred
