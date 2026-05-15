# XUUnity MCP Evidence Ergonomics And Profile Flow Design

Date: `2026-05-15`
Status: `partially implemented`

## Purpose

This document collects public-safe MCP improvements that make Unity editor
evidence cheaper to collect, easier to trust, and safer around build-profile or
environment mutations.

The target use case is a startup, lifecycle, or runtime smoke investigation
where an operator needs compact proof from logs, scene state, Play Mode, and
profile-sensitive compile behavior without dumping large raw JSON payloads or
leaving the project in a mutated profile.

## Current Coverage

The current public MCP surface already supports:

- editor readiness, status, health, request recovery, and stale cleanup
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.playmode.*`
- scenario steps for status, health, project refresh, console tail, scene
  snapshot, Play Mode, compile, tests, screenshots, and project-defined hooks
- scenario result summaries and result browsing utilities
- project-refresh settle waiting
- build-config compile matrices that can validate profile-specific defines

This is enough to prove many workflows, but it is sometimes too verbose or too
manual for routine operator use.

## Implementation Status

Updated: `2026-05-15`

| Item | Status | Evidence |
| --- | --- | --- |
| `unity.scene.assert` operation | Implemented | `templates/unity-package/Editor/Operations/XUUnityLightMcpSceneAssertOperation.cs` |
| `assert_scene` scenario step | Implemented | `templates/unity-package/Editor/Helpers/XUUnityLightMcpScenarioRunner.cs` |
| MCP tool schema for scene assertion | Implemented | `templates/server_specs.py` exposes `unity_scene_assert` |
| CLI scene assertion helper | Implemented | `templates/server.py` exposes `request-scene-assert` |
| Capability/status accounting for scene assertion | Implemented | `XUUnityLightMcpCapabilityRegistry.cs` and `XUUnityLightMcpHealthProbe.cs` include `unity.scene.assert` |
| Generic profile mutation scenario template | Not implemented in public core | Still needs a public template with placeholder hook payloads |
| Consumer profile restore scenario/shortcut | Implemented in one consumer overlay | Verified through a host-local scenario and wrapper shortcut outside public `AIRoot` |
| Hardened consumer profile timing probe | Implemented in one consumer overlay | Uses target switch, settle, compile gate, `assert_scene`, Play Mode probe, restore, settle, and compile closeout |
| `project_refresh_timeout` guidance | Not implemented | Timeout message and payload still need richer recovery guidance |
| Profile mutation closeout reminder in summaries | Not implemented | Scenario summaries do not yet infer mutation/restore obligations |
| Compact console query | Not implemented | `unity.console.grep` / `console_grep` remains future work |
| Compact loading timing helper | Not implemented | Depends on compact console query |
| Scenario summary evidence hints | Not implemented | Summary still needs next-best evidence recommendations |

Validation already performed for the implemented scene assertion and consumer
profile-flow work:

- host Python test suite passed
- scenario JSON parsing passed
- shell syntax checks passed
- live MCP `request-scene-assert` passed in a Unity editor
- live MCP scenario validation passed for the hardened consumer timing probe
- live MCP restore shortcut passed and ran an Android player-script compile gate

## Current Gaps

- Console evidence is tail-oriented, not query-oriented.
- Log payloads can be token-expensive because matching text and stack traces are
  returned together.
- Scene snapshots are observational; there is no first-class pass/fail scene
  assertion primitive.
- Profile or environment mutation scenarios depend on authors remembering the
  correct settle, compile, smoke, and restore sequence.
- `project_refresh_timeout` does not currently guide the operator toward the
  next safe evidence step when the editor later appears healthy.
- Scenario summaries do not automatically warn that a profile or environment
  mutation still needs restoration or explicit closeout evidence.

## Required Core Additions

### P0: Compact Console Query

Add a query-oriented console surface:

- operation name: `unity.console.grep`
- scenario step kind: `console_grep`
- optional CLI alias: `request-console-grep`

Inputs:

- `pattern`: required string or regex
- `patternMode`: `contains` or `regex`, default `contains`
- `includeTypes`: log, warning, error, exception; default all
- `limit`: max matches, default small
- `contextLines`: neighboring console entries around each match, default `0`
- `sinceRequestId` or `sinceUtc`: optional lower bound
- `includeStackTrace`: default `false`
- `stackTraceMode`: `none`, `first_line`, `full`

Output:

- compact match count and truncation status
- matching messages with type, timestamp, and optional compact stack
- no full stack traces by default
- clear error when the query cannot be evaluated

Default behavior should favor operator readability over raw completeness. Raw
console tail remains available when compact grep is insufficient.

### P0: Scene Assertion

Add a first-class scene assertion primitive:

- operation name: `unity.scene.assert`
- scenario step kind: `assert_scene`
- optional CLI alias: `request-scene-assert`

Inputs:

- `expectedName`: optional active scene name
- `expectedPath`: optional active scene path
- `requiredRootNames`: optional list of root GameObject names
- `allowDirty`: default `true`

Output:

- `passed` or `failed`
- active scene name, path, dirty state, and root count
- missing root names when applicable

This should not replace `unity.scene.snapshot`; it should turn common snapshot
checks into an explicit contract.

### P0: Profile Mutation Scenario Template

Add a generic checked-in scenario template for profile-sensitive runtime probes:

1. capture status before mutation
2. apply a project-defined profile or environment hook
3. settle with state-aware refresh or an equivalent hook-owned settle contract
4. run a compile gate
5. run Play Mode or scenario smoke
6. collect compact evidence
7. restore the previous profile or apply an explicit target profile
8. run status and compile closeout evidence after restore

The template should not contain project-specific profile names. Consumer
projects should provide the hook name and payload through local scenario JSON or
wrapper arguments.

### P0: Refresh Timeout Guidance

Improve `project_refresh_timeout` output so it distinguishes:

- editor failure
- package-settle timeout
- compile/import/update churn timeout
- lost final accounting after lifecycle churn

When the bridge is reachable and editor status is healthy or idle after timeout,
the failure payload should include:

- `recommended_next_action`: `request_status_summary_then_compile_gate`
- a concrete recovery command template
- a note that the Unity operation may have completed even though the scenario
  refresh waiter timed out

The operator should not need to infer whether retry, status, or compile is the
next step.

### P0: Profile Mutation Closeout Reminder

Scenario summaries should detect project-defined mutation steps when the step
declares a mutation class such as:

- `build_profile`
- `environment`
- `build_target`
- `scripting_defines`
- `project_settings`

If no later restore or explicit final-profile assertion appears in the scenario,
the summary should include:

- `profile_restore_required`: `true`
- `recommended_next_action`: restore or assert final profile, then run compile
  gate

This is a summary warning, not necessarily a scenario failure. Projects may
escalate it to failure in stricter local lanes.

## P1 Additions

### Compact Loading Timing Helper

Add a convenience helper built on `console_grep` for loading and startup timing:

- accept a pattern list such as loading step names, markers, or timing suffixes
- return only matching timing messages by default
- suppress stack traces unless explicitly requested
- preserve enough timestamp/order data to reconstruct startup sequence

### Scenario Summary Evidence Hints

Improve scenario result summaries to list the smallest next evidence surface:

- compact result summary
- console grep
- scene assertion
- status summary
- final request status
- raw result JSON

This keeps raw JSON as a fallback rather than the default operator path.

## Validation Plan

Minimum proof for these additions:

- host Python tests for CLI argument parsing and summary payload shape
- Unity editor tests or scenario smoke for `console_grep` and `assert_scene`
- scenario validation tests for new step kinds
- one generic scenario template smoke with a fake project-defined mutation hook
- regression coverage that raw `unity.console.tail` and `unity.scene.snapshot`
  keep their existing behavior

## Public Boundary

Keep this design generic:

- no project-specific profile names
- no product-specific scenes
- no host-private wrapper names
- no confidential identifiers

Consumer projects can layer local scenarios and wrappers on top of these public
primitives.
