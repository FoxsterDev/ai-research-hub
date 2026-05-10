# XUUnity Light Unity MCP Roadmap

Date: `2026-05-10`
Status: `active public roadmap`

## North Star

Build a small but serious Unity MCP service that can support an autonomous
engineering loop:

1. inspect project state
2. run compile and test validation
3. drive play mode and scripted scenarios
4. capture screenshots, logs, and profiler evidence
5. correlate findings back to code and assets
6. produce actionable diagnoses and candidate fixes

The target is not just "Unity commands through MCP".
The target is a trustworthy automation surface for coding agents, CUA-style
operators, and future project-specific assistants.

## Product Principles

- editor-first and removable by default
- zero player-build footprint unless a project explicitly opts into runtime probes
- capability-gated behavior instead of version guessing
- evidence-first outputs instead of opaque success flags
- narrow, composable operations instead of one giant universal tool
- support for more than one MCP client and more than one agent role

## Current Architecture Milestone

The architecture-hardening milestone that was previously only planned is now
materially implemented in the public baseline.

Implemented:

- explicit per-project `BridgeRegistry`
- explicit per-project `ProjectContext`
- per-project mutation locking
- formal discovery and reconciliation
- exact process ownership matching by parsed `-projectPath`
- health and ANR classification scaffold
- structured grouped state:
  - `transport_state`
  - `state_groups`
- explicit context-cache pruning for stale offline projects
- public proof runners for:
  - multi-project acceptance
  - divergence and reconciliation cases
  - health-policy classification

This means the current same-host editor lane is no longer only a transport
experiment. It now has an explicit routing model, recovery model, and proof
model.

What still remains after this milestone is less about basic multi-project
survival and more about:

- richer read surfaces
- stronger artifact and timing evidence
- broader supported-client proof
- deeper scenario result browsing and diagnosis flows

## Current Baseline

Already implemented:

- bridge enable/disable lifecycle
- status and capability probing
- compact status summaries with bridge stabilization fields
- additive request-scoped `structured_timing` and `artifact_manifest` on
  successful same-host editor responses and `request-final-status`
- console tail
- scene snapshot
- edit-mode tests
- compile validation without active platform switch
- play mode control
- Game View screenshot and resolution control
- first scenario automation layer:
  - `unity.scenario.validate`
  - `unity.scenario.run`
  - `unity.scenario.result`
- public reusable smoke runners for compact and JSON-heavy validation routes
- host-side editor session restore for host-opened validation runs
- lifecycle-reset finalization recovery by `request_id`
- `request-final-status` for operator follow-up after transport churn
- host-side persisted scenario result browsing:
  - `request-scenario-results-list`
  - `request-scenario-result-latest`
  - `unity_scenario_results_list`
  - `unity_scenario_result_latest`
- first cancellation slice for the same-host editor lane:
  - `request-cancel`
  - `request_cancelled`
  - `request_cancel_requested`
- stale request inspection and cleanup for the same-host editor lane:
  - `stale_request_artifacts`
  - `request-stale-cleanup`
- operator-facing separation of:
  - `transport_outcome`
  - `operation_outcome`
  - `recommended_next_action`
- per-project discovery and reconciliation reporting
- per-project health and ANR classification reporting
- structured grouped transport and lifecycle state
- compile-first public post-change validation ordering

This is enough for:

- real compile gating
- basic Unity-aware validation
- controlled screenshot capture
- early automation experiments
- repeatable same-host multi-project routing and recovery

This is not yet enough for:

- device profiling
- runtime bottleneck analysis
- rich scripted end-to-end gameplay scenarios
- autonomous regression investigation
- agent-safe mutation planning at scale

## Targeted Next Threshold

Near-term target:

- raise the current service from `78/100` to `85+/100`
- do this first in the intended same-host editor validation scope
- avoid widening scope until the current lane is measurably hardened

Meaning of `85+` here:

- repeatable healthy startup and validation across supported clients
- clear recovery after bridge churn and lifecycle resets
- stable compact operator status and finalization semantics
- richer evidence outputs per operation
- broader proof across more than one Unity consumer and version

This is not the same as "full world-class device automation platform".
It is the threshold for calling the current lane operationally strong.

Near-term emphasis after the architecture milestone:

- keep hardening the current lane with richer evidence outputs
- broaden proof across more supported clients and more real consumer projects
- improve read surfaces so diagnosis needs less shell fallback

## Current Priority Milestone

Current recommendation:

- close the remaining Phase 1 reliability hardening before broadening proof

Most valuable next milestone:

- lifecycle and stale-request reliability closeout for the current same-host
  editor lane

Why this is next:

- artifact manifests, structured timings, and persisted scenario result
  browsing are now materially in place
- the biggest remaining trust gap is now lifecycle churn proof and the limits of
  host-side-only cancellation semantics
- broader cross-client proof will be more meaningful after that reliability
  floor is tighter

Focus:

- broader lifecycle fault-injection proof
- request cancellation semantics
- keep the new host prerequisite report stable while closing the remaining
  lifecycle gaps

## Phased Plan To Reach 85+

### Phase 1: Core Reliability Hardening

Goal:
- remove the most expensive operational ambiguity from the current lane

Focus:
- stdio server hardening
- cancellation semantics
- stale request cleanup
- stronger lifecycle fault-injection proof
- explicit host prerequisite reporting

Current progress:

- additive host prerequisite reporting is now implemented on compact
  discovery/status/final-status surfaces through `host_prerequisites`
- first host-side cancellation slice is now implemented through best-effort
  `request-cancel` semantics for queued `file_ipc` requests plus structured
  in-flight cancellation intent reporting
- stale-request cleanup is now implemented through explicit stale artifact
  inspection plus `request-stale-cleanup`
- remaining work is now broader lifecycle fault-injection proof, and possibly
  deeper Unity-side cancellation behavior if this lane later needs more than
  host-side cancellation intent

Exit criteria:
- lifecycle churn is tested, not only reasoned about
- stale requests do not accumulate silently
- tool failures land in a stable structured taxonomy
- the operator can distinguish setup failure, transport loss, and Unity-side failure quickly

Expected score impact:
- `+3 to +4`

### Phase 2: Evidence And Observability Hardening

Goal:
- make every important operation easier to trust and debug

Focus:
- artifact manifest per operation
- structured timings per operation
- scenario result listing and last-result fetch
- clearer artifact path surfacing
- compact summary enrichment where it reduces operator guesswork

Current progress:

- additive request-scoped `artifact_manifest` is implemented in the current
  same-host editor lane
- additive request-scoped `structured_timing` is implemented in the current
  same-host editor lane
- host-side persisted scenario result browsing is implemented through:
  - `request-scenario-results-list`
  - `request-scenario-result-latest`
  - `unity_scenario_results_list`
  - `unity_scenario_result_latest`
- remaining value in this phase is summary polish, broader proof, and
  surfacing the evidence consistently across more operator flows

Exit criteria:
- a failed or timed-out run leaves enough structured evidence for a new chat to continue without journal archaeology
- scenario outputs are discoverable through first-class utilities
- timings and artifacts are part of the default debugging flow

Expected score impact:
- `+2 to +3`

### Phase 3: Proof Breadth Across Clients And Consumers

Goal:
- prove that the lane is stable outside one narrow local success case

Focus:
- repeatable validation in Codex, Claude Code, and Cursor
- proof on more than one Unity consumer project
- proof on a broader Unity version slice where feasible
- remove or sharply document client-specific quirks

Exit criteria:
- the same baseline flow works without ad hoc host repairs across supported clients
- the same core contract works on more than one real consumer
- known incompatibilities are explicit and bounded

Expected score impact:
- `+2 to +3`

### Phase 4: Narrow Surface Completion For The Current Lane

Goal:
- finish the missing pieces that block calling the lane mature within its current scope

Focus:
- scenario assertions and result browsing
- better read-surface helpers for diagnosis
- optional reduction of reflection dependency where practical
- tighter operational docs and decision trees

Exit criteria:
- common validation and regression tasks stay inside the MCP lane instead of falling back to shell scraping
- result interpretation is cheaper for both humans and agents
- the current lane is defensibly `85+`

Expected score impact:
- `+1 to +2`

## Roadmap Layers

### Wave 1: Harden The Core

Goal:
- make the current service operationally trustworthy

Deliverables:
- stronger stdio server hardening
- richer tool error taxonomy
- request cancellation and stale request cleanup
- artifact manifest per operation
- structured timing for every operation
- explicit host prerequisites report
- repeatable client validation in Codex, Claude Code, and Cursor

Done when:
- the same project can be onboarded and used across multiple clients without ad hoc host fixes
- every operation returns stable structured evidence

Current progress:
- lifecycle-reset ambiguity is materially reduced
- compact operator recovery by `request_id` is now in place
- compile-first validation order is now part of the reusable runner baseline
- request-scoped artifact manifests and structured timings are now in place
- explicit host prerequisite reporting is now in place on compact host-side
  discovery and recovery surfaces
- stale request inspection and cleanup are now in place for current same-host
  request artifacts
- remaining work in this wave is broader fault-injection proof and
  cancellation-hygiene polish
- this wave maps directly to Phase 1 and the beginning of Phase 2 in the `85+` plan

### Wave 2: Better Read Surface

Goal:
- make project inspection useful enough for agent diagnosis

Deliverables:
- asset read/list/search operations
- prefab snapshot operations
- hierarchy subtree snapshot
- selected object/component snapshot
- package and define read operations
- scene list and open-scene snapshot

Done when:
- an agent can connect a runtime symptom back to concrete assets, packages, and scene objects without shell scraping

### Wave 3: Scenario Automation

Goal:
- let agents drive deterministic Unity sessions instead of one-shot commands

Deliverables:
- scenario definition format for play-mode automation
- steps such as:
  - enter play mode
  - wait for condition
  - invoke menu item
  - invoke project-defined hook
  - capture screenshot
  - capture console slice
  - assert scene/object state
- persisted scenario result bundle
- MCP operations:
  - `unity.scenario.validate`
  - `unity.scenario.run`
  - `unity.scenario.result`

Current state:
- initial baseline is implemented
- current step surface is intentionally small
- persisted result browsing and artifact surfacing are now in place
- next gap is richer assertions and sharper failure interpretation rather than first-time scenario bring-up
- this wave contributes to Phase 2 and Phase 4 of the `85+` plan

Done when:
- a scripted play-mode regression scenario can be authored once and replayed by any supported agent

### Wave 4: Runtime Probe Layer

Goal:
- support deep analysis without bloating the base package

Deliverables:
- optional dev-only runtime companion package
- explicit opt-in runtime probe mode
- frame timing capture
- memory sample capture
- marker and subsystem counters
- scene/runtime event breadcrumbs

Guardrails:
- runtime probe layer must be separate from the editor-only base package
- uninstall path must remain simple
- no silent player-build inclusion

Done when:
- a project can opt into runtime diagnostics for development builds without contaminating normal builds

### Wave 5: Device Automation And Profiling

Goal:
- support the real mobile troubleshooting loop

Deliverables:
- device session abstraction
- attach/run/stop for Android and iOS dev builds
- screenshot capture from device
- runtime log collection from device
- profiler capture pull/export
- thermal and frame pacing evidence where available
- artifact mapping back to build config, git revision, and scenario id

Likely operation families:
- `unity.device.list`
- `unity.device.deploy`
- `unity.device.launch`
- `unity.device.logs.tail`
- `unity.device.screenshot`
- `unity.device.profiler.capture`
- `unity.device.session.stop`

Done when:
- an agent can run a dev build on a device, collect evidence, and reason about a bottleneck with no manual profiler clicking

### Wave 6: Evidence Analysis

Goal:
- turn captures into diagnoses instead of raw blobs

Deliverables:
- normalized artifact manifests
- capture-to-code correlation helpers
- profiler summary extraction
- spike detection and bottleneck ranking
- scene/object/code suspect set generation
- comparison mode:
  - before vs after
  - device A vs device B
  - branch vs branch

Done when:
- the service can surface a narrow suspect set for performance regressions instead of only dumping screenshots and logs

### Wave 7: Autonomous CUA Support

Goal:
- make the MCP usable by an automation specialist agent, not only by a coding agent

Deliverables:
- long-running session model
- scenario plans with resumable checkpoints
- artifact bundle IDs
- operation preconditions and side-effect declarations
- safe recovery after domain reload and editor restart
- explicit "human handoff required" states
- policy bands:
  - read-only
  - validation
  - guarded mutation
  - invasive diagnostics

Done when:
- a CUA-style agent can perform a multi-step Unity investigation with bounded risk and reliable resumption

## Key Capability Families To Add

Highest-value missing capabilities:

1. deeper scene and asset inspection
2. broader lifecycle fault-injection proof and deeper cancellation behavior
3. broader supported-client proof
4. device deploy and launch
5. profiler capture and export
6. runtime screenshot and logs

Second-wave mutation capabilities:

1. guarded prefab or asset patch application
2. controlled menu-item execution
3. project-defined hook execution
4. temporary instrumentation toggle

## Architecture Direction

The service should grow as plugins, not as one monolith.

Recommended layers:

1. base MCP server
2. editor bridge
3. optional runtime diagnostics companion
4. host-side device adapters
5. project-defined scenario adapters
6. analysis adapters

## Practical Sequencing

Do next:

1. close the remaining Phase 1 reliability hardening
2. broaden supported-client and multi-consumer proof in Phase 3
3. keep tightening Phase 2 evidence surfacing where operator friction remains
4. close Phase 4 only after the evidence says the lane is already near `85`

Do not do next:

- do not prioritize device automation before the current lane is hardened
- do not widen runtime-scope ambition to hide unresolved core reliability gaps

This keeps:
- the base install small
- project removal easy
- capability rollout incremental

## What "Full Support" Means

The ambitious end-state is:

- connect to Unity project
- validate capabilities
- compile for multiple targets
- run edit and play mode scenarios
- produce editor and runtime screenshots
- deploy and launch on device
- capture profiler evidence
- detect bottlenecks
- correlate bottlenecks with code, assets, and scene structure
- hand back ranked findings and next actions

That is the right target for "full automation support through MCP".

## Suggested Build Order

1. harden current core
2. add scenario runner
3. add deeper read surface
4. add runtime companion for development builds
5. add device session and profiler pipeline
6. add evidence analysis and comparison
7. add resumable autonomous workflows

## Non-Goals For The Base Package

- broad runtime support by default
- hidden downloads
- mandatory cloud relay
- broad reflection-based mutation without capability checks
- silent editor or project setting rewrites
- opaque "magic execute code" surfaces as the main extension model

## Immediate Next Milestone

The next milestone should be:

`lifecycle-fault proof, scenario result utilities, and broader cross-client proof`

That means:

- harden current operations further under induced transport churn
- expand scenario result evidence and artifact surfacing
- validate the same public smoke routes across more clients and consumers
- keep device profiling for the next wave, not this one

Reason:
- the base scenario control plane already exists
- the next highest leverage is trust, evidence quality, and reuse across consumers
