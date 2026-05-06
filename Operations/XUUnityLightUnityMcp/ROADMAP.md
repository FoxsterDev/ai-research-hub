# XUUnity Light Unity MCP Roadmap

Date: `2026-05-05`
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

## Current Baseline

Already implemented:

- bridge enable/disable lifecycle
- status and capability probing
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

This is enough for:

- real compile gating
- basic Unity-aware validation
- controlled screenshot capture
- early automation experiments

This is not yet enough for:

- device profiling
- runtime bottleneck analysis
- rich scripted end-to-end gameplay scenarios
- autonomous regression investigation
- agent-safe mutation planning at scale

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
- next gap is richer assertions, result browsing, and artifact surfacing rather than first-time scenario bring-up

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

1. scenario runner
2. device deploy and launch
3. profiler capture and export
4. runtime screenshot and logs
5. deeper scene and asset inspection
6. artifact manifests and comparison helpers

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

`richer scenario assertions, result utilities, and broader cross-client proof`

That means:

- harden current operations further
- expand scenario result evidence and artifact surfacing
- validate the same public smoke routes across more clients and consumers
- keep device profiling for the next wave, not this one

Reason:
- the base scenario control plane already exists
- the next highest leverage is trust, evidence quality, and reuse across consumers
