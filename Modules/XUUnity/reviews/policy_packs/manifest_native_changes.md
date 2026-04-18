# XUUnity Review Policy Pack: Manifest And Native Changes

## Goal
Strengthen the stack for changes where merged declarations, native contracts, or platform bridges can create release blockers even when the managed diff looks narrow.

## Trigger When
- the task changes Android manifest, plist, entitlements, privacy manifests, or other submission-sensitive declarations
- the task changes JNI, Objective-C, Objective-C++, Swift, native plugin contracts, or Unity-to-native bridge ownership
- the task depends on post-merge build artifacts or native linker behavior for correctness

## Primary Risk Signals
- merged artifact drift
- native callback lifetime and ownership mistakes
- unresolved symbol or wrong-platform compilation exposure
- permission, privacy, or submission-sensitive declaration mismatch
- crash, ANR, or store rejection exposure caused by native or manifest-level changes

## Mandatory Stack Additions
- `skills/native/bridge_contracts.md`
- `skills/native/callback_lifetime.md`
- `skills/native/ownership.md` when ownership transfer or cleanup is relevant
- `skills/mobile/android_manifest_stability.md` for Android manifest-sensitive work
- `skills/sdk/privacy_compliance.md` and/or `skills/sdk/store_compliance.md` when store or privacy declarations are part of the change
- `reviews/native_plugin_review.md` when native bridge design or plugin contracts are being reviewed
- `platforms/android.md` and/or `platforms/ios.md`
- `platforms/store_compliance.md` when submission-sensitive declarations are in play

## Validation Focus
- merged manifest or plist truth instead of only source templates
- compile-time and link-time platform guards
- callback-thread and delegate lifetime safety
- entitlement, privacy-manifest, and required-reason API consistency where applicable
- post-merge verification when tooling can rewrite declarations

## Co-loading Rule
- Prefer this pack as the primary pack when manifest, plist, entitlement, privacy-manifest, or native bridge correctness is the main exposure.
- If SDK or startup sensitivity is also present, add only the missing overlays from those families.

## Rule
- Treat source declarations as insufficient evidence when merged or generated build artifacts can drift.
