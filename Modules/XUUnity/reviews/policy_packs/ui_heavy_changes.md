# XUUnity Review Policy Pack: UI-Heavy Changes

## Goal
Strengthen the review and validation stack for UI-heavy work where screen lifetime, async loading, flow sequencing, or state ownership mistakes can create stuck UI, false first-visible state, duplicate actions, progression blocks, or release-visible regressions.

## Trigger When
- the task changes a long-lived screen, tab, page, root UI composition, navigation shell, or screen presenter/controller
- the task changes a popup, modal, one-shot flow, wizard, reward/offer dialog, or other temporary UI that must complete deterministically
- the task changes first-visible screen state, loading gates, skeleton or placeholder behavior, disabled controls, empty states, or unavailable-section handling
- the task changes async UI loading, paged lists, remote-content UI, network-dependent progression, retry behavior, or UI refresh orchestration
- the task changes duplicate open, duplicate close, back navigation, resume, re-entry, interruption, ad-return, or scene-return behavior
- the task changes ownership boundaries between view state, presenter/controller state, backing model state, cached state, or remote authoritative state

## Primary Risk Signals
- first-visible UI can imply data, eligibility, availability, or success that is not yet authoritative
- screen entry is blocked by data that is only required for a deeper step, optional section, or secondary enrichment
- UI actions can be tapped repeatedly while async work, close animation, navigation, or backend reconciliation is still in flight
- the same screen or popup can be opened, closed, re-entered, resumed, or disposed through more than one path
- view lifetime, async lifetime, and backing-state lifetime are owned by different objects without a clear cancellation or rehydration contract
- stale local, cached, or previous-view state can survive refresh, recycling, navigation, scene reload, or account/session change
- loading, retry, or refresh work can trigger layout rebuild spikes, asset-load stalls, input dead zones, or stuck disabled controls

## Mandatory Stack Additions
- `skills/ui/`
- `skills/ui/popup_and_screen_flows.md`
- `skills/core/critical_flow_protection.md` when the UI gates rewards, ads, IAP, save/load, progression, account, session, or other critical flows
- `skills/core/mobile_runtime_safety.md` when pause, resume, focus, back navigation, interruption, or mobile lifecycle behavior matters
- `skills/async/` when UI state depends on await paths, callbacks, cancellation, delayed data, pagination, retries, or network responses
- `skills/optimization/loading_and_microfreeze_prevention.md` when opening, refreshing, scrolling, animating, or closing the UI can cause frame spikes
- `skills/ui/mobile_ux_quality.md` when the task touches product-facing mobile layout, safe areas, touch targets, text scaling, localization, RTL, or readability
- `skills/ui/adaptive_grids.md` when the UI includes adaptive card grids, inventories, stores, rewards, galleries, or scrollable shelves
- `skills/ui/virtualized_scrollrect.md` when large lists, grids, infinite scroll, pooled cells, or paged UI data are involved
- host-local presenter or UI-lifetime overlays only when the project router declares a presenter-driven or host-specific UI ownership model
- `reviews/feature_code_review.md` for implementation or diff review of the changed UI behavior
- `reviews/release_readiness_review.md` when the UI gates a critical flow, rollout confidence, monetization, progression, account state, or ship-readiness decision

## Main Review Questions
- What user-visible UI flow changed, and is it a long-lived screen, a temporary flow, or shared navigation/composition behavior?
- What state is safe to show on first visibility, and what state must remain loading, disabled, hidden, or explicitly unavailable until authoritative data arrives?
- Which owner owns backing state, view-only state, async lifetime, cancellation, current selection, loading state, and final flow completion?
- Can duplicate taps, duplicate opens, duplicate closes, back navigation, animation callbacks, resume, or scene re-entry produce double side effects or stuck state?
- Does the UI degrade truthfully when network data, remote content, SDK-backed data, images, or optional sections are missing or late?
- Are refresh, retry, pagination, sorting, filtering, recycled-cell binding, and stale-response behavior deterministic?
- Does validation cover actual interactive behavior rather than only source inspection or compile-time confidence?

## Required Evidence
- the UI entry points touched, including navigation triggers, buttons, presenters/controllers, views, models, services, async loaders, and close or completion paths
- the first-visible-state contract: what may appear immediately, what must wait, what can be partial, and what must block entry entirely
- ownership evidence for loading state, disabled state, selected state, error state, empty state, authoritative backing state, and UI-only transient state
- lifecycle evidence for open, close, dispose, back, resume, interruption, scene change, view reload, re-entry, and repeated user actions
- async evidence for cancellation, stale response handling, retries, timeout or failure behavior, and main-thread handoff before touching Unity objects
- layout or performance evidence when the change adds heavy UI hierarchy, dynamic layout, list/grid refresh, image loading, animations, or frequent Canvas rebuilds
- validation evidence for happy path, slow data, failure, retry, duplicate action, reopen, close-during-load, resume, and stale-data cases proportional to risk

## Validation Focus
- first-visible state is truthful and does not imply completion, ownership, eligibility, reward, purchase, save, or backend success prematurely
- optional or later-step data failure does not suppress a safe first screen when the entry contract can still be satisfied
- required data failure does not show a misleading or partially interactive screen
- duplicate open, close, tap, back, and animation-completion paths are idempotent and leave controls in a usable state
- async UI work is cancelled, ignored, or rehydrated safely when the view closes, reloads, recycles, or resumes
- network-dependent progression blocks only the dependent step, not unrelated UI or already-valid local interactions
- scroll, grid, image, and refresh paths avoid layout rebuild spikes, full-list instantiation, blocking asset loads, and stale recycled-cell state
- interactive runtime validation covers actual screen entry, user input, loading transitions, close/reopen, background/resume, and failure paths

## Common Failure Modes
- popup opens with optimistic success or reward state before the backing operation is complete
- screen entry is blocked by optional enrichment that could have loaded after first visibility
- async completion updates a destroyed, hidden, recycled, or no-longer-current view
- duplicate tap, close, or back handling fires the same command twice or completes a one-shot flow twice
- close-during-load leaves input disabled, a spinner visible, a navigation lock held, or a pending completion unresolved
- stale server, cache, or previous-screen data reappears after refresh, filter change, account change, or scene re-entry
- recycled list or grid cells retain old listeners, selection, loading images, timers, badges, or error state
- retry or pagination appends late responses into a newer query, filter, sort, or dataset revision
- layout, localization, safe-area, or larger-text changes make critical controls unreachable or overlapping on mobile

## Release-Risk Framing
- Treat UI that can block progression, monetization, account access, save/restore, reward claim, purchase-adjacent entitlement, or mandatory consent as high risk until the interactive flow is validated.
- Treat false first-visible state, duplicate side effects, stuck disabled input, unresolved modal completion, or stale authoritative data as release-sensitive behavior even when the code compiles and the screen looks correct once.
- Treat editor-only or screenshot-only review as incomplete when correctness depends on timing, async data, input, navigation, resume, scrolling, or lifecycle re-entry.
- Treat UI-heavy changes with remote config, backend content, experiments, staged rollout, or device-specific layout as production-sensitive because low-percentage or platform-specific variants can still break the exposed audience.

## Co-loading Rule
- Prefer this pack as the primary pack when UI lifetime, user-visible flow sequencing, first-visible state, async UI loading, duplicate action protection, or view-versus-backing-state ownership is the main breakage surface.
- If the same UI change primarily gates monetization, save/load, startup, SDK, manifest/native, or store behavior, keep the dominant pack primary and load only the UI-heavy additions needed for screen and interaction correctness.
- Do not use this pack for purely visual polish, copy, static art, or isolated layout tweaks unless they affect interaction safety, critical-flow gating, lifecycle behavior, async state, or release-visible correctness.

## Final Review Must Report
- the UI surfaces touched and whether each is a long-lived screen, temporary flow, shared navigation shell, or collection-heavy surface
- the active policy pack and trigger reasons
- the first-visible-state contract and any blocked, degraded, hidden, partial, or unavailable states
- the owner of backing state, view state, async lifetime, loading/disabled state, and flow completion
- evidence for duplicate action handling, close/reopen, back navigation, resume, stale responses, and destroyed or recycled views
- validation performed and validation still missing, especially interactive runtime, slow data, failure, duplicate input, close-during-load, resume, and device-layout coverage
- release-risk classification for stuck UI, false state, duplicate side effects, critical-flow blocking, performance hitches, and rollout-sensitive variants

## Rule
- Compose existing shared reviews and skills. Do not duplicate full UI architecture, mobile UX, async, performance, or release-readiness protocols here.
