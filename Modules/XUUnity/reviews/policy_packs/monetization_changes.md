# XUUnity Review Policy Pack: Monetization Changes

## Goal
Strengthen the review and validation stack for monetization-sensitive work where a small lifecycle, callback, consent, or state mistake can silently lose revenue, grant the wrong reward, block progression, or create release-risk regressions.

## Trigger When
- the task changes ads, rewarded ads, interstitials, banners, offer placement, ad cooldowns, ad gating, or ad-return behavior
- the task changes reward eligibility, reward grant, reward acknowledgement, prize claim, ad-watched completion, or duplicate-grant protection
- the task changes IAP-adjacent monetization hooks such as ad removal, purchase-gated offers, paid entitlement checks, offer surfacing, or store-to-ad fallback behavior
- the task changes ad revenue callbacks, impression-level revenue reporting, attribution identity, placement metadata, or analytics emitted from monetization flows
- the task changes consent, startup, SDK-readiness, remote-config, experiment, or rollout behavior that controls when monetization can load, show, grant, or report

## Primary Risk Signals
- rewarded completion and authoritative grant state are owned by different layers
- callback delivery can be duplicate, delayed, out of order, cross-scene, or resume-sensitive
- ad show, close, fail, no-fill, timeout, and app-background paths are not all handled explicitly
- reward, currency, entitlement, placement, or offer config comes from remote config, experiments, backend state, or cached local state
- revenue reporting depends on SDK readiness, consent state, attribution identity, user identity, currency, precision, country, ad unit, placement, or ordering across SDKs
- monetization flow changes are guarded by rollout, A/B test, store build, platform, or region-specific conditions

## Mandatory Stack Additions
- `skills/core/critical_flow_protection.md`
- `skills/core/mobile_runtime_safety.md`
- `skills/sdk/callback_safety.md` when SDK callbacks, listeners, ad lifecycle events, or revenue callbacks are part of the flow
- `skills/sdk/initialization.md` when ad loading, show readiness, consent, or revenue reporting depends on SDK startup
- `skills/sdk/privacy_compliance.md` when consent, privacy flags, ATT, GDPR, or store policy affects ad loading or reporting
- `skills/refactoring/reward_grant_idempotency.md` when reward delivery, prize claim, duplicate callback, or resume-sensitive grant handling changes
- `skills/async/` when callbacks, await paths, cancellation, timeout, queueing, or delayed delivery are involved
- `skills/tests/smoke_and_release_checks.md` when release confidence depends on device or store-build monetization smoke coverage
- `reviews/release_readiness_review.md` when rollout, staged exposure, revenue impact, entitlement integrity, or ship-readiness is part of the task
- `reviews/sdk_code_review.md` and/or `reviews/sdk_breakage_review.md` only when the dominant change is also an SDK wrapper, SDK upgrade, connector, or vendor-boundary change
- `platforms/android.md` and/or `platforms/ios.md` only when platform-specific ad, purchase, consent, or store behavior is relevant

## Main Review Questions
- What exact monetization flow changed, and is it ads, rewards, purchase-adjacent entitlement logic, revenue reporting, or rollout/config behavior?
- Which owner decides eligibility, which owner performs the grant or entitlement change, and which owner only updates UI acknowledgement?
- If remote config or admin data gates monetization eligibility, does that gate stay at the eligibility boundary instead of leaking thresholds into SDK or ad-selection layers?
- Is reward delivery idempotent across duplicate callbacks, app backgrounding, scene changes, retries, and delayed completion?
- Are no-fill, load failure, show failure, cancel, close-before-complete, timeout, and SDK-not-ready paths explicit and user-safe?
- Does the flow keep consent, SDK readiness, identity, attribution, and revenue-event ordering stable before loading, showing, granting, or reporting?
- Can remote config, experiments, cached values, platform defines, or rollout flags create different reward amounts, placements, or entitlement behavior than the reviewed source path?
- Does any new logging, layout, asset load, await, or retry path add frame spikes, ANR risk, or user-visible stalls during the monetization moment?

## Required Evidence
- the monetization entry points touched, including UI triggers, SDK wrappers, callbacks, adapters, presenters, services, config readers, and persistence or backend owners
- current ownership of reward eligibility, authoritative grant state, UI acknowledgement, revenue reporting, and rollback or fallback behavior
- callback contract evidence for completion, close, failure, no-fill, revenue, and resume paths, including thread-affinity and duplicate-delivery assumptions
- consent and SDK-readiness evidence for ad loading, ad showing, revenue reporting, attribution identity, and purchase-adjacent entitlement decisions
- config and rollout evidence for placement ids, reward amounts, ad cooldowns, gating, offer visibility, defaults, cache invalidation, and platform or region overrides
- validation evidence that covers success, failure, cancellation, duplicate callback, delayed callback, background/resume, no-fill, SDK-not-ready, and rollout-default paths proportional to risk

## Validation Focus
- rewarded flow: grant exactly once after verified completion, never on simple close or failed show
- interstitial flow: no dead-end UI, blocked progression, missing resume recovery, or accidental reward side effects
- no-fill and failure flow: safe fallback, no crash, no stuck loading state, no repeated rapid retry loop
- revenue callback flow: correct event ordering, identity availability, currency and placement metadata, and no double-reporting across SDKs
- consent and startup flow: monetization does not load, show, or report before the current product and platform contract allows it
- rollout flow: default config, stale config, experiment variants, and disabled monetization paths remain safe
- device or integrated runtime validation when editor-only mocks cannot prove SDK callback, consent, store, or resume behavior

## Common Failure Modes
- reward granted from popup close, ad show attempt, or optimistic UI state instead of verified completion
- duplicate grants after duplicate callbacks, scene re-entry, resume handling, retry, or queued delivery
- missed grants when the app backgrounds, the callback arrives after the view is destroyed, or the SDK completes after a timeout
- no-fill or show failure leaves a screen blocked, a spinner alive, input disabled, or progression gated forever
- revenue is logged before consent, SDK readiness, user identity, attribution identity, or required placement metadata is available
- revenue is double-reported after SDK migration, wrapper refactor, event replay, or multiple analytics adapters listening to the same callback
- remote-config or rollout defaults change reward value, ad frequency, offer visibility, or entitlement behavior without matching validation
- a monetization callback touches Unity objects from the wrong thread or after object destruction

## Release-Risk Framing
- Treat duplicate reward, missed paid entitlement, purchase-adjacent entitlement breakage, irreversible currency corruption, consent violation, or store-policy monetization blocker as release-blocking until disproven.
- Treat lost ad revenue reporting, broken placement attribution, no-fill dead ends, or high-traffic ad show failures as high risk even when the app does not crash.
- Treat validation limited to editor mocks as incomplete for SDK callback ordering, ad-return lifecycle, consent, store, or device-specific behavior.
- Treat rollout-guarded monetization changes as production-sensitive because disabled or low-percentage variants can still corrupt revenue, rewards, analytics, or entitlements for exposed users.

## Co-loading Rule
- Prefer this pack as the primary pack when ads, rewards, purchase-adjacent monetization hooks, revenue callbacks, or monetization rollout behavior are the main breakage surface.
- If SDK wrapper, startup sequencing, manifest/native, or privacy declaration sensitivity is also present, load only the additional layers not already implied by this pack instead of stacking multiple full packs blindly.
- Do not use this pack for generic UI, generic analytics, or generic SDK changes unless the changed behavior can affect monetization correctness, rewards, entitlements, revenue reporting, or monetization rollout safety.

## Final Review Must Report
- the monetization surfaces touched and the dominant risk family
- the active policy pack and trigger reasons
- the authoritative owner for eligibility, grant or entitlement mutation, UI acknowledgement, and revenue reporting
- evidence for consent, SDK readiness, identity, callback ordering, config, and rollout assumptions
- validation performed and validation still missing, especially device, store-build, callback, no-fill, duplicate, resume, and rollout-default coverage
- release-risk classification for reward integrity, entitlement integrity, revenue reporting, user-visible blocking, consent or store compliance, and rollout safety

## Rule
- Compose existing shared reviews and skills. Do not duplicate full SDK, startup, purchase, privacy, or release-readiness protocols here.
