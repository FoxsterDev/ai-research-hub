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

### 1a. Closeout Truth Smoke

Run a host-opened validation session and then `restore-editor-state`.

Pass criteria:

- a host-opened editor closes with verified process exit, not only a quit
  acknowledgement
- the result exposes `closeout_classification`
- `closeout_classification=quit_ack_without_exit` is treated as a failure signal
  for the smoke, not as a passing closeout
- when closeout proof is incomplete, the wrapper surfaces one obvious follow-up
  command through `recommended_recovery_command`

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

### 6. PlayMode Lifecycle Retry Smoke

Use a representative direct `unity.tests.run_playmode` request while the editor
is already in Play Mode so the host must:

- observe `playmode_state_invalid`
- issue `unity.playmode.set exit`
- retry the PlayMode test request

Pass criteria:

- the terminal operator verdict exposes `result_trust_class`
- accepted terminal trust classes are:
  - `unity_completed_confirmed`
  - `unity_completed_after_lifecycle_reset`
  - `wrapper_failed_unity_unproven`
- a terminal `request_lifecycle_reset` without `result_trust_class` is a smoke
  failure
- a reclassified PlayMode request must not leave stale test ownership behind:
  a follow-up PlayMode request may fail for other reasons, but it must not fail
  with `tests_busy`
- final status returns to healthy `edit`

### 7. Lifecycle Reclassification Fault Smoke

Use a temporary editor script change that forces a real compile or bridge
rebootstrap while a top-level refresh request is in flight.

Pass criteria:

- the refresh request still resolves successfully
- lifecycle metadata reports a `bridge_identity_transition`
- the transition includes a host-written `request_reclassified` journal event
- a cleanup refresh returns the editor to healthy `edit` idle state

### 8. Request-Abandoned Fault Smoke

Use an in-flight async request plus an injected editor reload to prove Unity-side
`request_abandoned` journaling.

Pass criteria:

- the async request reaches `request_started`
- a forced reload occurs before completion
- Unity writes `request_abandoned` journal evidence for the same `request_id`
- cleanup restores healthy `edit` idle state

### 9. Transport Matrix Smoke

Switch the bridge transport across the supported transport set and rerun the
compact post-change validation route on each transport.

Pass criteria:

- each configured transport reaches healthy status
- status reports the requested and active transport coherently
- the compact post-change validation route passes on each transport
- cleanup restores the original bridge config

### 10. Lifecycle Stress Smoke

Run a short resilience route while another desktop app is frontmost, then verify
the bridge still handles refresh, scenario, and playmode lifecycle operations.

Pass criteria:

- status, refresh, contract scenario, and playmode enter/exit all succeed
- repeated `ensure-ready` works against the same editor session
- final status returns to healthy `edit`

### 11. Multi-Project Acceptance Smoke

Run the same compact readiness and refresh route against more than one Unity
project on the same host, with different project roots and transport bindings
where feasible.

Pass criteria:

- each project resolves to its own editor instance or offline state correctly
- status and refresh requests do not leak across project roots
- same-host transport selection stays per project, not global
- one project's degraded or offline state does not make the second healthy
  project look degraded

### 12. Discovery Divergence Smoke

Exercise cases where bridge state, host session state, and process-table
evidence disagree.

Minimum cases:

- `live_process_only`
- `stale_bridge_state`
- `stale_host_session`
- `bridge_disabled`

Pass criteria:

- `project-discovery-report` returns the expected
  `discovery_classification`
- summary surfaces return the expected `reconciliation_case`
- the surfaced `recommended_next_action` is coherent with the detected case

### 13. Health Policy Smoke

Exercise stale and ANR-suspected health classifications without accepting false
positive termination during normal lifecycle churn.

Pass criteria:

- healthy baseline reports fresh host health
- stale and ANR-suspected synthetic or live evidence classify correctly
- the surfaced termination policy is coherent with the health evidence
- normal compile/import/playmode churn does not escalate to destructive
  termination policy by default

## Public Template Assets

Generic example scenario JSON templates live under:

- `templates/scenarios/interactive_acceptance_smoke.json`
- `templates/scenarios/refresh_contract_smoke.json`
- `templates/scenarios/compile_contract_smoke.json`
- `templates/smoke/run_playmode_settled_state_regression.sh`
- `templates/smoke/run_playmode_lifecycle_retry_smoke.sh`
- `templates/smoke/run_request_abandoned_fault_suite.sh`
- `templates/smoke/run_transport_matrix_suite.sh`
- `templates/smoke/run_lifecycle_stress_suite.sh`
- `templates/smoke/run_lifecycle_fault_injection_suite.sh`
- `templates/smoke/run_multi_project_acceptance_suite.sh`
- `templates/smoke/run_phase2_divergence_suite.sh`
- `templates/smoke/run_phase3_health_policy_suite.sh`
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

PlayMode troubleshooting branch:

- if the first direct PlayMode request returns `playmode_state_invalid`, allow
  the host to exit Play Mode and retry once
- if the retry returns `request_lifecycle_reset`, recover by
  `request-final-status --request-id <id>` and inspect `result_trust_class`
  before concluding the test failed
- if the follow-up request returns `tests_busy`, treat that as stale test
  ownership and fail the smoke

Lifecycle contract:

- if the host opens Unity for the run, the runner should restore the original
  closed state on exit
- a closeout run is only considered successful when `restore-editor-state`
  reaches verified process exit; a plain quit acknowledgement is insufficient
- project-specific wrappers may opt out only when they intentionally want to
  preserve the interactive editor session for follow-up inspection
- after lifecycle churn or wrapper-side response loss, the preferred recovery
  path is `request-final-status --request-id <id>` before blind retry
- if the wrapper stalled before surfacing a usable `request_id`, the preferred
  recovery path is:
  - `request-status-summary`
  - then `request-latest-status --operation <operation>`
- when discovery and reconciliation surfaces exist, the preferred first
  diagnostic route is:
  - `project-discovery-report`
  - then compact status or final-status follow-up
- after a live-editor `devmode` package-source switch, the smoke contract should
  require:
  - `request-project-refresh`
  - then `request-status-summary`
  - before compile/test/scenario work claims success on the new package source
- when a compact summary surface exists, the smoke route should use it before
  raw result polling or large log inspection
- a lifecycle-reset smoke result is not accepted unless the wrapper exposes one
  obvious follow-up command using that exact `request_id`
- if the wrapper had already emitted `request_submitted`, a compact recovery
  result that reports:
  - `request_observed_in_unity_journal=false`
  - `bridge_changed_since_submission=true`
  - `operation_outcome=submitted_lost_after_lifecycle_churn`
  should be treated as a first-class regression signal for recovery clarity

Token-discipline contract:

- prefer `request-status-summary` over repeated raw status checks
- prefer `project-discovery-report` over manual state-file and process-table
  inspection when routing or recovery is unclear
- prefer `request-latest-status --operation ...` over manual request-journal
  digging when the request id is not already known
- prefer persisted scenario-result summaries over tight `unity.scenario.result`
  polling loops
- prefer compact batch failure summaries over direct `prepare.log` or
  `build.log` tailing
- treat a smoke workflow as failed if it repeatedly dumps raw scenario results
  or raw build logs before exhausting the compact summary surfaces
