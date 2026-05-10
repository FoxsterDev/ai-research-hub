# XUUnityLightUnityMcp Artifact And Timing Increment Archive

Date: `2026-05-10`
Status: `completed and archived`
Scope: `artifact manifest, structured timing, and immediate result-browsing follow-up`

## Original Intent

This note originally captured the next narrow same-host editor increment:

- additive artifact manifest output
- additive structured timing output

It is now retained in public `AIRoot` as a historical closeout record.

## Completed Outcome

The original increment is complete.

Completed public commits:

- `6b950a2`
  - `XUUnityLightUnityMcp: add request evidence outputs`
- `ff769f3`
  - `XUUnityLightUnityMcp: add scenario result browsing utilities`

Implemented public contract additions:

- additive request-scoped `artifact_manifest`
- additive request-scoped `structured_timing`
- host-side persisted scenario result browsing:
  - `request-scenario-results-list`
  - `request-scenario-result-latest`
  - `unity_scenario_results_list`
  - `unity_scenario_result_latest`

## What Was Validated

Validated on project through the project-local post-change runner.

Observed green route:

- `ensure-ready`
- `status`
- `health-probe`
- compile matrix `6/6`
- acceptance scenario
- contract scenario
- playmode settled-state regression

The validation route crossed real bridge lifecycle churn and still completed.

## What This Changed In Practice

The current same-host editor lane now gives first-class request-scoped evidence
for:

- when a request started and completed
- how long it took
- which scenario/capture/log/result artifacts are relevant
- whether those surfaced artifacts currently exist
- compact persisted-scenario browsing without falling back to raw file digging

## Remaining Highest-Value Work After This Increment

The next priority milestone is no longer artifact/timing output.

Recommended next milestone:

- close the remaining Phase 1 reliability hardening

Focus:

- broader lifecycle fault-injection proof
- request cancellation semantics
- stale request cleanup
- explicit host prerequisite reporting

Reason:

- the biggest remaining trust gap is still lifecycle and stale-request behavior
- cross-client proof is more valuable after that reliability floor is tighter

## Public Read Order After This Archive

1. `README.md`
2. `ROADMAP.md`
3. `CONTINUATION.md`
4. `SMOKE_TESTS.md`
5. this archive note
