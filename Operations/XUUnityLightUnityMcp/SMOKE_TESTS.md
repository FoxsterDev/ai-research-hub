# XUUnity Light Unity MCP Smoke Tests

This file defines the public reusable smoke-test contract for the lightweight
Unity MCP lane.

Keep project-specific wrappers, project roots, build-config assets, and local
hook names out of this file. Those belong in host-local `AIOutput/Operations/`
or project-local guidance.

## Goal

Provide a small generic baseline that proves:

- the bridge can start and report healthy state
- basic editor-integrated operations work through MCP
- ordered scenario execution works
- play mode lifecycle control works
- refresh semantics settle instead of returning only request-time transport

## Generic Smoke Layers

### 1. Bridge Readiness Smoke

Run:

- `ensure-ready`
- `request-status`
- `request-health-probe`

Pass criteria:

- healthy bridge heartbeat
- `unity.status` reachable
- `unity.health.probe` reports supported operations without infrastructure failure
- compact status output should expose whether the bridge is already stabilized enough for retry

### 2. Compile Gate

Before heavier scenario work on changed scripts, prefer a fast compile gate.

Preferred routes:

- `request-build-config-compile-matrix` when a project defines the authoritative build-profile matrix
- otherwise the narrowest representative `unity.compile.player_scripts` route

Pass criteria:

- no infrastructure failure
- all required target/profile entries pass for the project contract
- when Unity-side settle evidence is available, compile payloads should report
  `completion_basis: unity_compile_settle_watcher`

### 3. Interactive Acceptance Scenario

Minimum generic scenario steps:

- `status`
- `health_probe`
- `project_refresh`
- `playmode_set enter`
- `wait_for_playmode_state playing`
- `assert_playmode_state playing`
- `playmode_set exit`
- `wait_for_playmode_state edit`
- `assert_playmode_state edit`

Optional project-local additions:

- `game_view_configure`
- `game_view_screenshot`
- `project_defined_hook`
- `console_tail`

Pass criteria:

- scenario reaches terminal `passed`
- refresh step settles successfully
- play mode transitions reach explicit target states

### 4. Refresh Contract Smoke

Use a short scenario or direct route to verify refresh semantics.

Pass criteria:

- top-level refresh returns:
  - `refresh_completed` or `refresh_and_resolve_completed`
  - `requested_outcome`
  - `settled_at_utc`
  - `completion_basis`
- if scenario-driven refresh is used, nested refresh payload should expose the
  same settled contract class rather than only raw `*_requested` transport timing

### 5. PlayMode Result Parity Smoke

Use a representative direct `unity.tests.run_playmode` request and a scenario
`tests_run_playmode` step that target the same PlayMode test.

Pass criteria:

- both paths finish successfully
- both payloads expose `playmode_state_after_settle`
- both payloads report the same final value
- for the common single-test happy path, the final value should normally be
  `edit`

### 6. Lifecycle Reclassification Fault Smoke

Use a temporary editor script change that forces a real compile or bridge
rebootstrap while a top-level refresh request is in flight.

Pass criteria:

- the refresh request still resolves successfully
- lifecycle metadata reports a `bridge_identity_transition`
- the transition includes a host-written `request_reclassified` journal event
- a cleanup refresh returns the editor to healthy `edit` idle state

### 7. Request-Abandoned Fault Smoke

Use an in-flight async request plus an injected editor reload to prove Unity-side
`request_abandoned` journaling.

Pass criteria:

- the async request reaches `request_started`
- a forced reload occurs before completion
- Unity writes `request_abandoned` journal evidence for the same `request_id`
- cleanup restores healthy `edit` idle state

### 8. Transport Matrix Smoke

Switch the bridge transport across the supported transport set and rerun the
compact post-change validation route on each transport.

Pass criteria:

- each configured transport reaches healthy status
- status reports the requested and active transport coherently
- the compact post-change validation route passes on each transport
- cleanup restores the original bridge config

### 9. Lifecycle Stress Smoke

Run a short resilience route while another desktop app is frontmost, then verify
the bridge still handles refresh, scenario, and playmode lifecycle operations.

Pass criteria:

- status, refresh, contract scenario, and playmode enter/exit all succeed
- repeated `ensure-ready` works against the same editor session
- final status returns to healthy `edit`

## Public Template Assets

Generic example scenario JSON templates live under:

- `templates/scenarios/interactive_acceptance_smoke.json`
- `templates/scenarios/refresh_contract_smoke.json`
- `templates/scenarios/compile_contract_smoke.json`
- `templates/smoke/run_playmode_settled_state_regression.sh`
- `templates/smoke/run_request_abandoned_fault_suite.sh`
- `templates/smoke/run_transport_matrix_suite.sh`
- `templates/smoke/run_lifecycle_stress_suite.sh`
- `templates/smoke/run_lifecycle_fault_injection_suite.sh`
- `templates/smoke/run_post_change_validation.sh`
- `templates/smoke/run_smoke_suite.sh`

Projects may copy and extend them in host-local operational layers.

## Public Runner Contract

The public shell runners are baseline templates, not project routers.

Required caller-supplied inputs:

- `--project-root`
- `--acceptance-scenario`
- `--contract-scenario`

Current generic compile modes:

- `build-config-matrix`
- `none`

Optional post-change parity inputs:

- `--playmode-regression-assembly-name`
- `--playmode-regression-test-name`

Lifecycle contract:

- if the host opens Unity for the run, the runner should restore the original
  closed state on exit
- project-specific wrappers may opt out only when they intentionally want to
  preserve the interactive editor session for follow-up inspection
- after lifecycle churn or wrapper-side response loss, the preferred recovery
  path is `request-final-status --request-id <id>` before blind retry
- if the wrapper stalled before surfacing a usable `request_id`, the preferred
  recovery path is:
  - `request-status-summary`
  - then `request-latest-status --operation <operation>`
- when a compact summary surface exists, the smoke route should use it before
  raw result polling or large log inspection
- a lifecycle-reset smoke result is not accepted unless the wrapper exposes one
  obvious follow-up command using that exact `request_id`

Token-discipline contract:

- prefer `request-status-summary` over repeated raw status checks
- prefer `request-latest-status --operation ...` over manual request-journal
  digging when the request id is not already known
- prefer persisted scenario-result summaries over tight `unity.scenario.result`
  polling loops
- prefer compact batch failure summaries over direct `prepare.log` or
  `build.log` tailing
- treat a smoke workflow as failed if it repeatedly dumps raw scenario results
  or raw build logs before exhausting the compact summary surfaces
