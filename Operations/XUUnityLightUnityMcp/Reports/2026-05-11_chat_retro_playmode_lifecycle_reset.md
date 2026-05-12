# XUUnity Light Unity MCP Chat Retro: PlayMode Lifecycle Reset Session

Date: `2026-05-11`  
Status: `active public retro`

## 1. Executive summary

This session materially improved the public MCP surface, but it also exposed one
remaining trust gap in the direct PlayMode test lane.

The strongest result is that the operator path is now much better at separating:

- stale test state
- wrapper retry logic
- playmode-state preflight failure
- lifecycle-reset transport churn

The remaining failure is narrower:

- a direct `unity.tests.run_playmode` retry can still end in
  `request_lifecycle_reset`
- the request journal proves the wrapper/session failed after the Unity-side
  request was accepted
- the evidence does not prove that the PlayMode test body itself failed

That distinction is now visible enough to avoid false-negative conclusions, but
the lane is still not fully trustworthy under churn.

## 2. Evidence base

Primary evidence used in this retro:

- current session timeline and operator actions
- `ensure-ready` result after switching the project to `devmode`
- `request-final-status --request-id 2cf4cfb1-4a8f-4532-a60f-0f57847e3d9f`
- current `Library/XUUnityLightMcp/state/bridge_state.json` summary
- current public docs:
  - `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
  - `AIRoot/Operations/XUUnityLightUnityMcp/DESIGN.md`
  - `AIRoot/Operations/XUUnityLightUnityMcp/CONTINUATION.md`
  - `AIRoot/Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`

Most important request-journal evidence:

- `2cf4cfb1-4a8f-4532-a60f-0f57847e3d9f`
  - `request_submitted`
  - `request_started`
  - `request_abandoned`
  - `request_reclassified`
- reclassified reason:
  - `bridge_generation_changed_before_response`
- final status:
  - `operation_outcome=retryable_after_lifecycle_reset`
  - `request_observed_in_unity_journal=true`
  - `bridge_changed_since_submission=true`
  - `recovery_gap_detected=false`
  - `bridge_stabilization.safe_to_retry=true`

Current live bridge evidence after `ensure-ready` in `devmode`:

- `bridge_generation=138`
- `transport=tcp_loopback`
- `transport_listener_state=listening`
- `health_status=healthy`
- `playmode_state=edit`
- package dependency:
  - `alignment=aligned`
  - `dependency_mode=file`

## 3. Timeline

1. The session started from a noisy MCP/operator state with stale request and
   lifecycle-reset history around PlayMode tests.
2. Public MCP fixes were added for:
   - faster final-status resolution after request reclassification
   - compile-gated recovery
   - stale bridge cleanup
   - session-scoped log diagnosis
   - stronger closeout truth
3. The GUI subset runner was hardened:
   - parallel cross-project execution
   - JSON-aware failure parsing
   - retry hooks for lifecycle reset and `tests_busy`
   - macOS window arrangement helper with safe fallback when Accessibility
     permission is missing
4. The session then exposed a deeper PlayMode lane issue:
   - `playmode_state_invalid`
   - then stale `tests_busy`
   - then repeated `request_lifecycle_reset`
5. Package-side fixes were added for stale persisted test state and stale
   in-memory active test ownership.
6. The project was switched to `devmode`, `ensure-ready` was run, and package
   alignment was verified as `aligned`.
7. The remaining residual after all fixes is a repeated PlayMode
   lifecycle-reset path on a direct `unity.tests.run_playmode` retry.

## 4. What worked well

- `ensure-ready` in `devmode` produced a healthy live bridge with aligned local
  package wiring.
- `request-final-status` gave enough evidence to separate transport/session
  failure from Unity-side acceptance.
- request journaling is now strong enough to prove lifecycle churn by
  `request_id`.
- stale request cleanup and closeout proof are materially better than they were
  at the start of the session.
- stale test-run artifacts no longer dominated diagnosis.
- the GUI runner now actually retries on lifecycle-reset payloads instead of
  relying only on shell exit behavior.
- the window-arrangement helper degraded safely with
  `assistive_access_not_granted` instead of hanging.

## 5. What worked poorly

- the direct PlayMode test lane is still operationally weak during lifecycle
  churn.
- a retry after `playmode.set exit` can still lose its response channel and
  become `request_lifecycle_reset`.
- the operator still had to inspect request-journal/final-status evidence to
  know whether the failure was Unity-side or wrapper-side.
- one remaining failure class still requires too much manual reasoning:
  - request accepted
  - bridge generation changed
  - no `request_completed`
  - retryable, but not conclusively passed

## 6. What was not explicit enough

- the docs already describe lifecycle-reset recovery well, but they do not yet
  make this PlayMode-specific churn pattern concrete enough.
- the default operator path still does not make it obvious that:
  - `request_lifecycle_reset` after PlayMode retry is not proof that the test
    failed
  - the correct interpretation is “wrapper/session lost trust in the result”
- the smoke contract does not yet force a dedicated assertion for direct
  PlayMode request stability after `playmode.set exit`.

## 7. What the operator needed but did not have

- one obvious compact statement such as:
  - `unity_result_unproven_wrapper_failed`
- one compact summary field telling the operator whether the post-reset retry
  exhausted a known safe retry budget
- one PlayMode-specific smoke/fault suite that asserts:
  - stale active test ownership is released
  - retry after `playmode_state_invalid` is safe
  - retry after bridge-generation churn reaches either:
    - `request_completed`
    - or a stronger terminal “unproven but retry-safe” verdict

## 8. Scoring

Scale: `1-10`

| Category | Score | Notes |
|---|---:|---|
| Unity-side execution stability | 6 | Editor and bridge are healthy, but direct PlayMode retry still churns |
| Request journaling quality | 9 | Strong enough to prove lifecycle reset and request acceptance |
| Bridge health observability | 8 | Status/final-status/bridge-state are now useful and compact |
| Wrapper-to-operator clarity | 7 | Better than before, but PlayMode retry outcome is still not obvious enough |
| Recovery guidance quality | 8 | `recover-editor-session` and closeout surfaces are strong |
| Transport lifecycle transparency | 8 | Reclassified request evidence is clear |
| End-to-end trustworthiness during churn | 6 | Better, but still not reliable enough for direct PlayMode claims |
| Parallel request handling | 8 | Cross-project parallelism is valid; per-project serialization is understood |
| Token efficiency of the default operator path | 7 | Much improved, but the remaining PlayMode issue still forces extra inspection |
| Time-to-diagnosis | 7 | Considerably better than before this session, still not cheap for PlayMode churn |
| Validation workflow discipline | 8 | Compile-first and summary-first patterns are now clear |

Overall session score: `7.5 / 10`

## 9. Priority improvements

### P0

1. Add a direct PlayMode retry fault suite to public MCP smoke coverage.
   Required assertion:
   - `playmode_state_invalid -> playmode.set exit -> retry`
   - must not end in unresolved `request_lifecycle_reset`

2. Strengthen final-status phrasing for retryable lifecycle-reset results.
   Add a compact surface that explicitly distinguishes:
   - `unity_failed`
   - `wrapper_failed_unity_unproven`
   - `unity_completed_after_lifecycle_reset`

3. Add one public compact field to retryable lifecycle-reset summaries:
   - `result_trust_class`

### P1

4. Promote the runner behavior change into docs:
   - retry decisions must be based on JSON payload truth, not only process exit

5. Add a dedicated smoke check for stale in-memory test ownership release after
   reclassified PlayMode requests.

6. Extend public docs with one PlayMode-specific troubleshooting branch:
   - `tests_busy`
   - `playmode_state_invalid`
   - `request_lifecycle_reset`

### P2

7. Add a compact operator summary for macOS arrangement failure:
   - `assistive_access_not_granted`
   - remediation text

## 10. Public-promotion recommendations

Promote into `README.md`:

- direct statement that `request-final-status` is the canonical truth source for
  lifecycle-reset incidents
- direct statement that `request_lifecycle_reset` is not equivalent to
  Unity-side test failure

Promote into `DESIGN.md`:

- PlayMode-specific lifecycle-churn note:
  - bridge generation can change after request acceptance and before response
    commit
  - this requires a distinct trust classification

Promote into `CONTINUATION.md`:

- the stale test-run ownership lessons from this session
- the requirement that retry orchestration must read structured payloads, not
  only shell exit codes

Promote into `SMOKE_TESTS.md`:

- a new direct PlayMode churn smoke:
  - request while not in edit mode
  - automatic exit
  - retry
  - verify terminal trust class

Promote into wrapper/runtime behavior:

- compact retry-attempt annotation in stderr summaries
- compact `result_trust_class`
- explicit retry budget reporting for lifecycle-reset retries

## 11. Final verdict

This session was a good example of why the public MCP needs retrospectives built
from real request ids and not from vague error memory.

The system is meaningfully stronger now:

- stale log noise is reduced
- closeout truth is stronger
- stale test ownership is reduced
- retry logic is less brittle
- `devmode` alignment and `ensure-ready` are straightforward

But the direct PlayMode lane is still not fully productized under lifecycle
churn.

The correct reusable conclusion is:

- Unity editor startup, bridge health, journaling, and recovery are now mostly
  strong
- direct PlayMode validation after churn is still a trust-boundary problem, not
  a solved path
- the next public improvement should target PlayMode-specific lifecycle-reset
  trust classification and smoke coverage, not another generic transport refactor
