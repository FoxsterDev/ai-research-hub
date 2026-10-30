# XUUnity Session Reference: Session Domain Routes

Conditional reference extracted from `tasks/start_session.md`. All paths are module-relative unless explicitly host/project-qualified. This is not an always-loaded entrypoint or a new policy layer. Look up the complete matching sections, then read the selected instruction owners in full. The compact entrypoint owns the mandatory route and `knowledge/execution_contract.md` owns requirement/read accounting.

## Contents
- Shared Knowledge Routing Hints
- UI Tween Routing Hints
- Risk Routing Hints
- Critical Bug Escalation Rules
- Root Cause Before Patch

## Shared Knowledge Routing Hints
- Do not load the whole `knowledge/` folder by default.
- Load `knowledge/agent_source_of_truth.md` when the task touches multi-agent routing, agent-private memory, prompt entrypoints, duplicated rules between agents, public-core promotion, or source-of-truth placement.
- Load `knowledge/decision_rules.md` when the task changes routing, ownership boundaries, storage destinations, shared-vs-project placement, runtime config mutation policy, or when validation strategy depends on tool-path selection and evidence quality.
- Load `knowledge/cache_lifetime_ownership.md` for any `xuunity review ...` request, or when the task creates, disposes, or refactors an in-process cache of textures, decoded JSON, manifests, or other materialized state derived from a refreshable upstream source. Trigger keywords include `cache`, `MemoryTextures`, `IconCache`, `static Dictionary`, `Dispose`, `Destroy`, `GC.Collect`, `Addressables.Release`, `NativeArray`, `RenderTexture`, `Resources.UnloadUnusedAssets`, `singleton accessor`, repeated popup opens, re-download, or memory growth across logout/login.
- Load `knowledge/lazy_singleton_with_config.md` when the task constructs, mutates, or refactors a singleton service whose behavior depends on a config value that is only known after a later init step. Trigger keywords include mutable `public ... { get; set; }` config property on a singleton, late-bound config, `EnsureXxxService`, ordering bug between `Init()` and config assignment.
- Load `knowledge/validation_lanes.md` when validation strategy depends on choosing between integrated editor tooling, batch compile automation, or ordered scenario automation.
- Load `knowledge/unity_validation_boundaries.md` when validation strategy depends on MCP versus direct Unity CLI, representative Unity-aware evidence, build-config-backed define matrices, or whether shell compile is only a partial signal.
- Load `knowledge/unity_build_size_measurement.md` when the task mentions build size, APK size, AAB size, `BuildReport`, `packedAssets`, `PackedAssetInfo`, asset-size reports, texture/audio/font size, IL2CPP size, `global-metadata`, or `libil2cpp`.
- Load `knowledge/cross_platform_shell_portability.md` when the task writes or fixes bash scripts, wrappers, or CI steps that must also run on Windows Git Bash, or when a Windows CI leg fails while macOS/Linux legs pass. Trigger keywords include `bash`, `shell script`, `Git Bash`, `msys`, `CRLF`, `.gitattributes`, `xargs`, CI matrix, Windows runner.
- Load `knowledge/remote_only_failure_bisection.md` when a failure reproduces only in CI or another non-interactive environment and each verification costs a push-and-wait round-trip. Trigger keywords include `hang`, `timed out`, `only fails in CI`, `cannot reproduce locally`, canceled stuck job.
- Load `knowledge/mcp_scenario_authoring.md` when the task authors, reviews, or debugs Unity MCP scenario JSON or ordered MCP smoke flows, especially when steps include `project_defined_hook`, `project_refresh`, `compile_player_scripts`, `playmode_set`, build profile switches, scripting define mutation, or package/asset/project-settings mutation.
- Load `knowledge/assetbundle_compatibility.md` when the task touches AssetBundles, Addressables-backed remote content, bundled prefabs, bundled ScriptableObjects, bundle manifests, Type Trees, or content intended to work across multiple shipped client versions.
- Load `knowledge/validation_contract.md` when the task must produce or update a stable validation schema across session routing, planning, implementation, or review.
- Load `knowledge/routing_trigger_matrix.md` when classifying a runtime-warning, exception, popup, remote-content, or startup/config-ownership family; it maps signal -> required stack, required owner chain, allowed patch shapes, validation lane, and private capability check, and routes the derived routing contract through the pre-patch gate checker `scripts/routing_gate_check.py` (worked examples in `scripts/tests/routing_fixtures/`).
- Load `knowledge/detached_callback_attribution.md` when a reported exception's stack contains only framework frames, or when triage must identify a call site from telemetry that captured no application frame. Trigger keywords include `no application frame`, `framework-only stack`, `PlayerLoopRunner`, `PlayerLoopTimer`, timer/scheduler callback, thread-pool continuation, identical stacktrace across all samples, `first non-framework frame`.
- Load `knowledge/risk_classification.md` when task assembly needs an explicit risk class or matched policy pack, especially for SDK, startup, manifest/native, monetization, save/load, UI-heavy, or other critical-flow-sensitive work.
- Load `knowledge/severity_matrix.md` when the task requires explicit severity classification or release-blocker framing for findings, risks, or system-health issues.
- Load `knowledge/sdk_stability_scoring.md` when comparing SDK versions, connector tracks, upgrade candidates, or stability-first SDK choices.
- Load `knowledge/request_recovery.md` when task text or inspected code mentions structured error bodies on non-2xx responses, `HttpResponseCode`, `RawResponse`, application error codes, request retry after auth/session recovery, response cache invalidation, stale persisted identity/session state, idempotency keys, safe replay, or full transport/application error contracts.
- Load `knowledge/response_field_gating.md` when a client filter, restore path, or availability check is keyed on a server response field, when a feature reports "nothing found" against a non-empty payload, or when a request-side discriminator constant is compared against a response DTO. Trigger keywords include `SourceType`, optional discriminator, response field equality gate, silent empty result, no matching record.
- Load `knowledge/fail_closed_gate_ordering.md` when a fail-closed validation gate sits next to an availability or fill check, when a fallback branch looks reachable but never fires, or when a suppression reason, error code, or analytics event appears to name the wrong cause. Trigger keywords include `fail-closed`, `fail closed`, `gate ordering`, absent-versus-invalid, no-fill, unreachable fallback, wrong suppression reason.
- Load `knowledge/external_store_open_boundaries.md` when the task involves an attributed store open, cross-promo banner click, install-if-missing flow, StoreKit fallback ordering, or installed-app-versus-store-destination identity divergence (for example AppsFlyer-attributed store opens). `knowledge/decision_rules.md:37` remains a secondary cross-reference.
- Load `knowledge/glossary.md` for protocol/system onboarding, handoff, or when terms such as `project memory`, `previous outputs`, `bridge crossing`, or `release blocker` are likely to be ambiguous.
- Load `knowledge/ios_passive_network_monitoring.md` when the task is about `NWPathMonitor`, iOS path observers, passive network-environment monitoring, VPN or proxy heuristic detection on iOS, tunnel classification, or replacing legacy reachability-style logic.
- Load the matching `knowledge/vendors/<vendor>.md` profile when `xuunity sdk discover <Vendor>` or another SDK update research task targets a vendor with a public profile.
- Load `knowledge/vendors/applovin_max.md` when the task targets AppLovin, AppLovin MAX, MAX, or a MAX-mediated network such as Pangle, ByteDance, Google AdMob, Meta, ironSource, Unity Ads, or Liftoff.
- `knowledge/review_quality_scoring.md` is intentionally not selected from this block: it is owned and triggered by the review path (`tasks/code_review.md` and `reviews/*` whenever a review reaches a concrete verdict), so it loads through those files rather than here.


## UI Tween Routing Hints
- If the task mentions `PrimeTween`, `DOTween`, tween sequences, UI fade or scale transitions, or null or destroyed tween targets, load the narrowest relevant file from `skills/ui_tweens/`.
- Prefer `skills/ui_tweens/primetween.md` when the codebase uses PrimeTween and the bug or review depends on tween target lifetime, callback ownership, or popup close order.


## Risk Routing Hints
- Keep risk routing additive and narrow. Do not turn policy-pack matching into a broad always-on bundle.
- Prefer one primary policy pack:
  - `reviews/policy_packs/sdk_changes.md`
  - `reviews/policy_packs/startup_changes.md`
  - `reviews/policy_packs/manifest_native_changes.md`
  - `reviews/policy_packs/monetization_changes.md`
  - `reviews/policy_packs/save_load_changes.md`
  - `reviews/policy_packs/ui_heavy_changes.md`
- If more than one family clearly matches, keep one primary pack and load only the extra overlays the second family contributes.
- Use `knowledge/risk_classification.md` to infer:
  - `low`
  - `moderate`
  - `high`
  - `critical`
- Escalate risk when multiple independent high-risk signals are present, when validation-path uncertainty is material, or when the task directly touches critical flows.
- Show the trigger reason explicitly in task framing, for example:
  - `risk class: high`
  - `policy pack: startup changes`
  - `triggered by: startup sequencing + SDK initialization`
- Prefer the first matched policy pack by dominant breakage surface:
  - SDK wrapper, version, connector, or vendor-boundary change -> `reviews/policy_packs/sdk_changes.md`
  - startup sequence, first interactive flow, or startup-blocking consent/init change -> `reviews/policy_packs/startup_changes.md`
  - manifest, plist, entitlement, privacy-manifest, JNI, or native bridge contract change -> `reviews/policy_packs/manifest_native_changes.md`
  - ads, rewarded flows, reward grants, purchase-adjacent monetization hooks, ad revenue callbacks, or monetization rollout/config changes -> `reviews/policy_packs/monetization_changes.md`
  - save/load, persistence ownership, serialization boundary, migration, startup restore, cache/local/remote merge, stale-write, or destructive reset changes -> `reviews/policy_packs/save_load_changes.md`
  - long-lived screens, popup or modal flows, first-visible state, async UI gating, duplicate open/close, lifecycle re-entry, or view-versus-backing-state ownership changes -> `reviews/policy_packs/ui_heavy_changes.md`


## Critical Bug Escalation Rules
- Do not keep a bug on generic `tasks/bug_fixing.md` only when the request touches SDK startup, consent sequencing, attribution identity, ad revenue reporting, reward integrity, ads, purchase-adjacent monetization, or third-party wrappers.
- Automatically escalate a bug-fix task into matched SDK-sensitive, startup-sensitive, and/or monetization-sensitive routing when the request, code paths, or referenced files mention signals such as:
  - `AppsFlyer`
  - `Firebase`
  - `OneSignal`
  - `CustomerUserId`
  - `setCustomerUserId`
  - `af_ad_revenue`
  - `logAdRevenue`
  - `rewarded`
  - `RewardedAd`
  - `interstitial`
  - `no-fill`
  - `reward grant`
  - `IAP`
  - `purchase`
  - `initSDK`
  - `startSDK`
  - `consent`
  - `ATT`
  - `startup`
- For these signals, add the minimum relevant stack from:
  - `reviews/policy_packs/sdk_changes.md`
  - `reviews/policy_packs/startup_changes.md`
  - `reviews/policy_packs/monetization_changes.md` when ads, rewards, purchase-adjacent hooks, ad revenue callbacks, or monetization rollout behavior are the main breakage surface
  - `skills/sdk/`
  - `skills/async/`
  - `skills/mobile/startup.md`
  - host-local startup-consent knowledge when available
- If the task touches attribution identity, queued delivery, consent-gated SDK start, or revenue-reporting boundaries, prefer `skills/sdk/initialization.md`, `skills/sdk/wrapper_design.md`, and `skills/sdk/callback_safety.md`.
- If investigation or the patch plan shows that the fix also includes moving code across layers, merging duplicated orchestration, or introducing state machinery such as queues, flushes, or cache-backed fallback behavior, also load `tasks/refactoring.md` as an overlay so the final patch is simplified after it works.


## Root Cause Before Patch
- For SDK, startup, consent, attribution, identity-bound, ad-revenue, and reward-integrity bugs, do not propose or implement a callsite-only fix before tracing the full ownership path.
- For missing asset, missing design, missing config, missing manifest, or runtime-content warnings, do not patch the log emitter, presenter, view, or local service before tracing the upstream owner chain.
- Trace at minimum:
  - the user-visible symptom
  - the wrapper or adapter that emits the event
  - the startup or consent owner that initializes the SDK
  - the identity owner for user or customer ids
  - the reward, entitlement, or revenue owner when monetization correctness is involved
  - any queueing, delay, or retry path between initialization and delivery
- For runtime-content warnings, trace at minimum:
  - symptom
  - immediate caller
  - service or wrapper
  - initialization owner
  - active config/profile
  - content or manifest availability
- If the reported symptom is a missing or empty field on an SDK event, inspect where that field is owned and when the event can be emitted relative to consent, startup readiness, and identity assignment.
- Prefer ownership and sequencing fixes over payload-only patching when the bug touches startup, consent, async delivery, or SDK state.
- Apply the same tracing to the fix's own preconditions, not only the bug's symptom: before adding a defensive branch, guard, or fallback, prove the guarded state is reachable by tracing the controlling condition upstream. `present in source` or `has no early return` is not proof of reachability; if reachability cannot be shown, omit the guard instead of shipping defensive code for an unproven state.
- A local patch such as `set the id immediately before sending the event` is not sufficient by default when the real breakage surface may be SDK readiness, delayed delivery, consent order, or startup ownership.
- A local patch such as `ignore missing content`, `suppress the warning`, or `fallback to loaded true` is not sufficient by default when the real breakage surface may be disabled initialization, inactive config, missing manifest registration, remote-content publication, or service startup ownership.
- For runtime-content warning families, select the required owner chain and allowed patch shapes from `knowledge/routing_trigger_matrix.md`, and validate the derived routing contract with `scripts/routing_gate_check.py` before a source patch; a `local_fix` classification that fails the gate must be reclassified, not forced.
- Do not write a specific claim about observed system behavior (an error code, a timing window, a protocol or CDN detail, a "why it fails this way") into a code comment, log message, or test assertion unless it is backed by a concrete log line, reproduction, or documented source. A plausible-sounding mechanism by analogy to general systems is not evidence for this system. If no verification is available, obtain it (representative logs or another lane from `knowledge/validation_lanes.md`, or explicit user confirmation) or state the claim as an unverified hypothesis in the output instead of encoding it as fact in the fix.
