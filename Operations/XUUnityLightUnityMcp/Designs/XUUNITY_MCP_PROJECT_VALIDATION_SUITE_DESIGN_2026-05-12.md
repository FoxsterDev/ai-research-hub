# XUUnity MCP Project Validation Suite Design

Date: `2026-05-12`
Status: `active public backlog/spec design`
Scope: public-safe validation-suite model for `XUUnityLightUnityMcp`

Split from a host-local mixed design on `2026-05-15`.
Project-specific examples and consumer evidence belong outside public `AIRoot`.

## Implementation Status

This document is a public design and backlog spec, not a currently implemented
runtime contract.

Implemented MCP building blocks that this design can compose with:

- `ensure-ready`
- `unity.scenario.run`
- scenario validation and result inspection
- compile/test scenario primitives
- `project_defined_hook`
- `assert_scene`
- status, health, console, screenshot, and scene-snapshot evidence primitives

Not implemented as first-class public suite tooling yet:

- `validation-suite-validate`
- `validation-suite-compile`
- `validation-suite-run`
- `validation-suite-explain`
- committed public schema for `xuunity.validation-suite.v1`
- committed public schema for `xuunity.validation-plan.v1`
- generic suite compiler from YAML to host commands and scenario JSON
- generic project-action catalog validation

Until those pieces exist, use this document as the target shape for future
suite tooling and as a checklist for manual/project-local scenario work.

## Goal

Make complex Unity validation flows easy for humans to author and safe for AI
agents to execute.

The target workflow is:

1. a human describes a validation suite in a project-local file
2. a compiler validates the file against known MCP and project capabilities
3. the compiler emits deterministic host/MCP instructions
4. the runner executes the compiled plan and records structured evidence
5. missing Unity/MCP/project commands are reported as gaps instead of being
   hidden behind ad hoc chat instructions

Suites should support ordinary post-change validation and richer project E2E
flows such as:

- switch to a named environment or profile
- clear local state
- enter Play Mode
- reach a target scene or state
- assert expected UI, logs, state, screenshot, or reward outcome

No real credentials or secret-bearing URLs may be stored in committed suite
files. Secret inputs must come from local env, keychain, or another redacted
host-local source.

## Design Principles

- Project hooks must not become a hidden test framework.
- Project-contract validation and user-like E2E validation are different proof
  classes and must be labeled separately.
- Natural-language suite authoring is draft-only; generated plans must not run
  until validated.
- Missing capability reporting is a first-class output, not a failure to hide.
- All mutations need explicit cleanup or idempotency rules.

## Layered Model

### Layer 1: Human Suite Spec

Project-local, committed, readable by humans.

Recommended path:

- `<HostOutput>/Projects/<Project>/Operations/XUUnityLightUnityMcp/suites/*.yaml`

This layer describes intent, lanes, and named project actions without binding
every detail to current MCP JSON.

Example:

```yaml
schemaVersion: xuunity.validation-suite.v1
project: ExampleProject
suite: post_change_core
description: Compile and smoke the default post-change project path.
validationMode: project_action_contract

inputs:
  environment:
    default: dev
    allowed: [dev, staging, production_like]

lanes:
  - id: readiness
    kind: mcp.ensure_ready
    openEditor: true

  - id: quick_compile
    kind: mcp.compile
    target: Android
    profile: DevBuild

  - id: matrix_compile
    kind: mcp.build_config_compile_matrix
    targets: [Android, iOS]

  - id: editmode
    kind: mcp.tests.editmode
    assemblies: [EditMode.Tests]

  - id: playmode
    kind: mcp.tests.playmode
    assemblies: [PlayMode.Tests]

  - id: lobby_smoke
    kind: mcp.unity_scenario
    scenario: lobby_smoke

scenarios:
  lobby_smoke:
    steps:
      - action: project.set_environment
        environment: ${inputs.environment}
      - action: project.clear_local_data
        scopes: [player_prefs, local_cache]
      - action: unity.playmode.enter
      - action: project.wait_for_lobby
        timeoutSeconds: 90
      - action: project.assert_lobby_state
      - action: unity.game_view.screenshot
        fileName: lobby_smoke.png
```

For a user-like E2E flow, the mode must be explicit:

```yaml
schemaVersion: xuunity.validation-suite.v1
project: ExampleProject
suite: lobby_e2e
validationMode: user_like_interaction
requiresApproval: true
```

If the compiler cannot map this suite to real UI-driving or user-visible
evidence, it should produce a gap report and block execution unless the suite is
downgraded intentionally to `project_action_contract`.

### Layer 2: Compiled Execution Plan

Generated, deterministic, not hand-edited.

Recommended path for persisted run artifacts:

- `<Project>/Library/XUUnityLightMcp/validation_suites/compiled/`

The compiled plan expands suite steps into concrete commands:

- host command invocations
- generated Unity scenario JSON files
- expected capabilities
- timeouts
- evidence files
- cleanup obligations
- explicit validation gaps

Example compiled shape:

```json
{
  "schemaVersion": "xuunity.validation-plan.v1",
  "projectRoot": "ExampleProject",
  "suite": "post_change_core",
  "requiredCapabilities": [
    "mcp.ensure_ready",
    "mcp.build_config_compile_matrix",
    "mcp.tests.editmode",
    "mcp.tests.playmode",
    "project.set_environment",
    "project.clear_local_data",
    "project.wait_for_lobby"
  ],
  "steps": [
    {
      "id": "readiness",
      "runner": "host_cli",
      "command": "ensure-ready"
    },
    {
      "id": "matrix_compile",
      "runner": "host_cli",
      "command": "request-build-config-compile-matrix"
    },
    {
      "id": "lobby_smoke",
      "runner": "unity_scenario",
      "scenarioFile": "generated/lobby_smoke.json"
    }
  ],
  "validationGaps": []
}
```

If capabilities are missing, the compiler may still write a planning artifact,
but the plan must be non-runnable:

```json
{
  "schemaVersion": "xuunity.validation-plan.v1",
  "suite": "lobby_e2e",
  "runnable": false,
  "missingCapabilities": [
    {
      "id": "project.wait_for_lobby",
      "kind": "project_action",
      "owner": "ExampleProject",
      "neededByStep": "wait_for_lobby",
      "recommendedImplementation": "Add the action to the project action catalog and implement a narrow editor-only hook."
    },
    {
      "id": "unity.ui.click",
      "kind": "mcp_operation",
      "owner": "AIRoot/Operations/XUUnityLightUnityMcp",
      "neededByStep": "claim_reward",
      "recommendedImplementation": "Add a UI action/query primitive or change the suite to project_action_contract."
    }
  ],
  "validationGaps": [
    "user_like_interaction cannot be proven without UI-driving or equivalent user-visible evidence"
  ]
}
```

The runner must refuse to execute non-runnable plans.

### Layer 3: Unity Scenario JSON

Generated from the suite plan when the step needs ordered editor-integrated
runtime evidence.

This layer should continue to use the existing `unity.scenario.run` contract.
The compiler maps high-level actions to primitive steps where possible:

- `unity.playmode.enter` -> `playmode_set enter`
- `unity.playmode.exit` -> `playmode_set exit`
- `unity.game_view.screenshot` -> `game_view_screenshot`
- `unity.scene.assert` -> `assert_scene`
- project actions -> `project_defined_hook` or future typed project action

### Layer 4: Project Action Catalog

Every project that wants rich E2E validation should expose a typed action
catalog.

Recommended path:

- `<HostOutput>/Projects/<Project>/Operations/XUUnityLightUnityMcp/project_actions.yaml`

Example:

```yaml
schemaVersion: xuunity.project-actions.v1
project: ExampleProject
hookName: example.project_actions

actions:
  project.set_environment:
    payload:
      environment: enum[dev, staging, production_like]
    mutates:
      - local runtime config
    cleanup: restore_environment
    validationModes: [project_action_contract]

  project.clear_local_data:
    payload:
      scopes: list[player_prefs, local_cache, auth_session]
    mutates:
      - PlayerPrefs
      - local cache files
    cleanup: clear_or_restore_named_scopes
    validationModes: [project_action_contract, user_like_interaction]

  project.wait_for_lobby:
    payload:
      timeoutSeconds: number
    evidence:
      - scene_snapshot
      - console_tail
      - screenshot
    validationModes: [project_action_contract, user_like_interaction]
```

The Unity project implements the catalog with narrow editor-only hooks.
The public MCP package owns schema validation, runner behavior, and evidence
contracts; the consumer project owns project-specific actions and invariants.

## Missing Capability Workflow

Capability sources:

- public MCP capabilities exposed by the package
- host commands exposed by the wrapper
- project action catalogs
- known project scenario files

Gap categories:

- `missing_mcp_operation`
- `missing_host_command`
- `missing_project_action`
- `missing_evidence_channel`
- `unsafe_secret_source`
- `unsupported_validation_mode`
- `ambiguous_project_action`
- `missing_cleanup_contract`

Compiler behavior:

- validate suite schema
- resolve project root and action catalog
- resolve required MCP capabilities
- mark every unavailable action as a typed gap
- block runnable output when required proof is missing
- write a deterministic gap report that can become implementation backlog

Runner behavior:

- accept only compiled/approved suite plans
- reject raw natural language and unvalidated draft YAML
- preserve evidence bundles even on failure
- fail closed on unsafe secret input, unresolved project actions, or missing
  cleanup for destructive state changes

## Evidence Bundle

Each suite run should produce:

- normalized suite result JSON
- generated scenario JSON files
- command transcript with redacted env/secrets
- Unity status summaries
- console tail excerpts
- compile/test summaries
- screenshots or scene assertions when requested
- gap report when not fully runnable

Evidence should be durable enough for a reviewer to answer:

- what project and suite ran
- which MCP and project capabilities were required
- which proof class was claimed
- what mutated state
- what cleanup ran
- what failed and whether it failed before or during execution

## Required MVP

Slice 1: host suite compiler

- parse suite YAML
- validate lane kinds
- resolve public MCP capabilities
- emit compiled plan or gap report

Slice 2: project action catalog

- parse `project_actions.yaml`
- validate action names, payload shape, mutation list, cleanup, evidence, and
  validation modes
- map typed project actions to existing `project_defined_hook` execution

Slice 3: E2E flow actions

- keep project-specific E2E work behind typed project actions first
- add generic UI primitives only after repeated projects need the same capability

Slice 4: AI natural-language compiler

- generate draft suite YAML and explanation only
- require human approval before validation/run

## Recommended Path

Start with host suite specs and compilation, not generic UI automation.

Reasons:

- compile/test/smoke orchestration is already valuable
- current MCP primitives already cover much of the lane
- E2E actions are project-specific and safer behind typed project hooks
- gap reporting will show which generic MCP operations are actually worth adding

The first checked-in suite for a consumer project should normally compile to:

1. `ensure-ready`
2. quick target/profile compile or matrix compile
3. focused EditMode tests when configured
4. focused PlayMode tests when configured
5. generated acceptance/contract Unity scenario
6. `restore-editor-state` when the host opened Unity
