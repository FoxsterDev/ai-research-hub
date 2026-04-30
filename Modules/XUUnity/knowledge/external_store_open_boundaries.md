# XUUnity External Store Open Boundaries

## Purpose
Reusable guidance for install-if-missing and cross-promo store-open flows in Unity mobile projects.

## Use For
- cross-promo banner clicks
- install-if-missing flows
- AppsFlyer or similar SDKs that generate attributed destination URLs
- iOS StoreKit versus external App Store fallback decisions
- Android or iOS flows where installed-app identity differs from store-destination identity

## Rules
- Keep installed-app identity separate from store-destination identity.
  - installed-app checks and direct app open should use package or bundle identity
  - store-open flow should use the destination identity required by the store surface
  - do not overload one field to mean both
- Keep navigation policy above the raw SDK callback boundary.
  - an SDK adapter may request attribution or report a generated destination URL
  - the higher orchestration layer should own validation, fallback order, installed-versus-store routing, and product-visible open behavior
- Freeze the concurrency invariant before building callback-correlation machinery.
  - if the product only needs one active external-open request, prefer a single-flight guard
  - ignore or reject the second request explicitly rather than introducing dictionaries, regex routing, or multiplexing without a real requirement
- On iOS not-installed flows, prefer:
  1. in-app StoreKit product page
  2. attributed URL fallback
  3. direct App Store fallback
- Treat direct `itms-apps://...` or equivalent direct-store URLs as the safety net, not the first recovery step after in-app store presentation fails.
- When an attributed URL exists, preserve its chance to carry attribution before dropping to a direct store URL that may lose campaign context.
- Keep fallback logs branch-specific and operational.
  - log whether StoreKit, attributed URL, or direct store URL actually ran
  - log URL scheme when deciding whether attribution ping or web-style validation is meaningful
- Repeated identical store-product failures across different app ids are often stronger evidence of storefront, account, or availability constraints than of presenter or callback-race bugs.
  - use logs to distinguish product-availability failure from bridge-stability failure

## Review Focus
- identifier semantics for installed-app versus store-open paths
- callback-boundary ownership
- fallback order and attribution preservation
- single-flight versus multiplexed orchestration complexity
- operational logging quality for product-debug and runtime review

## Note
This file is decision support and code-shape guidance.
It does not replace device validation, storefront availability checks, or attribution verification in the relevant marketing or analytics backend.
