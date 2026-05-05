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

### 2. Interactive Acceptance Scenario

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

### 3. Refresh Contract Smoke

Use a short scenario or direct route to verify refresh semantics.

Pass criteria:

- top-level refresh returns:
  - `refresh_completed` or `refresh_and_resolve_completed`
  - `requested_outcome`
  - `settled_at_utc`
  - `completion_basis`
- if scenario-driven refresh is used, nested refresh payload should expose the
  same settled contract class rather than only raw `*_requested` transport timing

### 4. Compile Smoke

Prefer the narrowest representative compile route allowed by project rules:

- if a build-config asset exists and defines the project matrix, use
  `request-build-config-compile-matrix`
- otherwise use one or more representative `unity.compile.player_scripts` runs

Pass criteria:

- no infrastructure failure
- all required target/profile entries pass for the project contract
- when Unity-side settle evidence is available, compile payloads should report
  `completion_basis: unity_compile_settle_watcher`
- if scenario-driven compile is used, nested `compile_player_scripts` payloads
  should expose the same compile-settle contract rather than only synchronous
  API-return timing

## Public Template Assets

Generic example scenario JSON templates live under:

- `templates/scenarios/interactive_acceptance_smoke.json`
- `templates/scenarios/refresh_contract_smoke.json`
- `templates/scenarios/compile_contract_smoke.json`

Projects may copy and extend them in host-local operational layers.
