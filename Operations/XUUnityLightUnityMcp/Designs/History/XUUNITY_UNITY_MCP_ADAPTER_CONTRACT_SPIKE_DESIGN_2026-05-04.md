# XUUnity Unity MCP Adapter Contract Spike Design

Date: `2026-05-04`  
Status: `design for first implementation spike`  
Depends on:
- `historical host-local design source: XUUNITY_UNITY_MCP_EVALUATION_AND_ADAPTER_DESIGN_2026-05-04.md`
- `historical host-local candidate shortlist`
- `historical host-local hands-on harness report`

## Decision

For the first real `xuunity` Unity MCP integration spike:
- primary backend target: `IvanMurzak/Unity-MCP`
- active fallback/comparison backend: `CoplayDev/unity-mcp`

This document defines the stable `xuunity` adapter contract that should sit above any concrete backend.

## Goal

Create one backend-neutral Unity-aware contract that `xuunity` can rely on for the first valuable MCP workflows:
- readiness and status
- console inspection
- scene snapshot
- edit-mode test execution

The first spike should prove that these workflows can be exposed without coupling `xuunity` task logic to raw backend tool names or backend-specific payload quirks.

## Non-Goals

This spike should not try to solve everything:
- no broad scene mutation contract
- no asset-write contract
- no play-mode automation contract
- no custom-tool registration branch yet
- no production `ConsumerProject` rollout by default

Those can come after the validation-first adapter slice is stable.

## Contract Shape

There are two layers:

1. `xuunity` stable adapter operations
2. backend-specific execution mapping

`xuunity` should only reason about layer 1.
Layer 2 is allowed to change as backends evolve.

## Adapter Principles

### Validation honesty
- Never report shell compile or source inspection as Unity MCP validation.
- If the backend is unavailable, keep the validation gap explicit.

### Explicit project targeting
- Every operation must resolve to one concrete Unity project root.
- If multiple candidate projects exist, fail with `project_ambiguous`.

### Structured evidence first
- Return normalized structured payloads first.
- Raw backend responses may be attached as debug evidence, but must not be the primary contract.

### Narrow scope
- The first contract should optimize for reliability, not breadth.
- A smaller trustworthy adapter is better than a broad flaky one.

### Backend replaceability
- No stable `xuunity` operation name may embed backend naming such as `run-tool`, `console-get-logs`, or `manage_scene`.

## Stable Adapter Operations

The first spike should implement these four stable operations plus one internal control operation.

### Public stable operations

1. `unity.status`
2. `unity.console.tail`
3. `unity.scene.snapshot`
4. `unity.tests.run_editmode`

### Internal control operation

5. `unity.ensure_ready`

`unity.ensure_ready` is operationally required but should remain an adapter-internal control path rather than a user-facing conceptual tool.

## Canonical Contract

```yaml
adapter_contract_version: 1
scope: xuunity_unity_mcp_first_spike

public_operations:
  - name: unity.status
    purpose: Return normalized Unity editor and MCP readiness state for one project.
    input:
      project_root: required
    output:
      project_root: string
      backend_id: string
      editor_running: boolean
      mcp_reachable: boolean
      is_compiling: boolean|null
      is_playing: boolean|null
      transport: string|null
      validation_evidence: enum[unity_mcp, none]
      warnings: string[]

  - name: unity.console.tail
    purpose: Return recent Unity console items in normalized form.
    input:
      project_root: required
      limit: integer default=50
      include_types: array default=[error, warning, log]
    output:
      project_root: string
      backend_id: string
      items:
        - type: enum[error, warning, log, exception, unknown]
          message: string
          timestamp: string|null
          stack_trace: string|null
      truncated: boolean
      validation_evidence: enum[unity_mcp]
      warnings: string[]

  - name: unity.scene.snapshot
    purpose: Return a lightweight normalized snapshot of the currently open scene state.
    input:
      project_root: required
    output:
      project_root: string
      backend_id: string
      active_scene:
        name: string|null
        path: string|null
        is_dirty: boolean|null
        root_count: integer|null
      root_objects:
        - name: string
      validation_evidence: enum[unity_mcp]
      warnings: string[]

  - name: unity.tests.run_editmode
    purpose: Run Unity edit-mode tests and return normalized result accounting.
    input:
      project_root: required
      filters: object|null
      timeout_ms: integer default=600000
    output:
      project_root: string
      backend_id: string
      status: enum[passed, failed, no_tests, infrastructure_error]
      total: integer|null
      passed: integer|null
      failed: integer|null
      skipped: integer|null
      duration_seconds: number|null
      failures:
        - name: string
          message: string|null
      validation_evidence: enum[unity_mcp]
      warnings: string[]

internal_operations:
  - name: unity.ensure_ready
    purpose: Make sure the selected backend for one project is ready for Unity-aware operations.
    input:
      project_root: required
    output:
      ready: boolean
      backend_id: string
      actions_taken: string[]
      warnings: string[]
```

## Error Taxonomy

Every backend response should be normalized into one of these adapter-level error classes when the operation cannot complete:

- `project_not_found`
- `project_ambiguous`
- `backend_not_installed`
- `backend_not_configured`
- `editor_not_running`
- `mcp_unreachable`
- `auth_failed`
- `tool_unsupported`
- `compile_broken`
- `tests_failed`
- `backend_payload_invalid`
- `operation_timeout`
- `unknown_backend_error`

Important rule:
- `tests_failed` is not an infrastructure failure.
- `compile_broken` is not the same as `mcp_unreachable`.
- `no_tests` must not be normalized to `passed`.

## Evidence Labels

The adapter should preserve validation honesty with explicit evidence labels.

### Allowed labels for this spike
- `unity_mcp`
- `none`

### Rules
- `unity.status`, `unity.console.tail`, `unity.scene.snapshot`, and `unity.tests.run_editmode` may label their outputs as `unity_mcp` only when the backend actually returned the data through the Unity MCP path.
- If a future fallback uses shell compile or static inspection, the output must not carry `unity_mcp`.

## Backend Mapping: IvanMurzak

This backend is the first spike target because it gave the strongest end-to-end validation path in the hands-on harness.

### Backend ID

`ivanmurzak.unity_mcp`

### Backend assumptions

- CLI available from local build or installed package
- Unity plugin installed into the target project
- project config pinned to local custom mode
- local server may be started by the plugin itself

### Operation mapping

#### `unity.ensure_ready`

Primary path:
1. verify project root
2. verify CLI availability
3. verify plugin presence or install state
4. verify local config exists and points to deterministic local host
5. if editor is not running, open the project through the backend CLI
6. wait for ready
7. return normalized readiness result

Concrete backend calls:
- `unity-mcp-cli install-plugin <project>` when plugin missing
- `unity-mcp-cli bootstrap-local <project> --url <resolved_url> --token <token>` when local config missing or stale
- `unity-mcp-cli open <project> --url <resolved_url> --token <token> --auth none --keep-connected --transport streamableHttp --start-server true`
- `unity-mcp-cli wait-for-ready <project>`

#### `unity.status`

Primary path:
- `unity-mcp-cli status <project>`
- enrich with `unity-mcp-cli run-tool editor-application-get-state <project>`

Normalization rules:
- `editor_running` comes from `status`
- `mcp_reachable` comes from `status`
- `is_compiling` and `is_playing` come from `editor-application-get-state`

#### `unity.console.tail`

Primary path:
- `unity-mcp-cli run-tool console-get-logs <project>`

Normalization rules:
- map backend `LogType` values into adapter `type`
- preserve raw stack traces
- if the backend does not support count limits natively, truncate in the adapter and mark `truncated=true` when needed

#### `unity.scene.snapshot`

Primary path:
- `unity-mcp-cli run-tool scene-list-opened <project>`
- `unity-mcp-cli run-tool scene-get-data <project>`

Normalization rules:
- `active_scene` comes from the first loaded/open scene returned by `scene-list-opened`
- `root_count` comes from `scene-get-data`
- because current backend payload did not expose root names cleanly in the harness, `root_objects` may be empty in v1
- when `root_objects` is empty but `root_count > 0`, emit a warning:
  - `backend did not provide root object names`

#### `unity.tests.run_editmode`

Primary path:
- `unity-mcp-cli run-tool tests-run <project> --input '{"testMode":"EditMode"}'`

Normalization rules:
- backend `Passed` -> adapter `passed`
- backend `Failed` -> adapter `failed`
- backend explicit zero tests -> adapter `no_tests`
- backend transport or invocation failure -> adapter `infrastructure_error`

## Backend Mapping: Coplay Fallback Stub

Fallback backend ID:

`coplaydev.unity_mcp`

This branch should remain a comparison adapter only until the test-result discrepancy is resolved.

### Initial mapping intent

- `unity.status` -> `unity-mcp status`
- `unity.console.tail` -> `raw read_console`
- `unity.scene.snapshot` -> `raw manage_scene`
- `unity.tests.run_editmode` -> `raw run_tests` + `raw get_test_job`

### Current blocker

The hands-on harness observed a material mismatch:
- job succeeded
- summary still returned zero tests on the explicit shared fixture

Until that is resolved, `coplaydev.unity_mcp` should not be the first validation backend for `xuunity`.

## Project Targeting Contract

For monorepo use, the adapter must not guess loosely.

Resolution order:
1. explicit referenced source path
2. resolved Unity project root from repo routing
3. explicit project argument from the operator

Failure rules:
- if no project root can be resolved, fail with `project_not_found`
- if more than one project root matches, fail with `project_ambiguous`

## First Spike Execution Plan

### Phase 0: host-local proof wrapper

Implement a host-local wrapper layer that can run the four stable operations against one selected backend without changing public `AIRoot` prompts yet.

Expected output:
- one operator-facing wrapper surface for the four operations
- one backend mapping for `IvanMurzak`
- one fallback stub mapping for `Coplay`

### Phase 1: normalized output hardening

Add:
- payload normalization
- error normalization
- evidence labels
- warning propagation

Exit condition:
- the same backend call shape produces the same adapter output shape across repeated runs

### Phase 2: `xuunity` workflow integration

Only after Phase 1 is stable:
- wire the adapter into `xuunity` validation-path selection
- prefer MCP-backed Unity-aware validation when the active project/router allows it
- keep the validation gap explicit when MCP is unavailable

## Recommended File Layout For The Future Implementation

This is a suggested host-local shape, not a hard requirement:

```text
host-local UnityMcpAdapter prototype path
  README.md
  contract_v1.md
  backends/
    ivanmurzak.md
    coplay.md
  logs/
  examples/
```

If the wrapper evolves into executable utilities, keep the operational entrypoints host-local first.
Do not promote them into public `AIRoot` until the backend contract is proven stable across real projects.

## Acceptance Criteria For The First Spike

The spike is successful only if all of the following are true:

1. `unity.ensure_ready` can bring one scratch or selected project to a ready state through `IvanMurzak`
2. `unity.status` returns normalized editor + MCP state
3. `unity.console.tail` returns normalized console items
4. `unity.scene.snapshot` returns at least scene metadata and root count
5. `unity.tests.run_editmode` returns correct pass/fail/no-tests accounting
6. failures are classified into adapter-level error classes instead of leaking only backend raw errors
7. final outputs clearly say when the result is true Unity MCP evidence versus no Unity validation

## Practical Next Move

After this design, the next implementation step should not be another broad comparison pass.

It should be one narrow executable spike:
- implement the four stable operations for `IvanMurzak`
- prove normalized outputs on one scratch project
- then retry the same stable contract on `ConsumerProject` only when the project-level MCP readiness path is intentionally enabled
