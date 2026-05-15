# XUUnity MCP PlayMode Verdict Recovery Design

Date: `2026-05-15`
Status: `implemented-through-P2; proof-closed`

## Implementation Status

Last updated: `2026-05-15`

Implemented:

- P0 PlayMode verdict recovery vertical slice:
  - durable per-request test result artifacts
  - active test progress fields
  - host-owned compact `test_verdict`
  - persisted-result recovery when response payload is missing
  - runtime timeout classification after observed Test Runner progress
  - cleanup guidance for timeout/unproven PlayMode states
- P1 scenario/result recovery actions:
  - scenario wait reconciles terminal persisted results before final timeout
  - lookup by `run_id`, with scenario-name fallback
  - timeout details include latest persisted scenario evidence and recovery
    command
  - status summary exposes active test progress age and elapsed runtime
- P2 human-facing transport readiness wording:
  - `file_ipc` reports `transport_listener_state=inactive`
  - `file_ipc` reports `request_flow_state=usable`
  - `file_ipc` reports `transport_ready_for_requests=true`
  - strict listener readiness remains scoped to listener-backed transports such
    as `tcp_loopback`
- New project setup default:
  - setup writes `transport: tcp_loopback` to
    `Library/XUUnityLightMcp/config/bridge_config.json`
  - Unity package and host fallback defaults also resolve missing transport to
    `tcp_loopback`
  - `file_ipc` remains explicit fallback/compatibility mode

Validation completed:

- host Python regression suite: `90/90` passing after proof-gap closeout
  - includes regression coverage for `recover-editor-session --open-editor`
    using the helper that returns both JSON payload and process status
  - includes regression coverage for same-project host launch-in-progress reuse
- package self-tests through ApperfunHub MCP devmode:
  - EditMode `6/6` passing
  - PlayMode `5/5` passing
  - observed transport: `tcp_loopback`
- ApperfunHub project validation after P1:
  - EditMode `518/518` passing
  - PlayMode `250/250` passing on retry after a transient Unity Package
    Manager auth/log issue
- isolated setup smoke for a temporary Unity project root:
  - generated `bridge_config.json` contains `"transport": "tcp_loopback"`
- PlayMode verdict recovery proof suite through ApperfunHub MCP devmode:
  - compact passing PlayMode verdict with counts
  - scenario polling timeout reconciled from terminal persisted result
  - started PlayMode runtime timeout classified as
    `runtime_timeout_after_test_start`
  - cleanup guidance emitted as a concrete PlayMode exit command
  - cleanup command returned the editor to `playmode_state=edit`
  - proof cleanup removes its generated `Assets/XUUnityLightMcpGenerated`
    assembly assets and refreshes the project

Proof status:

- implementation, unit/fixture proof, package self-tests, consumer regression,
  and focused live proof are complete for the acceptance checks below
- the reusable proof route is
  `templates/smoke/run_playmode_verdict_recovery_proof_suite.sh`

## Purpose

This design turns the latest PlayMode retros into concrete MCP hardening
actions.

The critical defect is not only that PlayMode requests can cross Unity lifecycle
churn. The critical defect is that the operator surface can lose the final
verdict: a PlayMode run may start, keep running, complete, time out during test
execution, or persist evidence after the wrapper has already reported an
unclear failure. The MCP surface must compress that truth into a compact,
trustworthy result.

The design should not assume that the primary problem is a short timeout. Recent
full-suite evidence on a consumer project showed a PlayMode run completing after
lifecycle churn with a real Test Runner payload, including counts and failures.
That case is not an infrastructure timeout; it is an infrastructure success plus
a test-suite failure. The design therefore focuses on verdict separation:
transport outcome, lifecycle recovery outcome, and test verdict must be visible
as different fields.

## Problem Statement

The current lane has three distinct failure classes that are too easy to
collapse into one vague "PlayMode failed" outcome:

- the wrapper loses the response during lifecycle reset, while Unity later
  completes the request
- the PlayMode request starts successfully, but the test run exceeds its runtime
  budget before a final test result is available
- a scenario/result polling timeout occurs even though a terminal persisted
  result already exists or appears shortly after

The operator needs a single recovery output that answers:

- did Unity accept the request?
- did PlayMode test execution start?
- did tests pass, fail, produce no tests, time out, or remain unproven?
- what are `total`, `passed`, `failed`, `skipped`, and first failures?
- did lifecycle churn affect response delivery?
- is retry safe, or should the editor first be restored to `edit`?

## Design Principles

- Treat PlayMode verdict accounting as a first-class result plane, not as a
  side effect of response-file delivery.
- Distinguish transport/wrapper failure from Unity test verdict failure.
- Distinguish "test run started and exceeded runtime budget" from "request never
  reached Unity".
- Keep verdict ownership explicit: Unity owns observed test progress and raw
  test result facts; the host owns final operator classification from those
  facts plus journal and editor state.
- Prefer compact summaries before raw journal inspection.
- Never call a PlayMode lane validated when final test accounting is missing.
- Keep recovery idempotent: the first recovery command should inspect persisted
  truth before suggesting a retry.

## Verdict Ownership

PlayMode recovery has two layers of truth:

- Unity-side result facts: request acceptance, Test Runner callback progress,
  counters, failures, playmode state, timeout markers, and response handoff
  state.
- Host-side operator verdict: final classification built from response payload,
  persisted test artifact, request journal, and current bridge/editor state.

Only the host emits the final `test_verdict`. Unity emits `run_phase` and
observed facts. This prevents Unity-side code and host-side recovery from
assigning conflicting terminal meanings to the same request.

Verdict mapping:

| Evidence | Host `test_verdict` | Trust class | Retry stance |
| --- | --- | --- | --- |
| response or artifact has completed counts, `failed=0`, `total>0` | `passed` | `unity_completed_confirmed` | no retry |
| response or artifact has completed counts, `failed>0` | `failed` | `unity_failed_confirmed` | no infrastructure retry |
| response or artifact has completed counts, `total=0` | `no_tests` | `unity_completed_confirmed` | no retry |
| artifact has `run_phase=timed_out` after Test Runner start/progress | `runtime_timeout` | `unity_failed_confirmed` | inspect timeout or raise budget after cleanup |
| request accepted, artifact still running, timeout budget not expired | `in_progress` | `unity_unproven` | wait/recover final status |
| journal completed but no response payload or persisted artifact exists | `unity_unproven` | `wrapper_failed_unity_unproven` | inspect artifacts before retry |
| request never reached Unity journal | `infrastructure_error` | `request_not_observed` | retry after readiness recovery |

## Watchdog Contract

PlayMode cannot rely on `RunFinished` always firing. The persistent artifact
needs a watchdog closeout path.

Watchdog owner:

- Unity writes progress facts whenever callbacks fire.
- Host checks deadline expiry in `request-final-status` and
  `request-latest-status`.
- Host may classify an expired started run as `runtime_timeout` without waiting
  for Unity to write a final response, but it must preserve the Unity-side facts
  that justify the classification.

Deadline rules:

- `request_timeout_ms` is the outer wrapper budget.
- `runtime_timeout_ms` is the PlayMode test execution budget after Test Runner
  start or first progress.
- if Test Runner never starts before the outer request budget expires, classify
  as `timeout_before_test_start`, not `runtime_timeout`.
- if Test Runner started or emitted progress and the runtime budget expires,
  classify as `runtime_timeout_after_test_start`.
- if `RunFinished` arrives after host timeout classification, the later artifact
  may upgrade the verdict to `passed`, `failed`, or `no_tests`; summaries must
  expose that the result was `settled_after_timeout`.

Stale-state rule:

- an expired artifact may unblock future runs, but it must not be deleted before
  at least one final/latest status recovery can report the terminal reason.

## Current Codebase Review

This design is based on the current MCP code shape, not on a greenfield model.

What already exists:

- `XUUnityLightMcpPlayModeTestsOperation` and
  `XUUnityLightMcpPlayModeTestRunner` already map
  `unity.tests.run_playmode` to Unity Test Framework.
- `XUUnityLightMcpTestRunState` already persists an active run to
  `Library/XUUnityLightMcp/state/active_test_run.json`.
- `XUUnityLightMcpPersistedTestRunState` already stores request id, operation,
  test mode, started/completed timestamps, request timeout, counters, failures,
  completion basis, PlayMode state after settle, and response handoff state.
- `XUUnityLightMcpPersistedTestCallbacks.TestFinished` already records counters
  and failures incrementally.
- `RunFinished` builds a normalized `XUUnityLightMcpTestsPayload` and writes the
  final response through `XUUnityLightMcpResponseWriter`.
- `build_request_final_status` already reconstructs lifecycle truth from request
  journal events and current bridge state, then attaches response payload
  evidence when the outbox response still exists.
- `request-final-status` and `request-latest-status` already exist as operator
  recovery commands.

What is missing for the retro failures:

- `active_test_run.json` is an active ownership file, not a durable result
  artifact. `XUUnityLightMcpTestRunState.Clear()` deletes it after response
  handoff, so final-status recovery can lose counts when the response file is
  missing or was consumed.
- `TestStarted` is currently a no-op, so the host cannot distinguish "Test
  Runner never started" from "a specific test was running when the budget
  expired".
- there is no `run_phase`, `runtime_timeout_ms`, `timeout_classification`,
  `last_started_test`, `last_finished_test`, or `last_progress_at_utc` in the
  persisted model.
- `build_request_final_status` does not inspect any test-result artifact; its
  only result-payload path is `peek_response_payload`.
- `attach_operation_evidence_to_final_status` adds timing and artifact manifest,
  but it does not add a normalized PlayMode verdict.
- `BridgeStateWriter` exposes active request and busy reason, but not active
  PlayMode test progress.
- `wait_for_scenario_result_data` raises `scenario_wait_timeout` from polling
  state and does not reconcile terminal persisted scenario results before
  returning final failure.
- the current compact final status can say `completion_status=ok` and
  `result_trust_class=unity_completed_confirmed` while the nested test payload
  says `status=failed`; operators still need a top-level PlayMode test verdict
  summary to avoid reading infrastructure success as test success.

Net review:

- the existing request journal and active test state are good foundations;
- the high-value change is preserving test verdict facts beyond response-file
  delivery;
- the risky change is creating a second source of truth, so the host-owned
  verdict mapping above is required.

## Value And Actuality Review

| Change | Actuality in current code | Value | Risk |
| --- | --- | --- | --- |
| Durable PlayMode result artifact | Current `active_test_run.json` is deleted after handoff and cannot reliably support later recovery | High: directly fixes missing counts after response loss | Medium: must not create stale `tests_busy` ownership |
| Record `TestStarted` and progress fields | Current callback is empty | High: distinguishes runtime timeout from never-started request | Low: additive callback bookkeeping |
| Host PlayMode verdict summary | Current final status is lifecycle-first and payload-optional | High: gives the compact answer the retros needed | Medium: must keep verdict ownership host-side |
| Runtime timeout classification | Current request timeout and PlayMode runtime timeout are not separated in operator output | High: covers the clarified "started but timed out" case | Medium: deadline math must be deterministic |
| Cleanup guidance after timeout/reset | Current recovery can leave operator to infer PlayMode cleanup | Medium-high: reduces repeat failures and stuck `playing` sessions | Low |
| Scenario persisted-result reconciliation | Current scenario polling can false-negative when persisted result exists | Medium-high: fixes the contract smoke false negative | Medium: should be P1 because it is not the direct PlayMode verdict gap |
| `file_ipc` wording | Current status can be confusing for listenerless transport | Medium: improves operator trust but does not fix PlayMode verdicts | Low |

P0 should therefore stay focused on the first five rows. Scenario reconciliation
is valuable but belongs after the direct PlayMode verdict path is solid.

Scope correction:

- do not frame the P0 as "increase PlayMode timeouts";
- frame it as "make PlayMode verdict accounting explicit";
- a completed PlayMode request with failed tests must surface as
  `test_verdict=failed`, even when the wrapper-level operation is `ok`;
- a completed PlayMode request with passing tests must surface as
  `test_verdict=passed`;
- a started run that exceeds execution budget must surface as
  `test_verdict=runtime_timeout`;
- a lifecycle reset that later settles must not be treated as failure by itself.

## P0 Vertical Slice

### 1. Persist A Dedicated PlayMode Result Artifact

Add a durable per-request test result artifact under the project MCP `Library`
state, separate from the transient response outbox.

Required fields:

- `request_id`
- `operation`
- `test_mode`
- `run_phase`: `submitted`, `accepted`, `started`, `running`, `completed`,
  `timed_out`, `abandoned`, `response_written`, `settled_after_timeout`
- `started_at_utc`
- `last_progress_at_utc`
- `completed_at_utc`
- `request_timeout_ms`
- `runtime_timeout_ms`
- `timeout_classification`
- `total`
- `passed`
- `failed`
- `skipped`
- `failures`
- `last_started_test`
- `last_finished_test`
- `playmode_state_after_settle`
- `completion_basis`
- `lifecycle_churn_observed`
- `response_handoff_state`

Implementation target:

- extend `XUUnityLightMcpTestRunState`
- make `XUUnityLightMcpPersistedTestCallbacks.TestStarted` record progress
- make `TestFinished` record progress and counters
- keep the final artifact after response handoff long enough for
  `request-final-status` recovery
- keep an expired terminal artifact long enough for one recovery pass before
  stale cleanup removes it

### 2. Add A Normalized PlayMode Verdict Summary

Add a host-side summary builder that can be attached to:

- direct successful `unity.tests.run_playmode` responses
- `request-final-status`
- `request-latest-status`
- lifecycle-reset tool errors
- multi-project GUI test summaries

Output shape:

- `result_payload_available`
- `result_payload_source`: `response_payload`, `persisted_test_result`,
  `journal_only`, `none`
- `result_payload_reason`
- `test_verdict`: `passed`, `failed`, `no_tests`, `runtime_timeout`,
  `in_progress`, `unity_unproven`, `infrastructure_error`
- `run_phase`
- `total`
- `passed`
- `failed`
- `skipped`
- `first_failures`
- `last_started_test`
- `last_finished_test`
- `last_progress_at_utc`
- `runtime_timeout_observed`
- `timeout_classification`
- `lifecycle_churn_observed`
- `editor_cleanup_recommended`
- `cleanup_command`

Rule:

- `operation_status=ok` is not enough for PlayMode success. Success requires a
  `test_verdict` of `passed` or `no_tests` with trustworthy counts.
- `runtime_timeout` is a Unity test verdict, not a transport verdict, when Test
  Runner start/progress was observed before the timeout.

### 3. Upgrade `request-final-status` And `request-latest-status`

Current final status mostly summarizes journal lifecycle. It must also inspect
PlayMode result artifacts by `request_id`.

Resolution order:

1. response payload, if present
2. persisted PlayMode result artifact for the same `request_id`
3. request journal lifecycle state
4. current bridge/editor state

If the journal says `request_completed` but no result payload is available, the
summary must explicitly report:

- `result_payload_available=false`
- `result_payload_reason=response_missing_after_completed_request`
- `test_verdict=unity_unproven`

If the persisted artifact shows a runtime timeout after tests started, report:

- `test_verdict=runtime_timeout`
- `result_trust_class=unity_failed_confirmed`
- `recommended_next_action=inspect_test_timeout_or_raise_budget`

### 4. Add Runtime Timeout Classification For Started PlayMode Runs

The second retro clarified an important case: PlayMode can start and then fail
by execution time.

Add explicit classification:

- `timeout_before_unity_acceptance`
- `timeout_before_test_start`
- `runtime_timeout_after_test_start`
- `timeout_after_completion_before_response_commit`

For `runtime_timeout_after_test_start`, the operator output must include:

- last known test progress
- elapsed runtime
- configured timeout
- whether Unity is still in `playing`
- cleanup command if needed

This prevents a started-but-long-running test from being misreported as a bridge
startup or lifecycle failure.

### 5. Add Automatic PlayMode Cleanup Guidance

When any PlayMode request ends with timeout, lifecycle reset, or unproven
result, inspect current editor state.

If the editor is still `playing` or transitioning, include:

- `editor_cleanup_recommended=true`
- `cleanup_command=restore-editor-state --project-root <project>`
- `playmode_state`

Do not silently start a retry while the editor is still in `playing`.

### 6. Add One Regression Smoke For The Slice

Add one focused smoke that proves the vertical path:

1. start a targeted PlayMode request
2. force or simulate lifecycle churn while it is in flight
3. recover through `request-final-status`
4. assert compact `test_verdict`, counts or explicit `runtime_timeout`, and
   cleanup guidance
5. assert a follow-up PlayMode request is not blocked by stale `tests_busy`

Do not require scenario reconciliation or transport wording changes for this
first slice.

## P1 Actions

### 1. Reconcile Persisted Scenario Results Before Final Failure

Change scenario wait and smoke-runner timeout handling:

- when `unity.scenario.result` polling times out, search persisted scenario
  results by `run_id` first, then by scenario name
- if a terminal persisted result exists, return that terminal summary
- if it is `passed`, allow the runner to report success with a recovery note
- if it is `failed`, report the persisted failure summary
- if no terminal result exists, keep the timeout but include the latest
  persisted path and recovery command

This closes the false-negative pattern where the wrapper reports an operation
timeout while Unity-side scenario persistence already says `passed`.

### 2. Compact Recovery Command Output

Every lifecycle-reset or PlayMode timeout error should end with exact commands:

- `request-final-status --project-root <project> --request-id <id>`
- if request id is missing:
  `request-latest-status --project-root <project> --operation unity.tests.run_playmode`
- if cleanup is required:
  `restore-editor-state --project-root <project>`

### 3. PlayMode Progress Summary In Status

Expose active PlayMode test progress in `request-status-summary` when available:

- active test request id
- run phase
- last started test
- last progress age
- elapsed runtime
- timeout budget

This lets operators distinguish "hung bridge" from "test currently running".

### 4. Smoke Runner Result Reconciliation

Update checked-in smoke runners so failure output includes:

- compact final request status
- compact PlayMode verdict summary when operation is PlayMode tests
- compact persisted scenario summary when scenario polling timed out

Raw JSON remains fallback evidence, not the first operator answer.

## P2 Actions

### 1. Fix Human-Facing Transport Readiness For `file_ipc`

For `file_ipc`, avoid reporting same-host request flow as human-facing
`transport_not_ready` only because there is no listener.

Required wording split:

- `transport_listener_state=inactive`
- `request_flow_state=usable`
- `transport_ready_for_requests=true`

Keep strict listener readiness only for transports that actually have a
listener, such as `tcp_loopback`.

## Implementation Map

Host code:

- `templates/server_bridge_runtime.py`
  - attach PlayMode verdict summaries to final/latest status
  - classify runtime timeouts separately from lifecycle loss
  - apply the host-owned verdict mapping table
- `templates/server_operation_evidence.py`
  - include test result artifacts in artifact manifests
- `templates/server_summaries.py`
  - expose compact test verdict summary fields
- `templates/server_scenario_polling.py`
  - reconcile persisted terminal scenario results before timeout failure
- `templates/server_scenario_results.py`
  - support lookup by run id for recovery paths
- `templates/smoke/*.sh`
  - prefer compact recovery summaries before raw output dumps

Unity package:

- `templates/unity-package/Editor/Helpers/XUUnityLightMcpTestRunState.cs`
  - persist per-request result artifact and progress
  - preserve expired terminal artifacts through first recovery
- `templates/unity-package/Editor/Operations/XUUnityLightMcpPlayModeTestsOperation.cs`
  - ensure PlayMode callbacks update durable progress and final state
- `templates/unity-package/Editor/Core/XUUnityLightMcpModels.cs`
  - add result artifact/progress fields
- `templates/unity-package/Editor/Bridge/XUUnityLightMcpBridgeStateWriter.cs`
  - surface active PlayMode progress in bridge state when present

## Acceptance Checks

Current acceptance status as of `2026-05-15`:

| Check | Status | Proof |
| --- | --- | --- |
| A. Completed after lifecycle reset | Live-verified | Proof suite produced `test_verdict=passed`, `total=1`, `result_payload_source=response_payload`; package PlayMode self-tests also passed `5/5` with compact verdict/counts |
| B. Started then runtime timeout | Live-verified | Proof suite produced `test_verdict=runtime_timeout`, `timeout_classification=runtime_timeout_after_test_start`, `last_started_test`, `last_progress_at_utc`, and `runtime_timeout_ms=30000` |
| C. Scenario timeout with persisted success | Live-verified | Proof suite forced scenario polling timeout and returned `status=passed` from persisted result with `scenario_result_reconciliation_reason=terminal_persisted_result_after_poll_timeout` and `result_path` |
| D. Missing test payload is an explicit gap | Unit-verified | Host tests cover completed journal with missing response/result as `result_payload_available=false`, `test_verdict=unity_unproven`, and `result_trust_class=wrapper_failed_unity_unproven` |
| E. Cleanup guidance | Live-verified | Proof suite produced `editor_cleanup_recommended=true` with `cleanup_command=request-playmode-set --action exit`; executing the command returned final status to `health_status=healthy` and `playmode_state=edit` |

### A. Completed After Lifecycle Reset

Given a PlayMode request crosses a domain reload and later completes:

- `request-final-status` returns `request_completed=true`
- `result_payload_available=true`
- `test_verdict` is `passed`, `failed`, or `no_tests`
- counts are present
- `result_trust_class` is not `wrapper_failed_unity_unproven`

### B. Started Then Runtime Timeout

Given a PlayMode run starts but exceeds its runtime budget:

- final/latest status reports `test_verdict=runtime_timeout`
- final/latest status reports
  `timeout_classification=runtime_timeout_after_test_start`
- output includes `last_started_test` or `last_progress_at_utc`
- output includes elapsed runtime and timeout budget
- retry is not recommended until editor cleanup state is known

### C. Scenario Timeout With Persisted Success

Given scenario polling times out but the persisted scenario result is terminal
and passed:

- the runner reports success or success-with-recovery-note
- output includes `result_path`
- no final failure is emitted solely from the polling timeout

### D. Missing Test Payload Is An Explicit Gap

Given the journal says a PlayMode request completed but no response or persisted
test result exists:

- final status reports `result_payload_available=false`
- `test_verdict=unity_unproven`
- the lane is not counted as validated

### E. Cleanup Guidance

Given a PlayMode timeout or lifecycle reset leaves the editor in `playing`:

- final/latest status includes `editor_cleanup_recommended=true`
- output includes the concrete cleanup command
- a retry helper refuses or warns before starting another PlayMode run

## Proof Plan

The work is not complete when the code compiles. It is complete when the two
retro failure modes are impossible to misreport through the compact operator
surface.

Current proof-plan status as of `2026-05-15`:

| Proof area | Status | Notes |
| --- | --- | --- |
| Host unit and fixture tests | Complete for current implementation | `run_host_python_tests.sh` passes `90/90`; coverage includes persisted PlayMode result recovery, missing-payload unproven verdict, started runtime timeout, pre-start timeout separation, cleanup guidance, P1 scenario reconciliation, P2 `file_ipc` readiness wording, default `tcp_loopback` transport resolution, `recover-editor-session --open-editor` helper regression, and same-project host launch-in-progress reuse |
| Unity/package self-tests | Complete for current package self-test scope | `run_package_self_tests.sh --mode all` passes against ApperfunHub in devmode: EditMode `6/6`, PlayMode `5/5`, using `tcp_loopback` |
| Consumer project regression | Complete for broad project regression, with one transient retry | ApperfunHub EditMode `518/518` passed; ApperfunHub PlayMode `250/250` passed on retry after a transient Unity Package Manager auth/log issue |
| New-project setup default | Verified | Isolated setup smoke generated `Library/XUUnityLightMcp/config/bridge_config.json` with `"transport": "tcp_loopback"` |
| PlayMode verdict recovery proof suite | Complete | `run_playmode_verdict_recovery_proof_suite.sh` passed against ApperfunHub in devmode; it deploys a temporary generated PlayMode proof assembly under `Assets/`, cleans it up, and verifies pass, persisted scenario reconciliation, runtime timeout, cleanup guidance, final healthy/edit state, and no generated proof assets left in project status |
| Live started-runtime-timeout proof | Complete | Proof suite observed `runtime_timeout_after_test_start` with started/progress evidence |
| Live cleanup-guidance proof | Complete | Proof suite observed concrete PlayMode exit cleanup command and verified final `playmode_state=edit` |
| Live scenario polling false-negative proof | Complete | Proof suite forced poll-timeout recovery and reconciled the terminal persisted scenario result |

### Unit And Fixture Tests

Add host Python tests around `build_request_final_status` and the new verdict
builder:

- completed journal + missing response + persisted PlayMode result with counts
  returns `result_payload_available=true`, `result_payload_source=persisted_test_result`,
  and `test_verdict=passed` or `failed`
- completed journal + no response + no persisted result returns
  `result_payload_available=false`, `test_verdict=unity_unproven`, and does not
  claim validation success
- persisted artifact with `run_phase=timed_out`,
  `timeout_classification=runtime_timeout_after_test_start`, and test progress
  returns `test_verdict=runtime_timeout`
- persisted artifact with no Test Runner progress and expired request budget
  returns `timeout_classification=timeout_before_test_start`, not
  `runtime_timeout_after_test_start`
- current bridge state `playmode_state=playing` plus timeout/unproven verdict
  returns `editor_cleanup_recommended=true`

Add Unity-side edit/compile tests where practical for:

- `TestStarted` updates progress fields
- `TestFinished` preserves counters and first failures
- completed response handoff keeps a durable result artifact after
  `active_test_run.json` is cleared or released
- stale cleanup releases ownership without deleting the last terminal evidence
  before recovery can read it

### Synthetic Smoke Tests

Add one focused public smoke for P0:

1. run a targeted PlayMode test that can survive a bridge generation change
2. force or simulate lifecycle churn during the run
3. call `request-final-status --request-id <id>`
4. assert one of these terminal compact outcomes:
   - `test_verdict=passed` with counts
   - `test_verdict=failed` with counts and first failure
   - `test_verdict=runtime_timeout` with timeout classification and progress
5. assert no terminal result returns only `operation_status=ok` without
   `test_verdict`
6. assert a follow-up PlayMode request is not blocked by stale `tests_busy`

Add a started-then-timeout smoke:

1. run a targeted PlayMode test that intentionally exceeds a short runtime
   budget after Test Runner progress is observed
2. assert final/latest status reports
   `timeout_classification=runtime_timeout_after_test_start`
3. assert output includes `last_started_test` or `last_progress_at_utc`
4. assert cleanup guidance is present if the editor remains `playing`

### Live Regression For The Retros

To prove the original retro problems are fixed, rerun equivalent live paths and
require these outcomes:

- lifecycle-reset PlayMode run:
  - old bad outcome: `request_abandoned` or lifecycle reset with no compact
    counts
  - required new outcome: `request-final-status` reports a host-owned
    `test_verdict` and either counts or explicit `runtime_timeout`
- started-but-timeout PlayMode run:
  - old bad outcome: "PlayMode started but failed by execution time" without a
    clear compact classification
  - required new outcome:
    `test_verdict=runtime_timeout`,
    `timeout_classification=runtime_timeout_after_test_start`, progress fields,
    and cleanup guidance
- scenario polling false negative:
  - old bad outcome: smoke runner fails only because scenario result polling
    timed out while persisted result is terminal `passed`
  - required P1 outcome: runner reconciles persisted terminal result before
    final failure

### Closeout Criteria

Do not call the retrofit successful unless all of these are true:

- host tests cover the verdict mapping table
- a live or synthetic PlayMode lifecycle churn run returns compact
  `test_verdict`
- a started-then-timeout run is classified as runtime timeout, not transport or
  generic lifecycle failure
- final/latest status never treats PlayMode `operation_status=ok` as sufficient
  without result payload accounting
- cleanup guidance appears when the editor remains in `playing`
- stale ownership cleanup does not erase the terminal evidence needed by
  recovery

## Non-Goals

- Do not promise PlayMode cancellation support until Unity Test Framework
  cancellation semantics are proven for PlayMode.
- Do not treat batch PlayMode tests as equivalent to interactive PlayMode scene
  proof.
- Do not hide missing final counts behind `operation_status=ok`.

## Rollout Order

1. Implement the P0 vertical slice only: persisted artifact, host verdict
   summary, final/latest status wiring, runtime timeout classification, cleanup
   guidance, and one focused smoke.
2. Update README/CONTINUATION with the compact PlayMode recovery playbook.
3. Add persisted scenario result reconciliation.
4. Update broader smoke runners and public smoke acceptance cases.
5. Fix `file_ipc` human-facing transport readiness wording.
