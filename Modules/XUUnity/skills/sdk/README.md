# XUUnity SDK Skills

## Purpose
Use `skills/sdk/` for mobile SDK integration and review on iOS and Android.

## Routing
Always start with:
- `discovery_and_inventory.md`

Then add only the needed topic files:
- `initialization.md` for SDK startup order, consent-gated start, readiness, timeout, retry, or delayed-delivery behavior
- `wrapper_design.md` for wrapper ownership, adapter boundaries, cross-layer placement, or SDK-specific behavior isolation
- `callback_safety.md` for callback thread origin, listener lifetime, callback ordering, marshaling, or double-delivery risk
- `privacy_compliance.md` for consent, attribution identity, privacy-sensitive data flow, or user-tracking behavior
- `store_compliance.md` for ATT, manifest, plist, entitlement, privacy-manifest, or store-policy-sensitive SDK work

## Composition
SDK work often composes with:
- `skills/async/` when callbacks, async init, cancellation, retries, delayed queues, or main-thread handoff matter
- `skills/mobile/startup.md` when SDK behavior affects startup, consent flow, first interactive path, or resume-sensitive init
- `skills/native/` when JNI, Objective-C, Swift, native plugin ownership, or generated platform artifacts are involved
- `skills/tests/` when integration regression protection or breakage-focused validation is required
- `platforms/android.md` and/or `platforms/ios.md` when platform-specific SDK behavior is part of the defect or review

## Rules
- Do not load the whole SDK family by default; compose the smallest correct SDK stack for the concrete risk.
- For SDK bugs, inventory the wrapper, startup owner, callback owner, and identity owner before patching behavior.
- Prefer wrapper and sequencing fixes over payload-only fixes when the defect touches readiness, consent, delivery timing, or customer identity.
