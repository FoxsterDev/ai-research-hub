# XUUnity MCP SDK Rollout Validation Design

Date: `2026-05-14`
Status: `design`

## Purpose

This document defines the public-safe design direction for validating Unity
third-party SDK updates through the lightweight XUUnity MCP surface.

The target use case is a high-risk SDK rollout where a package update can affect:

- native Android/iOS dependency resolution
- generated Gradle and CocoaPods artifacts
- compile and build correctness
- device startup, crash, ANR, and native exception behavior
- monetization, attribution, analytics, consent, or other runtime SDK callbacks

The MCP should reduce rollout risk by making pre-rollout validation repeatable,
evidence-backed, and suspicious-diff aware.

## Current Coverage

The current public MCP surface already supports:

- editor readiness, health, status, and stale request cleanup
- active build target get/switch
- project refresh and package resolve
- live-editor EDM4U resolver triggering through known menu item paths
- generated dependency artifact verification from JSON expectations
- Android/iOS player script compile checks
- batch compile, compile matrix, EditMode tests, and plain batch player build
- generic scenario hooks, Game View screenshots, and Play Mode controls

This is enough for compile and dependency presence checks, but not enough for a
full SDK rollout gate.

Current gaps:

- `unity.edm4u.resolve` triggers resolver menus but does not enforce active
  Android build target before Android resolve.
- Resolver success can be superficial if generated Android outputs remain stale.
- The live-editor lane can open too many GUI Unity instances during broad
  portfolio work unless the host wrapper adds process pooling.
- `unity.editor.quit` is a request, not a hard process-exit contract.
- `unity.sdk.dependency.verify` checks required values, but it does not guard
  against unrelated destructive generated-file changes.
- The public MCP core does not yet install apps on connected devices, launch
  them, capture device logs, or run SDK runtime smoke flows.

## Required Core Additions

### P0: Resolver Correctness

Add a typed SDK dependency resolution lane.

`sdk.package_restore`:

- prefer closed-editor batch execution
- open Unity with package resolve and exit only after package operations settle
- record package cache package ids, versions, and dependency XML sources

`sdk.android_resolve`:

- enforce active `BuildTarget.Android` before EDM4U Android resolve
- optionally run Version Handler update before Android resolve
- run EDM4U Android Force Resolve
- wait for generated output freshness:
  - `ProjectSettings/AndroidResolverDependencies.xml`
  - `Assets/Plugins/Android/mainTemplate.gradle`
  - `Assets/Plugins/Android/settingsTemplate.gradle`
- fail if outputs still contain a known previous native dependency version
- report which resolver menu or method executed

`batch-edm4u-resolve`:

- closed-editor `-batchmode -executeMethod` wrapper around the same resolver code
- should become the default for broad multi-project SDK updates after validation
- must own async resolver waiting; a successful `ExecuteMenuItem` return value is
  not enough because the resolver can schedule work after the menu call

Batchmode is likely feasible for EDM4U-backed projects because Unity can load
editor assemblies in batchmode, but the MCP must prove it with versioned smoke
coverage before making it the default.

### P0: Generated Diff Guard

Add `sdk.generated_diff_guard` after resolver and before compile.

The guard should:

- accept an explicit expected changed-file allowlist
- require exact native dependency version changes
- compare generated outputs against a baseline snapshot
- classify changes as:
  - expected SDK dependency update
  - resolver normalization noise
  - suspicious deletion
  - unrelated project mutation
- fail on removal of critical generated-template content unless explicitly
  approved

Default suspicious removals for Android templates:

- `namespace "com.unity3d.player"`
- `ndkPath "**NDKPATH**"`
- `ndkVersion "**NDKVERSION**"`
- required Maven repositories
- signing config blocks
- manifest placeholders
- custom packaging excludes
- custom Gradle plugin declarations

The key rule: dependency presence is not sufficient. A rollout gate must also
detect unrelated generated-file damage.

### P0: GUI Concurrency Control

Add host-side editor pool control.

Required behavior:

- global Unity GUI process cap, default `3`
- SDK resolver lane default GUI cap `1`
- project-level lock so the same Unity project cannot be opened twice
- preflight report of already-open Unity PIDs and project paths
- `request-editor-quit-and-wait` that waits for process exit
- timeout escalation:
  - request Unity quit through MCP
  - graceful process termination
  - hard kill only when the PID is confirmed to belong to the target project

Broad SDK validation should prefer batch lanes. Live GUI lanes should be reserved
for editor-bound inspection, Play Mode, Game View, or short request flows.

### P1: Native Artifact Validation

Add Android artifact validation after export or build.

Android checks:

- run Gradle dependency report for the exported project
- verify expected resolved artifacts and transitive native SDKs
- detect duplicate classes and dependency conflict failures
- inspect merged AndroidManifest, Gradle files, repositories, ProGuard/R8 rules,
  native libraries, and manifest placeholders
- preserve build logs and normalized dependency summaries

Add iOS artifact validation after export.

iOS checks:

- fresh iOS export
- `pod install`
- verify expected pods and versions in `Podfile.lock`
- run `xcodebuild` compile/archive gate where feasible
- inspect `Info.plist`, privacy manifests, SKAdNetwork IDs, linked frameworks,
  and native SDK version evidence

### P1: Connected Device Validation

Add a device layer for USB-connected local devices.

Android device operations:

- `device.android.list` using `adb devices`
- install APK or APK extracted from AAB
- launch package/activity
- capture filtered `logcat`
- detect crash, ANR, Java exception, native crash, missing class, and SDK init
  errors
- capture screenshots and foreground state

iOS device operations:

- detect attached devices through Xcode tooling
- install and launch debug builds where signing allows
- collect device logs
- detect crash and startup failure

Device validation does not replace backend or dashboard checks, but it can close
most local pre-rollout runtime gates before business metrics are reviewed.

### P1: SDK Smoke Hook Contract

Device automation needs a reusable project-side hook contract. Add a debug-only
SDK smoke probe that a project can implement without exposing sensitive values.

Recommended hook capabilities:

- SDK initialization status
- adapter/native SDK version evidence when available
- mismatch evidence from SDK APIs or logs
- interstitial load/show/fail callbacks
- rewarded load/show/reward/fail callbacks
- banner/adaptive banner load/show/fail callbacks
- revenue callback continuity
- consent, privacy, and ATT/TCF state before and after prompts

The MCP should drive this hook and collect structured JSON. Screen tapping should
be a fallback, not the primary validation strategy.

### P2: Vendor-Specific Evidence Plugins

Add optional vendor-specific validators on top of the generic SDK lane.

Examples:

- parse vendor initialization logs
- parse adapter mismatch lines
- parse missing privacy, attribution, or SKAdNetwork warnings
- verify required native SDKs and transitive dependencies
- optionally open vendor debug screens and capture screenshots/log markers
- verify project config field presence without exposing literal secret values

Dashboard and backend checks remain outside the public MCP core unless a safe
host-local connector exists. The MCP should still produce a manual dashboard
checklist with expected windows and metrics.

## Recommended SDK Update Order

1. Record clean git baseline and expected diff allowlist.
2. Update Unity packages and package lock.
3. Run closed-editor package restore.
4. Switch active target to Android.
5. Run EDM4U Android Force Resolve, preferably through batchmode.
6. Run dependency verifier and generated diff guard.
7. Run Android and iOS compile gates.
8. Run Android export/build and Gradle dependency inspection.
9. Run iOS export, `pod install`, and `xcodebuild` compile.
10. Install on a connected device.
11. Run SDK smoke hook and collect device logs.
12. Produce rollout report with unresolved gates and manual dashboard checklist.

## Proposed Commands

High-level command:

```bash
xuunity sdk validate update <Vendor> <Component> for <Project> --android-device connected
```

Portfolio command:

```bash
xuunity sdk validate update <Vendor> <Component> --projects portfolio --android-device optional
```

Lower-level MCP commands to add:

```bash
xuunity_light_unity_mcp.sh batch-edm4u-resolve --project-root "$PROJECT" --platform android --switch-target Android
xuunity_light_unity_mcp.sh sdk-generated-diff-guard --project-root "$PROJECT" --config-file sdk_diff_guard.json
xuunity_light_unity_mcp.sh android-artifact-verify --project-root "$PROJECT" --export-root Builds/Android
xuunity_light_unity_mcp.sh device-android-smoke --project-root "$PROJECT" --apk Builds/Android/app.apk --config-file sdk_device_smoke.json
```

## Implementation Priority

1. Android target switch, batch EDM4U resolve, and output freshness checks.
2. Generated diff guard.
3. GUI process cap and quit-and-wait.
4. Android artifact inspection.
5. Connected Android device install, launch, logcat, and smoke hook.
6. iOS export, CocoaPods, and `xcodebuild` inspection.
7. Connected iOS device validation.

