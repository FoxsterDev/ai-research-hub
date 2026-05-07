# XUUnity Light Unity MCP Progress Status

Date: `2026-05-07`
Status: `public progress report`

## Summary

The lightweight Unity MCP is no longer just a design scaffold.

It is now a working early-stage service with:

- a minimal stdio MCP server
- an editor-only Unity bridge
- a validated core operation set

Current operator-grade assessment:

- `78/100` overall stability against strong industry expectations
- `82/100` for same-host editor validation and control
- not yet strong enough to claim `85+` as a broadly hardened automation platform

## Current Functional State

Implemented:

- install/init workflow
- enable/disable workflow
- status and capability probing
- compact status summary with retry/stabilization clues
- compile validation
- edit-mode test execution
- scene snapshot
- console tail
- play mode control
- Game View screenshot and resolution control
- scenario validation
- asynchronous scenario execution
- persisted scenario results
- public reusable smoke runners
- host-side editor-state restore for host-opened validation runs
- request-finalization recovery after lifecycle reset
- compile-first reusable post-change validation ordering

## Current Maturity

For narrow Unity-aware validation:

- usable

For ambitious autonomous Unity automation:

- still early

## Scorecard

### Stability Score

- overall: `78/100`
- same-host editor validation lane: `82/100`
- broad production automation platform: `68-72/100`

### Aspect Breakdown

1. Operational reliability: `84/100`
   Evidence:
   - healthy live bridge state
   - compact status reports `stabilized=true`
   - safe retry signal is surfaced explicitly
   - full post-change validation passed in current `prodmode`

2. Failure handling and recovery: `80/100`
   Evidence:
   - lifecycle-reset recovery by `request_id`
   - request journal as operator evidence
   - explicit split between transport outcome and Unity operation outcome
   - `request-final-status` for post-churn reconciliation

3. Observability and diagnosability: `79/100`
   Evidence:
   - `bridge_state.json`
   - `capabilities_report.json`
   - compact status summary
   - persisted scenario results
   - health-probe contract

4. Validation discipline: `86/100`
   Evidence:
   - compile-first validation order
   - capability gating
   - native settle watchers for refresh, compile, and playmode
   - acceptance and contract smoke coverage

5. Deployment and reproducibility: `81/100`
   Evidence:
   - `devmode` and `prodmode`
   - git-pinned package source
   - package lock invalidation for honest re-resolve
   - editor-only removable base package

6. Compatibility and version resilience: `70/100`
   Evidence:
   - capability probe and adapter model are correct
   - broad Unity version proof and multi-client proof are still limited

7. Blast-radius control and package safety: `85/100`
   Evidence:
   - disabled by default
   - no `ProjectSettings` mutation
   - no player-build footprint by default
   - no broad define mutation

8. World-class platform maturity: `64/100`
   Evidence:
   - no device layer yet
   - no runtime evidence lane yet
   - no profiler export/analysis lane yet
   - no broad resumable long-running automation proof yet

## What Has Been Proven

The current service has already proven that it can:

- connect to a real Unity project
- expose bridge health and capability state
- compile for explicit targets without switching active platform
- run EditMode tests
- capture Game View screenshots
- control play mode transitions
- persist scenario result bundles
- run second-wave scenario steps for compile, tests, Game View configure, and project-defined hooks
- restore host-opened Unity sessions back to closed after validation
- resolve lifecycle-reset ambiguity from the request journal by request id

Recent live proof in `prodmode`:

- `request-health-probe` passed with healthy status and supported operation set
- compile matrix passed `6/6`
- acceptance scenario passed `10/10`
- contract scenario passed
- full reusable post-change suite passed

## What Is Not Yet Proven

- broad multi-client production use
- device automation
- profiler export
- runtime bottleneck analysis
- rich scenario replay framework
- resumable long-running automation

## Current Risk Areas

- stdio layer still needs hardening
- Game View support still depends on reflection
- deeper project inspection surface is still thin
- no runtime evidence pipeline yet
- multi-client and multi-version proof is still narrow
- lifecycle fault-injection proof is not yet broad enough for a stronger score claim

## Current Recommendation

Treat the service as:

- ready for controlled Unity-aware validation
- not yet ready as a full autonomous Unity automation platform

Target recommendation for the next milestone:

- move from "good narrow validation lane" to "operationally hardened same-host MCP lane"
- do not spend the next cycle on device/runtime scope until the service reaches a defensible `85+` in its current scope

## Continuation Note

The next chat should treat this report as baseline only.

It should also read:

- `2026-05-05_xuunity_protocol_integration_status.md`
- `../CONTINUATION.md`

## Best Next Milestone

Next:

- close the `78 -> 85+` gap inside the current scope before expanding surface area
- prioritize:
  - fault-injection and churn recovery proof
  - cancellation and stale-request hygiene
  - artifact manifests and structured timings
  - scenario result browsing and artifact surfacing
  - repeatable validation in Codex, Claude Code, and Cursor
  - proof on a broader Unity version and consumer-project set

This is now the most valuable bridge between the current validated core and the
future device-and-profiler automation goal.
