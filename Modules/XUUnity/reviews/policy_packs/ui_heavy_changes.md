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

## UI PlayMode Post-Validation Proposal
After code changes are done and the normal compile/test gates have passed, a UI-heavy implementation or bug fix should include a proposed PlayMode UI-smoke when the bug could be observed through runtime UI behavior.
- If optional private-pack routing is enabled and a loaded pack provides capability `xuunity.game_qa.runtime_ui_validation` or `xuunity.game_qa.playmode_smoke_planning`, route the post-validation proposal through that resolved pack before authoring or running the smoke. Do not reference private Game QA files by guessed public paths.
- first inspect the available project validation surface, such as MCP capabilities, existing scenario JSON, project-defined hooks, PlayMode tests, UI click helpers, screenshot support, and console or scene evidence
- design the narrowest smoke that can prove or disprove the fixed behavior, naming the exact user-visible steps, expected state transitions, runtime assertions, evidence artifacts, and timeout budget
- prefer EventSystem-driven UI clicks or the project's existing UI input helper over direct presenter method calls when the claim depends on user navigation or button wiring
- use deterministic project hooks, test seams, or fixture data to inject backend, ad, purchase, or remote-content outcomes when the external system would make the smoke flaky
- assert on the real view state that regressed, such as text, button interactability, fill amount, selected tab, visible holder, active pooled item, or animation final value, not only on the backing model
- include a screenshot, scene snapshot, console marker, or hook payload when it materially improves the evidence
- do not run a newly designed UI-smoke automatically unless the user has already asked for validation execution; present the smoke plan and ask for operator approval to run it
- include explicit stop conditions before running: max scenario timeout, max per-step timeout, what counts as stuck, cleanup or PlayMode-exit behavior, and when to fall back to manual validation
- if the needed validation capability is missing or the smoke would be too flaky for automation, report the missing capability or instability reason and leave a concrete manual-check recipe instead of weakening the claim

Use this proposal step to make runtime UI validation available at closeout without forcing a broad end-to-end scenario for every small UI edit.

## UI Runtime Validation Closeout Gate
- A UI-heavy runtime bug fix is not validated by compile success, source inspection, or a neighboring happy path alone.
- Closeout must include automated UI evidence, an operator-approved manual recipe, or an explicit MCP/project capability gap.
- If a loaded private Game QA pack supplies a path coverage taxonomy, name the selected coverage class in the evidence.
- If only a weaker alternate path passed, report it as supporting evidence and keep the required path open.
- If automation is blocked, report the exact missing capability, why it blocks proof, and the smallest hook/scenario/MCP addition needed.

## Optional Game QA Paid Bridge
- Use this bridge only when the resolved private module registry exposes a loaded pack with capability `xuunity.game_qa.runtime_ui_validation` or `xuunity.game_qa.playmode_smoke_planning`.
- Load private Game QA guidance through the pack entrypoints returned by `loadedPacks[]`; do not hardcode private pack ids or private paths in public policy files. Local smoke tests may still assert `xcntp.game_qa_paid_skill` as the current canonical first pack.
- Keep the bridge proposal-first: the paid pack should produce the smoke plan, timeout and cleanup budget, evidence target, and missing-capability report before a new interactive scenario is run.
- Do not use this bridge to force automation for pure visual polish, copy-only changes, or UI changes where runtime behavior cannot materially prove the claim.

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
- A popup/UI warning that depends on remote content, asset bundles, backend design ids, ad-readiness callbacks, or a first-show startup path must not remain UI-heavy only. Co-load `reviews/policy_packs/startup_changes.md`; make startup/config ownership primary when the likely fix depends on initialization owner, active config/profile, content manifest, or service readiness.
- If correctness depends on runtime UI state, first-visible popup behavior, blocking popup behavior, or whether a popup can be proven visible/interactive after async content loads, perform a private Game QA session-plan capability check when optional private-pack routing is available.
- If the private runtime UI validation pack or equivalent project validation capability is unavailable, state that as an explicit validation gap rather than treating source inspection, compile, or static routing as complete UI proof.
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
