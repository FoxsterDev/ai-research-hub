# XUUnity MCP Test Result Accounting Consistency Design

Date: `2026-05-16`
Status: `backlog design note, reviewed against current source`

Last source review: `2026-05-16`

## Purpose

This document preserves a public-safe backlog item for a subtle accounting
inconsistency in `unity.tests.run_playmode` result reporting.

The issue does not currently invalidate test pass/fail verdicts. It affects
operator trust in secondary state accounting, specifically the value reported
for `playmode_state_after_settle` when comparing the direct response payload
with the persisted compact test-result artifact.

## Observed Symptom

A PlayMode test run can complete successfully through Unity Test Runner
callbacks, but two accounting surfaces may disagree:

- direct operation response payload: `playmode_state_after_settle = edit`
- persisted compact test result: `playmode_state_after_settle = playing`

The pass/fail totals still matched the Unity Test Runner callback result.

## Public-Safe Evidence

Evidence was captured from a consumer project using the public MCP package in
local devmode. Project-specific paths and names are intentionally omitted.

### Direct PlayMode Run

Operation:

- `unity.tests.run_playmode`
- request id: `e4fe0029-e473-4f79-8002-2bce938b58bb`
- filter: one PlayMode test assembly
- direct response verdict: passed
- direct response totals: `total=20`, `passed=20`, `failed=0`, `skipped=0`
- direct response `completion_basis`: `unity_test_runner_callbacks`
- direct response `playmode_state_after_settle`: `edit`

Persisted compact artifact for the same request:

```json
{
  "request_id": "e4fe0029-e473-4f79-8002-2bce938b58bb",
  "operation": "unity.tests.run_playmode",
  "run_phase": "response_written",
  "total": 20,
  "passed": 20,
  "failed": 0,
  "skipped": 0,
  "completion_basis": "unity_test_runner_callbacks",
  "playmode_state_after_settle": "playing",
  "lifecycle_churn_observed": false
}
```

Related request journal events:

```json
{
  "event_type": "request_completed",
  "event_source": "unity_bridge",
  "operation": "unity.tests.run_playmode",
  "operation_status": "ok",
  "request_id": "e4fe0029-e473-4f79-8002-2bce938b58bb"
}
```

```json
{
  "event_type": "request_reclassified",
  "event_source": "host_wrapper",
  "operation": "unity.tests.run_playmode",
  "reason": "bridge_generation_changed_during_post_request_settle",
  "reclassified_status": "settled_after_lifecycle_reset",
  "request_id": "e4fe0029-e473-4f79-8002-2bce938b58bb"
}
```

### Full-Suite Observation

Another full PlayMode run showed trustworthy final callback totals while the
persisted compact artifact reported `playmode_state_after_settle = playing`:

```json
{
  "operation": "unity.tests.run_playmode",
  "total": 250,
  "passed": 250,
  "failed": 0,
  "skipped": 0,
  "completion_basis": "unity_test_runner_callbacks",
  "playmode_state_after_settle": "playing"
}
```

This reinforces that the issue should be treated as result-accounting cleanup,
not as evidence of failed tests.

## Why This Matters

`playmode_state_after_settle` is used as operator evidence for whether the
editor returned to a stable Edit Mode boundary after a PlayMode validation lane.

If response payloads and persisted artifacts disagree, a later recovery or
summary command can make a different claim than the original direct response.
That undermines confidence in post-run state accounting even when the test
verdict itself is correct.

## Current Code Context

Relevant public code areas:

- `templates/unity-package/Editor/Helpers/XUUnityLightMcpTestRunState.cs`
- `templates/unity-package/Editor/Operations/XUUnityLightMcpPlayModeTestsOperation.cs`
- `templates/server_specs.py`
- `templates/server_bridge_payloads.py`
- `templates/server_bridge_runtime.py`
- `templates/server_operation_evidence.py`
- `templates/server.py`
- `templates/smoke/run_playmode_settled_state_regression.sh`

## Source Review Findings

The current source narrows the likely root cause.

Unity-side test-run accounting:

- `CompleteAndBuildResponse(...)` stores the final test summary and the supplied
  `playmodeStateAfterSettle`, persists the active test-run state, and builds the
  direct response payload.
- `TryWritePendingCompletedResponse()` writes the response, marks
  `response_handoff_state = written`, sets `run_phase = response_written`, and
  persists the compact result artifact.
- `XUUnityLightMcpPersistedTestCallbacks.RunFinished(...)` passes
  `XUUnityLightMcpPlayModeStateOperation.ResolvePlayModeState()` into
  `CompleteAndBuildResponse(...)`.
- For PlayMode tests, `RunFinished(...)` can still execute while Unity reports
  Play Mode as active or transitioning. That makes a Unity-side persisted value
  of `playing` plausible and expected at callback time.

Host-side response normalization:

- `server_specs.py` configures `unity.tests.run_playmode` with
  `wait_for_idle_after = True` and `idle_stable_cycles_after = 2`.
- `server.py` waits for post-request editor idle after the bridge response.
- `server_bridge_payloads.py` then calls `normalize_tests_payload_from_lifecycle`
  for `unity.tests.run_playmode`.
- `normalize_tests_payload_from_lifecycle(...)` overwrites
  `playmode_state_after_settle` in the response payload with
  `idle_wait_after.playmode_state` when that host-side lifecycle state exists.
- This explains why the direct response can report `edit` even when the
  persisted test result for the same request still reports `playing`.

Bridge lifecycle event context:

- `server_bridge_runtime.py` records `request_reclassified` with
  `reason = bridge_generation_changed_during_post_request_settle` when the
  bridge identity changes between the pre-request state and the post-request
  settled state.
- For PlayMode tests this can happen naturally because leaving Play Mode may
  recreate the bridge session.
- The reclassification is useful lifecycle evidence, but it is not by itself a
  failed request or failed test-run signal.

Existing regression gap:

- `templates/smoke/run_playmode_settled_state_regression.sh` currently verifies
  direct and scenario response payloads both report `edit`.
- That smoke does not compare the response payload against
  `Library/XUUnityLightMcp/state/test_results/<request_id>.json`.
- Therefore the current smoke can pass while the persisted compact artifact
  still carries the older Unity-side callback-time state.

Source-grounded conclusion:

- The mismatch is not random.
- The direct response and persisted artifact are using two different evidence
  moments under one field name:
  - Unity callback-time state, persisted by `XUUnityLightMcpTestRunState`
  - host post-idle state, applied by `normalize_tests_payload_from_lifecycle`
- The design fix should make those evidence moments explicit and reconcile the
  persisted artifact, not change test verdict logic.

## Desired Design Contract

For completed PlayMode test runs:

1. The direct response payload and persisted compact test result must either
   agree on `playmode_state_after_settle`, or explicitly report that they come
   from different evidence moments.
2. If host-side settle produces a more authoritative post-run editor state, that
   authority should be named and preserved in both direct and recovery surfaces.
3. Persisted compact artifacts should include enough metadata to explain the
   source of the state value.
4. Test verdict fields must remain callback-derived and must not be weakened by
   editor state uncertainty.

## Candidate Schema Patch

Add explicit source metadata instead of overloading one field. The final field
set should be small, backward-compatible, and usable from both direct responses
and persisted compact artifacts.

Recommended final fields:

- `playmode_state_after_test_callbacks`
- `playmode_state_after_host_settle`
- `playmode_state_after_settle`
- `playmode_state_after_settle_source`
- `playmode_state_accounting_consistent`
- `playmode_state_accounting_note`

Avoid adding both `playmode_state_after_unity_response_build` and
`playmode_state_after_unity_response_write` unless implementation reveals a real
diagnostic need. The currently useful split is callback-time Unity state versus
host post-idle state.

## Final Field Semantics

`playmode_state_after_test_callbacks`

- Source: Unity editor package.
- Capture point: `XUUnityLightMcpPersistedTestCallbacks.RunFinished(...)`, at
  Unity Test Runner completion.
- Meaning: the Unity Play Mode state at test callback completion time.
- Expected values: existing `ResolvePlayModeState()` output such as `edit`,
  `playing`, `transitioning`, or empty if unavailable.
- Stability: diagnostic. It may be `playing` for successful PlayMode runs.

`playmode_state_after_host_settle`

- Source: host wrapper lifecycle state.
- Capture point: `idle_wait_after.playmode_state` after
  `unity.tests.run_playmode` completes and host-side idle settle finishes.
- Meaning: the best host-observed editor state after the wrapper's post-request
  settle contract.
- Stability: preferred final operator evidence when present.

`playmode_state_after_settle`

- Source: compatibility field.
- Meaning: the best final state this surface wants older clients to read.
- Rule: prefer `playmode_state_after_host_settle` when present; otherwise fall
  back to `playmode_state_after_test_callbacks`; otherwise keep the existing
  value or empty string.
- This field should not be used to infer test pass/fail verdict.

`playmode_state_after_settle_source`

- Source label for `playmode_state_after_settle`.
- Suggested values:
  - `host_post_idle_settle`
  - `unity_test_callbacks`
  - `legacy_persisted_result`
  - `unavailable`

`playmode_state_accounting_consistent`

- Boolean.
- `true` when callback-time and host-settled values are both absent, both
  equal, or only one evidence source is available.
- `false` when both evidence sources exist and differ.
- A `false` value is an accounting note, not a test failure.

`playmode_state_accounting_note`

- Short human-readable explanation.
- Use it only when values differ or source quality is degraded.
- Suggested message for the known case:
  `callback-time state differed from host post-idle state; test verdict remains callback-derived`

## Backward Compatibility

- Do not remove `playmode_state_after_settle`.
- Do not change `status`, `total`, `passed`, `failed`, `skipped`,
  `completion_basis`, `run_phase`, or failure payload semantics.
- Old persisted artifacts without new fields must still summarize correctly:
  - treat existing `playmode_state_after_settle` as
    `legacy_persisted_result`
  - set `playmode_state_after_settle_source = legacy_persisted_result` if the
    source cannot be inferred
  - do not invent host-settled evidence for old artifacts unless a matching
    request lifecycle record is available
- Existing clients that read only `playmode_state_after_settle` should receive
  the best final state available on newly written responses and artifacts.

## Data Ownership

- Unity package owns callback-time state and raw test callback totals.
- Host wrapper owns post-idle settled state and response/artifact reconciliation.
- Host-side reconciliation may augment persisted compact artifacts, but it
  should not rewrite callback-derived totals or failure lists.

## Candidate Implementation Direction

Preferred direction:

1. Preserve Unity-side callback-time state instead of treating it as final
   settled state.
2. In `XUUnityLightMcpTestRunState`, record the value captured in
   `RunFinished(...)` as callback-time evidence, for example
   `playmode_state_after_test_callbacks`.
3. Keep `playmode_state_after_settle` in the Unity response payload for backward
   compatibility, but attach a source field so clients can tell whether it came
   from Unity callback time or host post-idle settle.
4. Add a host-side test-result accounting reconciler near
   `normalize_tests_payload_from_lifecycle(...)` or the evidence enrichment
   layer.
5. When a persisted test result is available, compare its
   `playmode_state_after_settle` against the direct response payload and any
   host-side post-settle state.
6. If values differ, keep test verdict unchanged but attach explicit accounting
   metadata.
7. If host-side post-settle state is considered authoritative for the legacy
   `playmode_state_after_settle` field, update or augment the persisted compact
   result with that final source-marked value instead of silently leaving the
   older Unity-side value.
8. Extend the settled-state smoke so it checks both:
   - direct response payload
   - persisted compact artifact for the same request id

Do not make `RunFinished(...)` wait for Edit Mode directly. That callback is a
test-run completion boundary, not a lifecycle settle boundary. Host-side idle
settle is the better place to define post-run editor state.

## Implementation Checklist

### Unity Package Model

Files:

- `templates/unity-package/Editor/Core/XUUnityLightMcpModels.cs`
- `templates/unity-package/Editor/Helpers/XUUnityLightMcpTestRunState.cs`

Changes:

- Add nullable-or-empty string fields to the persisted test-run state and tests
  payload model:
  - `playmode_state_after_test_callbacks`
  - `playmode_state_after_host_settle`
  - `playmode_state_after_settle_source`
  - `playmode_state_accounting_note`
- Add bool field:
  - `playmode_state_accounting_consistent`
- In `RunFinished(...)`, capture `ResolvePlayModeState()` into
  `playmode_state_after_test_callbacks`.
- For the Unity-side response built before host settle, set:
  - `playmode_state_after_settle = playmode_state_after_test_callbacks`
  - `playmode_state_after_settle_source = unity_test_callbacks`
  - `playmode_state_accounting_consistent = true`
- Preserve current totals and failures logic.

### Host Payload Normalization

Files:

- `templates/server_bridge_payloads.py`
- optionally `templates/server_operation_evidence.py` if the reconciliation
  should be attached during evidence enrichment rather than raw payload
  normalization

Changes:

- Extend `normalize_tests_payload_from_lifecycle(...)` to preserve the incoming
  Unity callback-time value before overwriting the compatibility field.
- Set `playmode_state_after_host_settle` from `idle_wait_after.playmode_state`
  when available.
- Recompute `playmode_state_after_settle` according to the compatibility rule:
  host-settled value first, callback-time fallback second.
- Set `playmode_state_after_settle_source`.
- Set `playmode_state_accounting_consistent` and
  `playmode_state_accounting_note`.
- Keep response payload verdict fields unchanged.

### Persisted Artifact Reconciliation

Files:

- `templates/server_operation_evidence.py`
- or a small new helper imported by both `server_bridge_payloads.py` and
  `server_operation_evidence.py`

Changes:

- Locate the persisted compact artifact for the request:
  `Library/XUUnityLightMcp/state/test_results/<request_id>.json`.
- After host-side settle, update or augment that artifact with the same
  source-marked fields as the normalized response payload.
- Do not rewrite callback-derived totals, failures, status, timestamps, or
  `completion_basis`.
- Preserve the original Unity callback-time state in
  `playmode_state_after_test_callbacks`.
- If artifact update fails, keep the direct response enriched with an accounting
  note and do not fail the test run.

### Recovery And Summary Surfaces

Files:

- `templates/server_operation_evidence.py`
- `templates/server.py`
- any final/latest status helper that summarizes persisted test results

Changes:

- When summary data comes from a persisted artifact, include the new source
  fields in the compact summary.
- If only a legacy artifact exists, mark source as `legacy_persisted_result`.
- Ensure `test_verdict` stays derived from totals/status/timeout fields, not
  from Play Mode state fields.

### Smoke And Regression Coverage

Files:

- `templates/smoke/run_playmode_settled_state_regression.sh`
- host Python tests under `tests/`, likely around payload normalization and
  artifact accounting

Changes:

- Extend the smoke to read
  `Library/XUUnityLightMcp/state/test_results/<request_id>.json`.
- Assert direct response and persisted artifact agree on the compatibility field
  after host settle when host settle evidence exists.
- Assert callback-time state is still preserved when it differs.
- Add a host-side unit test with synthetic payload/lifecycle input:
  - incoming payload `playmode_state_after_settle = playing`
  - lifecycle `idle_wait_after.playmode_state = edit`
  - expected compatibility field `edit`
  - expected callback field `playing`
  - expected host field `edit`
  - expected source `host_post_idle_settle`
  - expected consistency `false`

## Suggested Test Matrix

- Host unit: no lifecycle state, legacy payload only.
- Host unit: lifecycle state matches callback state.
- Host unit: lifecycle state differs from callback state.
- Host unit: missing persisted artifact does not fail response enrichment.
- Host unit: persisted artifact update preserves totals and failures.
- Live smoke: direct PlayMode request reports final `edit` and persisted artifact
  reports the same compatibility value.
- Live smoke: lifecycle reclassification after PlayMode does not turn a passed
  callback result into retry/failure status.

## Acceptance Criteria

- Direct `unity.tests.run_playmode` responses and persisted test-result summaries
  no longer silently disagree on `playmode_state_after_settle`.
- When a disagreement is unavoidable because the states are sampled at different
  moments, both surfaces include explicit source metadata.
- `test_verdict`, totals, failures, and timeout classification remain based on
  Unity Test Runner callbacks or persisted terminal test-run evidence.
- Existing clients that read only `playmode_state_after_settle` continue to get
  a useful value.
- Regression coverage exists at the host-side accounting layer and, if
  practical, in a lifecycle smoke lane.
- `run_playmode_settled_state_regression.sh` or a successor smoke compares the
  direct response payload and persisted compact artifact for the same request.
- When PlayMode lifecycle churn changes bridge generation after test callbacks,
  the result remains classified as a passed test run with explicit lifecycle
  accounting metadata, not as a retry-needed product validation failure.

## Suggested Reproduction Recipe

1. Run a PlayMode suite through the local MCP wrapper.
2. Capture the direct response payload from stdout.
3. Read the matching persisted compact artifact:

   `Library/XUUnityLightMcp/state/test_results/<request_id>.json`

4. Compare these fields:

   - `total`
   - `passed`
   - `failed`
   - `skipped`
   - `completion_basis`
   - `run_phase`
   - `playmode_state_after_settle`
   - `lifecycle_churn_observed`
   - any future `playmode_state_after_*_source` fields

5. Read the matching request journal events:

   `Library/XUUnityLightMcp/journal/requests/*<request_id>*`

6. Check whether a `request_reclassified` event exists with:

   - `reason = bridge_generation_changed_during_post_request_settle`
   - `reclassified_status = settled_after_lifecycle_reset`

## Non-Goals

- Do not treat this as a product test failure.
- Do not change Unity Test Runner pass/fail verdict logic unless callback totals
  are also proven wrong.
- Do not remove bridge lifecycle reclassification; it is useful evidence.
- Do not add host-private project assumptions to the public MCP package.
