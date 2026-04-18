# XUUnity Review Policy Pack: SDK Changes

## Goal
Strengthen the review and validation stack for SDK-sensitive work without forcing a broad always-on bundle into unrelated tasks.

## Trigger When
- the task is about SDK integration, SDK upgrade, SDK downgrade, SDK wrapper design, connector-track choice, or vendor-boundary review
- the task touches startup or critical flows through a third-party SDK
- the task compares SDK versions, bundled native SDK lines, or connector compatibility

## Primary Risk Signals
- third-party API contract change
- hidden native version drift
- startup and callback behavior
- consent, privacy, attribution, ads, IAP, auth, notifications, or resume sensitivity
- merged manifest or plist drift

## Mandatory Stack Additions
- `reviews/sdk_code_review.md` for integration or implementation review
- `reviews/sdk_breakage_review.md` when the task is upgrade-sensitive, breakage-prone, or explicitly about SDK stability
- `skills/sdk/`
- `skills/async/` when callbacks, listener APIs, async init, or timeout sensitivity exist
- `skills/native/` when JNI, Objective-C, Swift, or native plugin layers exist
- `skills/tests/` when breakage-oriented validation design is required
- `knowledge/sdk_stability_scoring.md` when comparing versions, upgrade candidates, wrapper lines, or connector tracks
- `platforms/android.md` and/or `platforms/ios.md` only when platform-specific SDK behavior is relevant

## Validation Focus
- exact wrapper and bundled native version inventory
- initialization order and double-init safety
- callback thread origin and main-thread handoff
- malformed data, timeout, retry, and callback-lifetime handling
- merged manifest, plist, entitlement, or privacy-manifest truth when build tooling can rewrite declarations

## Co-loading Rule
- Prefer this pack as the primary pack when SDK sensitivity is the main breakage surface.
- If startup or manifest/native sensitivity is also present, load only the additional layers that are not already implied by this pack instead of loading multiple full packs blindly.

## Rule
- Compose existing shared reviews and skills. Do not duplicate SDK technical rules here.
