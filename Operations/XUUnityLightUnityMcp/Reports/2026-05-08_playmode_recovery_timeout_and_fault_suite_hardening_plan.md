# XUUnityLightMcp Hardening Plan

Date: `2026-05-08`
Status: `public-safe working plan`
Scope: `PlayMode recovery, request-abandoned validation, and timeout budgeting`

## Goal

Harden the PlayMode test lane, lifecycle-reset recovery, and request-abandoned
fault validation so the package behaves correctly on weak hosts where:

- compile plus domain reload can legitimately take about 100 seconds
- PlayMode tests can legitimately run for 1-2 minutes
- nested scenario paths may cross compile, refresh, and PlayMode transitions in
  one request budget

## Phase 1: Host Timeout And Recovery Budget Hardening

Objective:
- remove short fixed post-reset recovery waits
- make lifecycle-reset recovery use the remaining request budget
- add operation-aware high caps for long-running operations

Changes:
- extend `templates/server_specs.py` lifecycle policies with post-reset recovery
  caps for long-running operations
- extend `templates/server.py` lifecycle policy resolution and transport
  invocation wiring
- extend `templates/server_bridge_runtime.py` so recovery waits use remaining
  request budget instead of a hard 5-second window

Acceptance:
- long PlayMode tests are not falsely reported as `request_lifecycle_reset`
- long scenario runs are not falsely reported as transport failures immediately
  after reload
- short operations still fail promptly when truly broken

## Phase 2: Persisted PlayMode Recovery State Machine

Objective:
- preserve valid PlayMode resume-after-reload
- prevent stale PlayMode pending state from permanently blocking future test runs

Changes:
- extend persisted test-run state in
  `templates/unity-package/Editor/Core/XUUnityLightMcpModels.cs`
- track original request timeout in
  `templates/unity-package/Editor/Helpers/XUUnityLightMcpTestRunState.cs`
- treat original request timeout as the upper recovery deadline for abandoned
  PlayMode runs
- discard expired unrecovered PlayMode state instead of leaving permanent
  `tests_busy`

Acceptance:
- valid PlayMode reload resume still completes normally
- unrecovered PlayMode runs stop blocking later tests after their original
  request budget expires
- EditMode abandoned runs still clean up immediately

## Phase 3: Deterministic Request-Abandoned Fault Suite

Objective:
- make the public request-abandoned smoke route target only the synthetic test
  fixture
- remove dependence on the host project's full EditMode test inventory

Changes:
- update `templates/smoke/run_request_abandoned_fault_suite.sh`
- target the synthetic test by explicit `testNames` payload instead of all-tests
  execution
- simplify the synthetic test body so it stays in-flight without adding extra
  PlayMode noise
- preserve preexisting directories and tracked `.meta` files during cleanup

Acceptance:
- request-abandoned route reproduces consistently on a live consumer project
- the route no longer deletes tracked project metadata
- the route does not accidentally run the entire EditMode suite

## Validation Matrix After Implementation

Recommended live validation order:

1. `run_mcp_request_abandoned_fault_suite.sh`
2. `run_mcp_lifecycle_fault_injection_suite.sh`
3. `run_mcp_lifecycle_stress_suite.sh`
4. `run_mcp_transport_matrix_suite.sh`
5. `run_mcp_post_change_validation.sh`
6. `run_mcp_smoke_suite.sh`

## Execution Status Snapshot

- Phase 1: completed
- Phase 2: completed
- Phase 3: implemented, regression cleanup still in progress at capture time

## Current Validation Notes At Capture Time

- `run_mcp_request_abandoned_fault_suite.sh` passed with deterministic targeting
  and a longer synthetic in-flight window
- full validation was not fully clean yet:
  - `run_mcp_lifecycle_fault_injection_suite.sh` was not deterministically
    observing a bridge-generation transition on every run
  - after repeated fault-route cleanup, Unity could still report
    `compile_broken` for later PlayMode requests because deleted temporary `.cs`
    paths remained visible to Unity compilation state longer than the cleanup
    path assumed

## Reusable Takeaways

- lifecycle recovery should spend the remaining request budget rather than a
  short fixed sleep
- persisted PlayMode recovery state needs an explicit expiry model or it becomes
  a `tests_busy` trap
- request-abandoned smoke routes are only trustworthy when they isolate the
  synthetic fixture instead of depending on the project's broader test graph
