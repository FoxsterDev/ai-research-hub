# Skill: In-App Purchases

## Use For
- store purchase clients on Unity IAP, StoreKit or Google Play Billing
- consumables, non-consumables and subscriptions: catalog, prices, purchase, delivery, confirmation, restore
- reviews of a purchase flow, a store screen that sells, or an IAP package upgrade

## Host Shared Client First
- Before writing any purchase code, search the host and project for an existing purchase client: host packages, host overlay
  knowledge, project memory and SDK inventory. Search by capability, not only by type name.
- When the host declares a shared purchase client, use it and extend it in its own location. A project-local store client next
  to it is a defect, even when it works. The host overlay that names the shared client owns its contract and overrides this
  file where they differ.
- A vendor asset that ships its own purchase code is stripped during onboarding and replaced by the shared client, not revived.

## Delivery Contract
- Deliver, persist, then confirm. Pay out the content and save it before confirming, finishing, acknowledging or consuming the
  order. An unconfirmed order is redelivered by the store; that redelivery is the crash-safety mechanism, so never confirm first.
- Make delivery idempotent per store transaction id. Keep the granted transaction ids, bounded, in the same save as the content
  they paid out, so a crash between pay-out and confirmation cannot pay twice.
- Distinguish `delivered now`, `already delivered` and `not delivered`. Confirm the first two; leave `not delivered` (for
  example a failed save) unconfirmed for redelivery. Report revenue only for `delivered now`, so a redelivery is not counted twice.
- Never grant from optimistic UI state, a purchase attempt, a client-side price or a closed store sheet.

## Purchase Lifecycle
- Allow one open purchase at a time and keep one owner of that state and of the UI busy signal.
- End the open purchase on every terminal store signal: success, failure, deferral (Ask to Buy, pending payment), store
  disconnect, disposal, and a failure the store cannot tie to a catalog product (no id or a placeholder id). Anything else can
  leave buy buttons disabled until restart.
- Contain exceptions from vendor calls (purchase start, confirmation) and from the game's fulfill callback inside the wrapper.
- A caller's cancellation stops only that caller's wait; the purchase stays open in the store and ends through the same flow.
- Map vendor failure reasons to an internal error enum at the boundary. A user cancellation is silent in the UI.
- Subscribe to the pending-order event before connecting, so orders left unfinished by an earlier session reach the fulfiller.
- Establish the callback thread from evidence. Unity IAP 5 dispatches `StoreController` events on the main thread; state owned
  by the client is then `main_thread_confined` and needs no locks (`skills/async/concurrency_classification.md`).

## Version And Store Gates
- New work uses the Unity IAP 5 `StoreController` API. Do not build on the legacy `IStoreListener` / `UnityPurchasing.Initialize`
  path or on Unity IAP 4.x.
- Check the Google Play Billing Library version the IAP package bundles against Google's deprecation table, fetched from the
  current deprecation FAQ, not from memory. A Billing version past its deadline blocks new apps and updates.
- Another SDK that bundles Billing code, such as an attribution purchase connector, must be built for the same Billing major as
  the IAP package. A connector built for an older track can fail at runtime with missing methods once started. If it is present
  but never initialized, record it as dormant risk and do not start it until the tracks match.
- Declare purchases in the App Privacy label and in Play Data safety; check the IAP package's privacy manifest in the merged
  Xcode project.

## Editor Validation Notes
- The Unity IAP editor fake store draws its default Buy / Cancel dialog with IMGUI, which uGUI automation cannot click and which
  can let the same tap fall through to the button under it. A short tap cooldown after a purchase ends prevents a double buy.
- The `IAP_FAKE_STORE_DEFAULT` scripting define makes the fake store approve purchases without a dialog. Use it only for an
  automated editor run and revert it afterwards.
- Editor play writes to the same persistent save as other editor sessions of the product; restore any test grants.

## Validation
- Editor: prices load from the store, one purchase pays out once, the grant survives a relaunch without a second pay-out.
- Device (sandbox, license testers): cancel, double tap, kill during the purchase (delivered once on the next launch), deferred /
  Ask to Buy, interrupted purchase, offline.
- Device evidence is the release gate; editor and fake-store evidence are not.

## Review Focus
- purchase code outside the host's shared client
- confirmation before the content is persisted
- missing per-transaction idempotency or a ledger kept outside the content's save
- an open purchase that a failure, deferral or disconnect does not end
- revenue reported for redeliveries
- Billing track mismatches between the IAP package and other SDKs
