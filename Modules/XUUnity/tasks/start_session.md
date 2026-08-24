# XUUnity Task: Start Session

## Goal
Assemble the minimum prompt stack for the current Unity task.
Start every new task from a senior mobile-production mindset.
Support shorthand commands such as `xuunity refactor this code` and expand them into the full working context automatically.
Assume Unity `6000+`, mobile target constraints, zero-crash and zero-ANR expectations, and no microfreezes on critical flows.

## Entrypoint Kernel
This block is head-complete and authoritative: it carries the must-load rule, the routing procedure, and the output/execution contract. Everything below elaborates it. If the body is truncated or skimmed, this kernel alone is sufficient to route correctly and to know what to emit.

**Must-load.** A selected router, protocol entrypoint, or start-session file is atomic context: load it first line through EOF before applying it. A partial read, summary, excerpt, search hit, or fixed line window is not valid entrypoint loading.

**Route (one-shot, then act).** For any request: (1) classify the task; (2) resolve the target project from referenced source paths; (3) infer the primary role and risk class; (4) select the minimum stack — role, codestyle, core skills, task file, and only the matched skills / reviews / utilities / knowledge / policy packs; (5) for SDK, startup, consent, attribution, reward, or runtime-content families, trace the owner chain and pass the root-cause gate BEFORE any source patch. Full procedure is `## Process` below; routing targets are the shorthand and routing-hint sections below.

**Execution contract.** Derive and surface the compact execution contract before patching, large review output, or implementation planning. Field-set owner: `knowledge/execution_contract.md`; validation cluster: `knowledge/validation_contract.md`. Reference the owner instead of copying the field list.

**Root-cause gate.** Source patches for SDK, startup, consent, attribution, reward, or runtime-content families are blocked until the consumer, producer, init owner, active config/profile, and content/manifest availability have been inspected and recorded (`## Root Cause Before Patch`). A `local_fix` that fails `scripts/routing_gate_check.py` must be reclassified, not forced.

**Pre-edit gate.** Before the first source-mutating tool call in an implementation or bug-fix task, state: the selected stack, explicitly naming whether `AIModules/XUUnityInternal/` overlay and the matched `skills/` families (e.g. `skills/async/` for any cancellation/retry/backoff work) were checked; whether an existing implementation of the mechanism being added (retry policy, cache, wrapper, client) was searched for and found or ruled out, not assumed absent; and, for any claim about observed system behavior driving the fix (an error code, a timing pattern, a protocol or CDN detail), its evidence basis or an explicit `unverified hypothesis` label. Re-run this gate whenever a fix design is abandoned and a new one starts — a long iterative session earns one gate per design attempt, not one gate total for the whole session. Loading a router or protocol file is not evidence that its content was applied; this gate is what makes application checkable. Derived from a session where the internal overlay and an existing sibling implementation both already existed unread, and an unverified claim reached shipped code before being challenged. This gate is prose, not enforcement — nothing blocks a mutating call if it is skipped. A task item, checklist entry, or sentence asserting that the gate was satisfied is not evidence. The gate is satisfied only by naming, in the message immediately before the first mutating call of each edit batch: (a) the `codestyle/` files read in this session, (b) the matched `skills/` families including `skills/core/`, (c) the matched project `SkillOverrides/` files, (d) for a path with an async, callback, or thread boundary, or code attached after an `await` or thread hop, the resumption-thread map; otherwise `not_applicable` with a reason, and (e) the existing-implementation search result. Where the harness exposes a task-tracking tool, tracking those items additionally helps the harness resurface them, but a closed task proves nothing about whether the check ran: this wording comes from a session where a gate task was created and closed while `codestyle/`, `skills/async/`, `skills/core/` and the project `SkillOverrides/` were never opened, and the resulting patch shipped an off-main Unity API read onto a monetization path. Re-run the gate per edit batch; "the design was approved, so the implementation is mechanical" is the thought that precedes skipping it.

**Concurrency evidence gate.** Before adding or retaining a lock, atomic, semaphore, concurrent collection, thread hop, or custom thread-safe wrapper, classify the path as `main_thread_confined`, `temporal_reentrancy`, `cross_thread_shared`, or `unknown`; name the actual readers, writers, ingress thread, and post-await resumption evidence; and record which project-local capabilities were inspected. Callback or `await` presence alone is not cross-thread evidence. Owner: `skills/async/concurrency_classification.md`.

**Required output (re-state before the first mutating tool call per the Pre-edit gate above, and again immediately before emitting final output — do not assume either stayed salient across a long turn):**
- Selected stack
- Inferred risk class, if any
- Derived execution contract (field set from `knowledge/execution_contract.md`)
- Missing project memory, if any
- Main risk areas for the session
- Critical flows that must not regress
- Concurrency and thread-safety classification when applicable, otherwise `not_applicable`; validation focus for exception safety and performance

**Owner-file rule.** Put detailed rules, command catalogs, and matrices in explicitly routed owner files; longer knowledge, review, skill, and reference files are valid only when trigger-loaded and are never default entrypoints. Entrypoint adequacy is governed by the byte-complete-kernel invariant (`scripts/check_entrypoint_kernel.py`: every must-survive marker within the smallest head window, contract restated in the tail), not by a fixed line count.

## Process
1. Classify the task from the user request, even if the request is shorthand.
1a. Resolve the target project from referenced local source paths before role and stack assembly.
1b. If all referenced local source paths fall under one project root, treat that project as resolved immediately.
1c. If the repo contains multiple Unity projects and no concrete target project can be resolved, do not assume the current workspace root is the target project; ask for clarification or perform minimal project discovery first.
1d. If the target project is resolved, load that project's router before final stack narrowing.
1e. If this is the first `xuunity` request for a new agent or project and the agent supports durable private memory, load `knowledge/agent_source_of_truth.md` and use `utilities/agent_private_bootstrap.md` to install or refresh a thin agent-private router before continuing. If unsupported, continue normally and record the gap only when relevant.
1f. Perform one cheap delegation check: identify a routine lane only when its algorithm, inputs, allowed mutations, expected outputs, and stop conditions are already exact and it can run independently while the root agent does useful work. If no such lane exists, do not load delegation guidance and continue normally.
1g. When a routine lane exists, load `../../AgentOperations/subagent_delegation.md`, apply the host router's model choice, and create its complete task packet before spawning. Any unexpected result is `needs_smart_escalation`; the routine subagent stops and returns evidence instead of diagnosing or fixing it.
2. Detect whether the user requested a specific role.
3. If no role was requested, infer the best primary role from the task type and risk profile.
3a. Infer whether the task needs explicit risk classification and policy-pack routing.
3b. If the task touches SDK initialization, consent sequencing, attribution identity, ad revenue reporting, reward integrity, startup ownership, or third-party wrapper code, require root-cause tracing before proposing a source-level fix.
3b-i. If a runtime warning or exception stack crosses feature startup, a flow or presenter, an async service, a remote asset/content service, SDK/service initialization, or build/runtime config, classify the task at minimum as `bug_fixing` with `startup/config ownership` as an overlay. Do not keep it as a local UI, local presenter, or local service bug only.
3b-ii. For those runtime warnings or exceptions, a source patch is blocked until the consumer, producer, initialization owner, active config/profile, and content or manifest availability have been inspected and recorded in the compact execution contract.
3c. If investigation or the patch plan shows that a bug-fix task will move ownership between layers or introduce non-trivial state orchestration such as queues, flush paths, cache fallbacks, helper wrappers, or duplicated triggers, keep `tasks/bug_fixing.md` as the primary task but also load `tasks/refactoring.md` as a behavior-preserving overlay.
4. Decide whether the task needs one role or a small role group.
5. Select the primary role file and only the minimum useful supporting role files.
6. Select one or more relevant files from `codestyle/`.
7. Load baseline safety skills from `skills/core/`.
8. Infer and load only the relevant task-specific skill packs from `skills/`.
8a. For any implementation task such as bug fixing, refactoring, feature development, SDK work, or native-plugin work, always load the testing baseline:
  - `skills/tests/testing_doctrine.md`
  - the narrowest additional files from `skills/tests/` only when the task or planned validation actually needs them
8b. Treat the testing doctrine as a default development constraint, not only as a review-time reference. Any new tests authored during the session must follow it.
8c. Do not assume that tests must always be written.
  - Prefer writing tests near the end of the implementation after the production shape is stable enough to test.
  - If test writing is optional or materially expensive relative to the task, ask the user whether they want tests instead of spending large token budget by default.
  - If tests are clearly required by risk, regression surface, or an explicit user request, state that briefly and proceed.
9. Select one task file.
10. Add only the review, utility, and platform files required.
10a. Add root-level `knowledge/` files only when a concrete routing hint or the selected task or review requires them.
10b. If the task is risk-sensitive, load only the minimum matched policy-pack files from `reviews/policy_packs/` and surface the trigger reason explicitly.
11. If the host repo provides `AIModules/XUUnityInternal/`, load only the minimum relevant internal shared overlay files after the public `XUUnity` core.
11a. When a host-local internal overlay exists, prefer starting from its host-local overlay entrypoint before loading narrower internal files.
12. When the task touches internal presenter-driven UI, choose the narrowest internal UI skill by lifetime shape (these live in the host internal overlay at `AIModules/XUUnityInternal/skills/ui/`, not the public core, and load only when that overlay exists):
   - internal `skills/ui/screen_presenters.md` for long-lived screens, tabs, pages, or root screen composition
   - internal `skills/ui/flow_presenters.md` for one-shot popups, modal flows, or explicit flow-result presenters
   - internal `skills/ui/presenter_development.md` only as the lifetime-map entry file or when the task spans more than one presenter shape
12a. Resolve optional private/paid module overlays before project memory when the user asks for private modules, paid packs, premium skills, Game QA paid validation, or when a known loaded private-pack trigger matches the task. If `scripts/module_registry_tool.py` exists, prefer the latest user-cache registry from `~/.xuunity/cache/resolved_modules/`; run `python3 Modules/XUUnity/scripts/module_registry_tool.py rollsync --project-root <host-root>` when the cache is missing, stale, or the user explicitly asks to verify loading.
12b. Treat the resolved registry as a user-local overlay contract:
   - use `loadedPacks[]` as eligible prompt-stack candidates
   - use `lockedPacks[]` and `invalidPacks[]` only to explain why a pack cannot be used
   - never write resolved private-pack paths or manifests into the project repo
   - never load private pack files by guessing paths outside the registry
   - load only the entrypoints declared by the matched loaded pack
12c. Match `loadedPacks[].routing.triggers` against the current task text after public-core and internal-overlay routing have narrowed the stack. Public routing may also require a stable capability tag with `session-plan --require-capability <capability-id>`. If a loaded private pack matches by trigger or required capability, add only its manifest-declared entrypoints and record the pack id in `matched_private_packs` inside the execution contract.
12d. For Game QA paid work, prefer a loaded private pack that provides capability `xuunity.game_qa.runtime_ui_validation` or `xuunity.game_qa.playmode_smoke_planning`. Load it through the registry paths rooted at the resolved private module, not through public `Modules/XUUnity` paths. Local smoke tests may still assert canonical pack id `xcntp.game_qa_paid_skill`; public policy should route by capability first. If no matching pack is loaded, or the pack is locked or invalid, state the gap and continue with public validation planning instead of silently degrading into non-registered private content.
12e. When `scripts/module_registry_tool.py session-plan` is available, use it as the preferred private-runtime session-routing proof. Copy only its public-safe `sessionContract` fields into planning, reports, or project output; do not copy private entrypoint paths or private pack bodies into company/public artifacts.
13. Load project memory before using previous outputs.
14. Check `Assets/AIOutput/ProjectMemory/SkillOverrides/` for matching local overrides.
15. For gameplay projects, load durable guidance from `Assets/AIOutput/ProjectMemory/` by default.
16. Do not load historical reports from `Assets/AIOutput/` by default.
17. Load historical reports from `Assets/AIOutput/` only when the task is investigating behavior drift, reconstructing legacy intent, or researching old bug root causes.
18. If historical reports are loaded, keep them lower-priority than current-truth memory and current source code.
19. Identify whether the task touches shared state, async flows, native boundaries, startup, UI, rendering, loading, monetization, or other critical project flows.
19a. If the task touches cache design, persistence shape, startup override, fallback state, or remote-config application, derive the minimal product contract before implementation:
  - source count
  - persistence unit
  - merge boundary
  - partial-update semantics
  - compatibility envelope
  - platform storage backend
19b. For cache, persistence, startup override, or remote-config tasks, prefer the smallest architecture that satisfies the derived product contract and restate that contract before broader implementation if redesign churn appears.
20. Decide the safest implementation shape before writing code.
20a. Before implementation, review, or planning output is finalized, derive the compact execution contract for the session. `knowledge/execution_contract.md` is the single owner of the field set, field meanings, and contract rules (brevity, `none` instead of omitting, update-on-change, `required_validation` derivation for `tasks/bug_fixing.md`, and `required_self_review` obligations). Reference the owner instead of re-listing the fields here.
20b. Apply the Pre-edit gate from the Entrypoint Kernel here, before the first `Edit`/`Write` call: confirm the skill-loading steps above (6-11) were actually followed for this task, not only the router/entrypoint files — in particular that `AIModules/XUUnityInternal/` and any matched `skills/` family were checked for an existing pattern or implementation before writing a new one. Loading a file earlier in the session is not the same as having applied it here; if step 6-11 was skipped for time pressure, do it now before the first edit, not after a defect surfaces.
21. If the task depends on validation, confirm whether the available tool path is representative for a Unity project before running it; if not, avoid defaulting to substitute shell-driven validation and plan for an explicit validation gap.
22. Do not treat the mere presence of a Unity binary or CLI entrypoint as proof that direct shell-launched Unity validation is allowed for the current repo.
22a. If the project exposes a supported Unity MCP path, treat that MCP path as the default Unity-aware validation surface.
22b. When Unity MCP is available for the project, do not start with direct Unity CLI, `-batchmode`, `-runTests`, `-executeMethod`, or shell-side generated-project compile as the primary validation route.
23. Before running Unity via shell, batchmode, `-runTests`, `-executeMethod`, or similar editor automation, check host-local overlays, project routers, and project memory for validation-path constraints.
24. If a host-local or project-local rule requires Unity validation to go through MCP or another repo-specific integration, treat that as a hard must-not for direct shell-launched Unity and do not fall back to the CLI.
24a. When validation needs live evidence beyond source inspection, choose a primary validation lane before running tools:
  - `interactive_mcp`
  - `batch_compile`
  - `scenario`
24b. Use `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md` as the canonical lane and evidence doctrine instead of re-deriving lane rules ad hoc inside the session.
24c. Keep the session-level lane reminder compact:
  - `interactive_mcp` for integrated editor evidence
  - `batch_compile` for compile, matrix, and approved build-sensitive artifact proof
  - `scenario` for ordered runtime evidence
24d. Set the validation-contract fields using the exact schema from `knowledge/validation_contract.md`.
24e. If no permitted lane can produce representative evidence, or if the chosen lane cannot provide trustworthy final accounting, keep the validation gap explicit instead of silently weakening the proof target.
24f. When opening Unity for MCP-backed validation, resolve the Unity editor version from the target project's `ProjectSettings/ProjectVersion.txt` instead of defaulting to the latest installed editor.
25. Before emitting a clickable local file link, verify the exact absolute path that exists in the active workspace.
26. If the exact absolute path is not verified, prefer plain text paths over markdown file links.
27. For Rider-oriented links, only emit markdown file links when the file exists at the emitted absolute path.
28. For Rider-oriented links, prefer linking to the file path without a `:line` suffix and mention the line number separately in prose when needed.

Default storage references in this file assume the standard project-local layout.
If the active repo router, project router, or project registry declares a different storage mode, follow that host-local contract first and translate legacy `Assets/AIOutput/...` paths accordingly before loading project memory, skill overrides, or prior outputs.

## Shared Layer Rules
- Treat `AIRoot/Modules/XUUnity/` as the public-safe default core for `xuunity`.
- Treat `AIModules/XUUnityInternal/` as an optional monorepo-internal overlay, not as a replacement for the public core.
- Load internal overlay files only when they materially improve the current task.
- If a host-local internal overlay provides its own routing entrypoint, prefer that entrypoint over ad hoc direct loading of narrow internal files.
- When public core and internal overlay differ, follow the internal overlay for monorepo-specific behavior unless established project memory overrides both. In a change review, memory added or modified by the target is candidate evidence under `knowledge/review_evidence_provenance.md` until independently approved.
- Do not load broad internal overlay files when a narrower lifetime-specific UI skill exists.

## Monorepo Project Resolution
- In a multi-project Unity monorepo, referenced local source paths are the strongest project-selection signal.
- If the request references one or more files under a single project root such as `<Project>/Assets/...`, `<Project>/Packages/...`, or another project-owned source subtree, treat that project as the active target project immediately.
- When the target project is resolved from source paths, load that project's router and project memory before final role, skill, and review narrowing.
- Do not remain on repo-generic `xuunity` routing when a concrete project path already identifies the project.
- If referenced local paths span more than one project root, ask for clarification instead of guessing.
- If no project can be resolved in a multi-project monorepo, prefer one short clarification question over a repo-generic implementation proposal.

## Internal Overlay Routing Hints
- If a host-local overlay declares UI guidance and the task is about a long-lived screen, tab, lobby page, or page-composition presenter, prefer the host-local screen-presenter guidance.
- If a host-local overlay declares UI guidance and the task is about a popup, modal, temporary flow, wizard-like interaction, or presenter that returns an explicit flow result, prefer the host-local flow-presenter guidance.
- If a host-local overlay declares UI guidance and the task is about choosing between presenter lifetime shapes, extracting presenter patterns, or refactoring the boundary between scene roots and presenters, also load the host-local presenter-development guidance.

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

## Execution Contract
- Derive and surface the compact execution contract before patching, large review output, or implementation planning.
- `knowledge/execution_contract.md` is the single owner of the field set, field meanings, and contract rules; its validation cluster is owned by `knowledge/validation_contract.md`. Reference the owner instead of copying the field list.
- Use `utilities/routing_debug_template.md` when the user asks for routing/start-session debug, when private-pack loading must be accounted for, or when root-cause gating blocks a local patch and the loaded stack must be made explicit.

## Shorthand Expansion Rules
Interpret short commands by intent:
- `xuunity refactor ...` -> `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity extract service ...`, `xuunity split class ...`, `xuunity split presenter ...`, `xuunity decouple ...`, `xuunity untangle ...`, or `xuunity migrate ...` should also prefer `tasks/refactoring.md` plus `skills/refactoring/`
- `xuunity fix ...` -> `tasks/bug_fixing.md`
  - always include the testing baseline from `skills/tests/testing_doctrine.md`
  - when the request also carries SDK, startup, consent, attribution, identity, ad revenue, or third-party wrapper signals, keep `tasks/bug_fixing.md` as the task file but also load the matched SDK-sensitive and startup-sensitive stack instead of staying on a narrow local fix route
  - when the request reports a runtime warning or exception that crosses feature startup, a flow/presenter, async service, remote asset/content service, SDK/service init, or active config/profile, keep `tasks/bug_fixing.md` as the task file but add `startup/config ownership` routing and block local source patches until the owner chain is checked
  - when investigation or the patch plan shows that the fix changes ownership boundaries or adds non-trivial orchestration or state handling, also load `tasks/refactoring.md` as a cleanup and behavior-preservation overlay
- `xuunity feature request ...` or `xuunity intake feature ...` -> `tasks/feature_request_intake.md`
- `xuunity feature design ...` or `xuunity design feature ...` -> `tasks/feature_design_brief.md`
- `xuunity architecture plan ...`, `xuunity arch plan ...`, `xuunity plan this subsystem split ...`, or `xuunity plan the architecture ...` -> `tasks/architecture_plan.md`
- `xuunity feature screen ...` -> `tasks/feature_development.md` plus internal `skills/ui/screen_presenters.md` when the host overlay exists
- `xuunity feature popup ...` -> `tasks/feature_development.md` plus internal `skills/ui/flow_presenters.md` when the host overlay exists
- `xuunity feature presenter ...` -> `tasks/feature_development.md` plus the narrowest internal presenter skill by inferred lifetime shape
- `xuunity implementation plan ...` or `xuunity feature plan ...` -> `tasks/implementation_plan.md`
- `xuunity validation plan ...` or `xuunity feature validation ...` -> `tasks/validation_plan.md`
- `xuunity rollout plan ...` or `xuunity feature rollout plan ...` -> `tasks/rollout_plan.md`
- `xuunity sdk discover <Vendor> ...`, `xuunity sdk check <Vendor> ...`, or `xuunity sdk scout <Vendor> ...` -> `tasks/sdk_update_research.md`
  - this is the canonical one-command SDK update candidate research flow
  - if the command includes `for <Project>`, resolve that project explicitly
  - if no project is named, use the active resolved project or the Unity project that owns the current working directory
  - if the workspace is a multi-project monorepo root and no project is resolved, ask one short clarification question
  - load `knowledge/sdk_stability_scoring.md`, `reviews/policy_packs/sdk_changes.md`, `skills/sdk/discovery_and_inventory.md`, and the matching `knowledge/vendors/<vendor>.md` profile when available
  - when a vendor component is named, such as `xuunity sdk discover AppLovin Pangle`, keep one command but run component-mode research inside the task
  - when the command says `for all apps`, run portfolio-mode research and group projects by safe update lane
  - save the resulting research report before returning the final recommendation
- `xuunity sdk profile design <Vendor> ...`, `xuunity sdk research profile <Vendor> ...`, or `xuunity system design sdk research profile <Vendor> ...` -> `utilities/sdk_vendor_research_profile_template.md`
  - this is the canonical flow for creating a new vendor-specific SDK update research profile
  - compare against `knowledge/vendors/appsflyer.md` and `knowledge/vendors/applovin_max.md`
  - require source-of-truth ladder, candidate identity, wrapper-to-native version mapping, mandatory extraction, breaking-change/API migration checkpoint, hard gates, scoring rules, validation, and command examples
  - create or update `knowledge/vendors/<vendor>.md` only when the user asks for integration or has approved the profile design
- `xuunity commit this work ...`, `xuunity commit all changes ...`, `xuunity push local changes ...`, `xuunity push all changes ...`, `xuunity publish local changes ...`, `xuunity publish all changes ...`, or `xuunity split these changes into commits ...` -> `tasks/change_delivery.md`
- `xuunity agent bootstrap ...`, `xuunity bootstrap agent memory ...`, `xuunity setup agent memory ...`, `xuunity install working discipline ...`, or `xuunity refresh working discipline ...` -> `utilities/agent_private_bootstrap.md`
- `xuunity task registry bootstrap ...`, `xuunity enable task registry ...`, or `xuunity setup task history ...` -> `utilities/task_registry_bootstrap.md`
- `xuunity start tracking this task ...`, `xuunity open task record ...`, or `xuunity create task record ...` -> `utilities/task_tracking_start.md`
- `xuunity finish the work ...`, `xuunity close this task ...`, `xuunity record this fix ...`, or `xuunity post and record this work ...` -> `utilities/task_registry_append.md`
- `xuunity publish the work ...` -> `tasks/change_delivery.md` first, then any host-declared closeout or reporting route from the repo router
- `xuunity this works ...`, `xuunity this has bugs ...`, `xuunity reopen this task ...`, `xuunity mark this validated ...`, or `xuunity customer says it works ...` -> `utilities/task_feedback_capture.md`
- `xuunity task registry reconcile ...`, `xuunity rebuild task index ...`, or `xuunity sync task snapshots ...` -> `utilities/task_registry_reconcile.md`
- `xuunity validate task registry ...`, `xuunity check task events ...`, or `xuunity task registry lint ...` -> `utilities/task_registry_validate.md`
- `xuunity task metrics ...`, `xuunity task registry metrics ...`, or `xuunity ai delivery metrics ...` -> `utilities/task_metrics_rollup.md`
- `xuunity archive task registry ...`, `xuunity task registry rollover ...`, or `xuunity review task registry retention ...` -> `utilities/task_registry_archive.md`
- `xuunity delivery risk ...` or `xuunity feature risk review ...` -> `reviews/delivery_risk_review.md`
- any normal XUUnity task command that includes an explicit Claude execution
  selector such as `via claude`, `with claude`, `use claude`, `through claude`,
  `using claude`, `через claude`, or `с claude` -> keep the normal task routing
  and add the external AI CLI overlay:
  - provider selector: `claude_cli`
  - operation: `AIRoot/Operations/XUUnityAiCliOrchestrator/`
  - auth policy: official login/OAuth only
  - billing policy: subscription quota first, no API-key fallback
  - proof gate: Claude must prove official subscription login, subscription
    quota, enforced access policy, and resolved model before selection
  - if Claude is unavailable or fails proof gate, continue with the local
    XUUnity stack and report the provider gap
  - do not change the primary task file; `xuunity fix the bug via claude` still
    routes as bug fixing, `xuunity review ... via claude` still routes as review
- `xuunity feature ...` or `xuunity implement ...` -> `tasks/feature_development.md`
  - always include the testing baseline from `skills/tests/testing_doctrine.md`
- `xuunity review the git change ...` -> `reviews/git_change_review.md`
- `xuunity git change review ...` -> `reviews/git_change_review.md`
- `xuunity review tests ...` -> `reviews/test_quality_review.md`
- `xuunity tests review ...` -> `reviews/test_quality_review.md`
- `xuunity review test quality ...` -> `reviews/test_quality_review.md`
- `xuunity full review ...` -> `reviews/full_review.md`
- `xuunity review all ...` -> `reviews/full_review.md`
  - classify target kind first:
    - `current_state_sdk`
    - `current_state_feature`
    - `current_state_project`
    - `change_sdk`
    - `change_feature`
    - `change_project`
  - activate matching policy packs before final bundle assembly:
    - `reviews/policy_packs/sdk_changes.md`
    - `reviews/policy_packs/startup_changes.md`
    - `reviews/policy_packs/manifest_native_changes.md`
    - `reviews/policy_packs/monetization_changes.md`
    - `reviews/policy_packs/save_load_changes.md`
    - `reviews/policy_packs/ui_heavy_changes.md`
  - prefer one aggregate report with canonical merged findings unless the user explicitly asks for per-protocol reports
- `xuunity design review ...`, `xuunity review designs ...`, `xuunity design retro ...`, `xuunity audit designs ...`, or `xuunity score designs ...` -> `utilities/design_retro_review.md`
- `xuunity review ...` -> `tasks/code_review.md`
- `xuunity sdk breakage review ...` -> `reviews/sdk_breakage_review.md`
- `xuunity sdk ...` -> `tasks/sdk_integration.md` or `reviews/sdk_code_review.md` based on whether the user asks to build, update, or review
- `xuunity plugin ...` or `xuunity native ...` -> `tasks/native_plugin_work.md` or `reviews/native_plugin_review.md` based on intent
- `xuunity system extract review artifact ...` -> `utilities/review_artifact_extract.md`
- `xuunity system merge review artifacts ...` -> `utilities/review_artifact_merge.md`
- `xuunity system integrate review artifacts ...` -> `utilities/review_artifact_merge.md`
- `xuunity extract implementation pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity extract presenter pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity system extract implementation pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity system extract presenter pattern ...` -> `utilities/implementation_pattern_extract.md`
- `xuunity extract ...` -> `utilities/knowledge_extraction_triage.md`
- `xuunity system extract ...` -> `utilities/knowledge_extraction_triage.md`
- `xuunity system merge ...` -> `utilities/skill_merge.md` plus `utilities/knowledge_merge.md`
- `xuunity system intake review ...` -> `utilities/knowledge_intake_review.md`
- `xuunity apply approved extraction ...` -> `utilities/knowledge_integration.md`
- `xuunity system integrate approved ...` -> `utilities/knowledge_integration.md`
- `xuunity system apply approved extraction ...` -> `utilities/knowledge_integration.md`
- `xuunity intake ...` -> `utilities/knowledge_intake_review.md`
- `xuunity apply approved ...` -> `utilities/knowledge_integration.md`
- `xuunity integrate approved ...` -> `utilities/knowledge_integration.md`
- `xuunity system progress review ...` -> `utilities/system_progress_review.md`
- `xuunity system next milestone ...` -> `utilities/system_progress_review.md`
- `xuunity system registry refresh ...` -> `utilities/system_registry_refresh.md`
- `xuunity system refresh project registry ...` -> `utilities/system_registry_refresh.md`
- `xuunity system project registry audit ...` -> `utilities/system_project_registry_audit.md`
- `xuunity system registry audit ...` -> `utilities/system_project_registry_audit.md`
- `xuunity system research watch ...` -> `utilities/internet_research_watch.md`
- `xuunity system research what is new ...` -> `utilities/internet_research_watch.md`
- `xuunity system evaluate ...`, `xuunity system installation review ...`, or `xuunity system review this installation ...` -> `utilities/system_self_evaluation.md`
- `xuunity system protocol clean review ...`, `xuunity system protocol cleanup review ...`, `xuunity system clean protocol review ...`, `xuunity system sanitary review ...`, or `xuunity system public core sanitation ...` -> `utilities/system_protocol_clean_review.md`
- `xuunity system health improve ...` -> `utilities/system_health_review.md` in bounded improve mode
- `xuunity system health review ...` or `xuunity system health ...` -> `utilities/system_health_review.md` in review mode
- `xuunity system output cleanup ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup all aggressive ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup ai outputs ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup stale reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup projects ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup apply ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system cleanup aggressive ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup all ...` -> `utilities/system_output_cleanup.md`
- `xuunity system cleanup ...` -> `utilities/system_output_cleanup.md`
- `xuunity system apply cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system apply approved cleanup ...` -> `utilities/system_output_cleanup_apply.md`
- `xuunity system archive old reports ...` -> `utilities/system_output_cleanup.md`
- `xuunity system prune old archives ...` -> `utilities/system_output_cleanup.md`
- `xuunity system audit ai clutter ...` -> `utilities/system_output_cleanup.md`
- `xuunity system evaluation cadence ...` -> `utilities/system_evaluation_cadence.md`

### Cleanup Routing Notes
- Treat legacy shorthand `xuunity system output cleanup ...` as an exact alias for `xuunity system cleanup ...`.
- Treat `xuunity system cleanup aggressive ...`, `xuunity system cleanup all aggressive ...`, and user phrasing such as `hard cleanup`, `prune old archives`, `stop keeping so much history`, or `project changes every week` as explicit volatile-project-mode triggers for `utilities/system_output_cleanup.md`.
- When those triggers are present, the cleanup execution contract should explicitly include:
  - `cleanup_mode: aggressive`
  - `volatile_project_mode: yes`
  - `reference_rewrites_required: yes|no`
  - `archive_recheck_required: yes`
- For aggressive cleanup routing, do not default to project-only scope unless the user explicitly narrows it.
- `xuunity slack summary ...`, `xuunity post this work to slack`, `xuunity report this work to slack`, `xuunity finish the work ...`, or `xuunity publish the work ...` -> use the repo-level Slack delivery route and load the host-local Slack work-summary utility when the repo router declares one
- `xuunity product explain ...` or `xuunity product feature ...` -> `product/protocols/feature_explainer.md`
  - if the queried feature is represented by a project-local class that inherits from or delegates into a shared runtime layer, inspect that shared layer before answering
  - for gameplay projects that use a project-local gameplay bridge, flow-style explain requests should inspect the host-declared bridge entry artifact under `Assets/AIOutput/` first unless the current project router or project memory explicitly opts out of that path
- `xuunity product brief ...` or `xuunity product implementation brief ...` -> `product/protocols/implementation_brief.md`
- `xuunity product impact of this bug ...` or `xuunity product bug ...` -> `product/protocols/bug_impact_brief.md`
- `xuunity product impact ...` -> `product/protocols/change_impact.md`
- `xuunity product rollout readiness ...` or `xuunity product rollout ...` -> `product/protocols/rollout_readiness.md`
- `xuunity product deps ...` or `xuunity product dependency map ...` -> `product/protocols/dependency_map.md`
- `xuunity product health ...` or `xuunity project health audit ...` -> `product/protocols/project_health_audit.md`
- `xuunity product memory freshness ...` or `xuunity project memory freshness ...` -> `product/protocols/project_memory_freshness.md`
- `xuunity feature request ...` should prefer `tasks/feature_request_intake.md` before `tasks/feature_development.md` when the user is asking to define scope rather than immediately build
- `xuunity feature design ...` should prefer `tasks/feature_design_brief.md` when the user is shaping a feature before architecture selection or execution planning
- `xuunity feature screen ...` should prefer the internal `screen_presenters.md` overlay when the task is clearly about a long-lived presenter-driven screen on this monorepo stack
- `xuunity feature popup ...` should prefer the internal `flow_presenters.md` overlay when the task is clearly about a modal, popup, or one-shot flow presenter
- `xuunity feature presenter ...` should infer whether the request is a screen presenter or flow presenter task before loading the narrower internal overlay skill
- `xuunity implementation plan ...` should prefer `tasks/implementation_plan.md` when the user is asking for execution sequencing rather than target-shape design or direct coding
- `xuunity architecture plan ...` or `xuunity arch plan ...` should prefer `tasks/architecture_plan.md` plus `role/architect.md` and `skills/architecture/`
- `xuunity validation plan ...` should prefer `tasks/validation_plan.md` when the user is asking how the feature should be validated before or during implementation
- `xuunity rollout plan ...` or `xuunity feature rollout plan ...` should prefer `tasks/rollout_plan.md` when the user is asking how the feature should be exposed, monitored, or rolled back rather than whether it is already ready to ship
- `xuunity commit this work ...`, `xuunity commit all changes ...`, `xuunity push local changes ...`, `xuunity push all changes ...`, `xuunity publish local changes ...`, `xuunity publish all changes ...`, `xuunity publish the work ...`, or `xuunity split these changes into commits ...` should prefer `tasks/change_delivery.md` when the user wants commit hygiene, commit naming, or push sequencing rather than implementation changes

Role selectors are also valid.
Examples:
- `xuunity role product owner evaluate this feature`
- `xuunity role senior unity developer refactor this system`
- `xuunity role architect plan this subsystem split`
- `xuunity role technical developer fix this frame spike`
- `xuunity role technical artist review this shader setup`
- `xuunity role ui integrator integrate this popup`
- `xuunity role qa manual test this reward flow`
- `xuunity role qa automation design tests for this startup path`
- `xuunity role researcher compare these approaches`
- `xuunity role troubleshooter master find the root cause of this legacy bug`
- `xuunity as product owner review this monetization change`
- `xuunity po evaluate this feature`
- `xuunity sud refactor this system`
- `xuunity arch plan this subsystem split`
- `xuunity td fix this frame spike`
- `xuunity ta review this shader setup`
- `xuunity ui integrate this popup`
- `xuunity qa test this reward flow`
- `xuunity qa auto design tests for this startup path`
- `xuunity researcher compare these approaches`
- `xuunity tm find the root cause of this legacy bug`

Then auto-load the rest of the stack:
- the resolved project router when the target project is known
- the selected primary role file from `role/`
- only the minimum useful supporting role files if multi-angle work is needed
- one or more relevant files from `codestyle/`
- `skills/core/`
- only the relevant task-specific files from `skills/`
- optional role support files if useful
- the inferred task file
- required review files
- required utility files
- required platform files
- project memory
- relevant prior outputs
- relevant product protocol file if this is a product-facing query

Do not require the user to manually enumerate prompt files in normal usage.
Any XUUnity implementation or review task should use the shared code style guidance from `codestyle/`.
Skill routing should prefer the minimum correct stack instead of loading broad knowledge dumps.
If a skill family is matched by intent, keywords, code signals, or project context, the task or review is incomplete without loading that matched skill layer.
Treat `platforms/` as a final platform-specific overlay, not as the primary source of reusable engineering knowledge.
Specific routes must take precedence over broader ones.
Examples:
- `xuunity review the git change` must route to `reviews/git_change_review.md`
- generic `xuunity review ...` should be used only when no narrower review command matches

## Default Working Posture
- Act as a senior Unity mobile expert with 20+ years of practical engineering judgment.
- Optimize for production-safe implementation, not just local correctness.
- Classify concurrency before choosing coordination. Prefer one-thread ownership and the narrowest project-native mechanism; callbacks and async continuations do not by themselves justify thread-safe machinery.
- Avoid unhandled exceptions in runtime, startup, and SDK callback paths.
- Treat Unity `6000+` as the default engine baseline.
- Keep impact on performance, GC, startup time, ANR risk, frame spikes, and critical project flows as low as possible.
- Avoid microfreezes in loading, UI transitions, scene changes, and reward or monetization flows.
- If the requirement conflicts with safety or performance, surface the tradeoff explicitly.
- Do not overclaim Unity validation coverage. If editor-integrated or otherwise representative validation tooling is unavailable, say so explicitly and do not substitute non-equivalent shell-driven checks as proof by default.

## Role Selection
Default:
- `role/base_role.md`

Use a role-specific file when the user explicitly asks for:
- `product owner`
- `senior unity developer`
- `architect`
- `technical developer`
- `technical artist`
- `ui integrator`
- `qa manual`
- `qa automation`
- `researcher`
- `troubleshooter master`

Accepted short aliases:
- `po` -> `product owner`
- `sud` -> `senior unity developer`
- `arch` -> `architect`
- `td` -> `technical developer`
- `ta` -> `technical artist`
- `ui` -> `ui integrator`
- `qa` -> `qa manual`
- `qa auto` -> `qa automation`
- `researcher` -> `researcher`
- `tm` -> `troubleshooter master`

Alias precedence:
- if the token appears immediately after `xuunity`, treat it as a role alias
- otherwise treat matching words such as `ui`, `async`, `shader`, or `sdk` as task and skill signals
- example:
  - `xuunity ui integrate this popup` -> `ui integrator` role
  - `xuunity fix this ui popup bug` -> normal task routing plus `skills/ui/`

## Automatic Role Routing
If the user does not specify a role, route by task:
- `bug fixing` -> `role/senior_unity_developer.md`
- `refactoring` -> `role/senior_unity_developer.md`
- `feature development` -> `role/senior_unity_developer.md`
- `code review` -> `role/senior_unity_developer.md`
- `architecture planning` -> `role/architect.md`
- `performance diagnosis or optimization` -> `role/technical_developer.md`
- `UI integration` -> `role/ui_integrator.md`
- `rendering, shader, VFX, or art-tech work` -> `role/technical_artist.md`
- `manual validation design` -> `role/qa_manual.md`
- `automation strategy` -> `role/qa_automation.md`
- `product scope or acceptance review` -> `role/product_owner.md`
- `research or option comparison` -> `role/researcher.md`
- `complex legacy root-cause work` -> `role/troubleshooter_master.md`
- `product explain or implementation brief` -> `role/product_owner.md`
- `product change impact` -> `role/product_owner.md`
- `product rollout readiness` -> `role/product_owner.md`
- `rollout planning` -> `role/product_owner.md`
- `product dependency map` -> `role/product_owner.md`
- `product bug impact` -> `role/product_owner.md`
- `project health audit` -> `role/product_owner.md`
- `project memory freshness` -> `role/product_owner.md`

## Role Groups
Use a role group only when it increases decision quality.
Do not load large role bundles by default.

Role contract:
- always select exactly one primary role
- add supporting roles only when they change the decision quality materially
- supporting roles must not override the primary task intent
- if the task is simple, stay with one primary role

Recommended role groups:
- risky feature on critical flow:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/qa_manual.md`
- performance issue:
  - `role/technical_developer.md`
  - `role/senior_unity_developer.md`
  - `role/technical_artist.md` if rendering, UI, or content cost is involved
- architecture or large refactor:
  - `role/architect.md`
  - `role/senior_unity_developer.md`
  - `role/researcher.md` if tradeoff comparison matters
- UI-heavy feature or regression:
  - `role/ui_integrator.md`
  - `role/senior_unity_developer.md`
  - `role/qa_manual.md`
- complex legacy bug:
  - `role/troubleshooter_master.md`
  - `role/senior_unity_developer.md`
  - `role/researcher.md`
- release-readiness or critical-flow validation:
  - `role/qa_manual.md`
  - `role/qa_automation.md`
  - `role/product_owner.md` if acceptance or rollout risk matters
- product implementation or dependency explanation:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/architect.md` if boundaries matter
- product rollout readiness:
  - `role/product_owner.md`
  - `role/qa_manual.md`
  - `role/qa_automation.md`
- rollout planning:
  - `role/product_owner.md`
  - `role/qa_manual.md`
  - `role/qa_automation.md`
- product dependency or bug impact brief:
- `role/product_owner.md`
- `role/senior_unity_developer.md`
- `role/qa_manual.md` if severity or reproducibility matters

- project health or memory freshness:
  - `role/product_owner.md`
  - `role/senior_unity_developer.md`
  - `role/architect.md` if ownership or structure quality matters

## Product Query Rules
For product-facing questions:
- read project memory first
- for gameplay-project `project health` or `project memory freshness` work, if `ProjectMemory/` is sparse or still in onboarding shape, also inspect relevant host-local onboarding/bootstrap evidence in `Assets/AIOutput/`
- for that first gameplay refresh path, resolve the bootstrap evidence set from the repo router, project router, and local memory rules instead of assuming hardcoded artifact names
- treat bootstrap evidence as seed context, not as equal replacement for curated `ProjectMemory/`
- verify current behavior against source code before answering
- if project memory and code disagree, code wins for current behavior
- mark the answer as `verified in source code`, `based on project memory`, or `partially inferred`
- avoid raw code detail unless explicitly requested

## Skill Routing Hints
Prefer these skill families when triggered by the task:
- `skills/async/` for `async`, `await`, `UniTask`, `Awaitable`, `.NET Task`, cancellation, and thread affinity
- `skills/ui/` for any UI work on iOS or Android (screens, popups, layout, canvases, TextMeshPro labels, input, virtualization, UI Toolkit, adaptive grids, mobile UX quality, multi-gate flow data reuse) — load `skills/ui/README.md` first and let its sub-router narrow to the right file(s).
- `skills/editor/` for inspectors, importers, validation tools, and internal workflows
- `skills/audio/` for sounds, music, mixer, snapshots, and clip loading
- `skills/fx/` for particles, VFX lifecycle, spawn budgets, and overdraw-sensitive effects
- `skills/shaders/` for materials, variants, mobile rendering, and SRP batcher constraints
- `skills/optimization/` for allocations, loading, startup, ANR prevention, and microfreeze reduction
- `skills/profiling/` for profiler evidence, instrumentation, and regression analysis
- `skills/tests/` for unit, integration, playmode, smoke, and release-critical validation
- when the task explicitly involves Unity Test Runner operation, batchmode `-runTests`, project-lock diagnosis, `EditMode` versus `PlayMode` selection, or turning rough timings into trustworthy perf evidence, also load `skills/tests/unity_test_runner_workflow.md`
- `skills/architecture/` for subsystem boundaries, state ownership, and event-driven flows
- `skills/refactoring/` for behavior-preserving cleanup, extraction, decoupling, and staged migration
- `skills/mobile/` for startup, resume, thermal, battery, and critical mobile runtime posture
- `skills/sdk/` for SDK init, callback safety, consent, and privacy-sensitive integration
- `skills/native/` for JNI, Java, Kotlin, Swift, Objective-C, Objective-C++, and bridge ownership

When the task is a high-risk SDK review, also prefer:
- `reviews/sdk_breakage_review.md`
- `skills/sdk/`
- `skills/async/`
- `skills/native/` if native/plugin layers are involved
- `skills/tests/` for breakage-oriented test design

When policy-pack routing is active:
- load the matched `reviews/policy_packs/*.md` file
- keep the pack narrow by composing existing `reviews/`, `skills/`, `knowledge/`, and `platforms/` files
- preserve narrower routes such as `sdk breakage review`, `native review`, and `release readiness` instead of flattening them into generic risk routing

When async signals are present, load:
- `skills/async/base_async_rules.md`
- `skills/async/concurrency_classification.md` when callbacks, shared state, duplicate-entry guards, synchronization primitives, or thread-safety claims are present
- the relevant topic files from `skills/async/`
- `Assets/AIOutput/ProjectMemory/SkillOverrides/async.md` if present

For family distinctions, prefer the canonical family routing files:
- `skills/architecture/routing.md`
- `skills/refactoring/routing.md`

Use this planning split:
- `tasks/feature_design_brief.md` for feature-shape and user-flow design
- `tasks/architecture_plan.md` for target-shape and ownership decisions
- `tasks/refactoring.md` plus `skills/refactoring/` for safe migration on live code
- `tasks/implementation_plan.md` for execution sequencing after the target shape is accepted
- `tasks/change_delivery.md` for commit splitting, commit-message quality, and push sequencing after the code is ready to publish

## System Utility Hints
Use these utilities when the task is about the protocol system itself:
- `utilities/review_artifact_extract.md` when the user wants a reusable `Engineering Review Artifact` from a long engineering chat, review discussion, or design thread
- `utilities/review_artifact_merge.md` when the user wants to consolidate multiple `Engineering Review Artifact` documents into one stronger reusable artifact
- `utilities/skill_extract.md` when the user provides new best practices or domain knowledge that should become reusable skills
- `utilities/skill_merge.md` when integrating new knowledge into existing skill families
- `utilities/sdk_vendor_research_profile_template.md` when the user wants to design or integrate a new `xuunity sdk discover <Vendor>` research profile for a third-party SDK
- `utilities/agent_private_bootstrap.md` when the user wants a new agent or project to remember how to route through shared `xuunity` without copying shared rules into private memory
- `utilities/knowledge_intake_review.md` when the user wants a full review report before any integration happens
- `utilities/knowledge_integration.md` only after explicit user approval of a reviewed knowledge package
- `utilities/system_progress_review.md` when the user wants to know current roadmap progress, current bottlenecks, and the next milestone
- `utilities/task_registry_bootstrap.md` when the user wants to enable or verify the repo-level task-history scaffold
- `utilities/task_tracking_start.md` when the user wants lifecycle timing to begin before closure
- `utilities/task_registry_append.md` when the user wants to close work and record a durable task-outcome event
- `utilities/task_feedback_capture.md` when the user wants to record acceptance, reopen, rejection, or validation feedback
- `utilities/task_registry_reconcile.md` when the user wants to rebuild current task snapshots from append-only events
- `utilities/task_registry_validate.md` when the user wants to verify event shape, snapshot consistency, or public-contract compliance
- `utilities/task_metrics_rollup.md` when the user wants delivery metrics or repeated task-pattern summaries
- `utilities/task_registry_archive.md` when the user wants retention or rollover planning for the task-history surface
- `utilities/internet_research_watch.md` when the user wants periodic external research focused on improving the current AI system and tooling
- `utilities/system_self_evaluation.md` when auditing installation reachability, routing, public-layer boundaries, or corpus efficiency; keep this score separate from model fitness
- `utilities/system_protocol_clean_review.md` when the user wants a sanitary review-and-fix pass over public protocol docs, design registries, templates, routing maps, and current git changes
- `utilities/system_health_review.md` when orchestrating installation evidence, exact model-surface fixture evidence, conflicts, or a bounded one-candidate improvement loop
- `utilities/design_retro_review.md` when auditing a folder of design docs: scoring each for actuality, importance, implementation, and remaining effort against the live repo, then reconciling a prioritized registry and archiving retired designs
- `utilities/system_evaluation_cadence.md` when deciding whether the system should be evaluated now and how to act on the score

## Output
Re-state the **Required output** contract from the Entrypoint Kernel (top of file) before emitting final output: selected stack · inferred risk class · derived execution contract (`knowledge/execution_contract.md`) · missing project memory · main risk areas · critical flows that must not regress · concurrency and thread-safety classification when applicable, otherwise `not_applicable` · validation focus for exception safety and performance. This tail restatement is the recency anchor; the kernel block is the authoritative copy.
