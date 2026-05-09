# XUUnity Light Unity MCP PlayMode And Player Tests Design Plan

Date: `2026-05-08`
Status: `design plan`
Scope: `public MCP operation and batch-lane expansion`

## Summary

Current `XUUnity Light Unity MCP` supports:

- `unity.tests.run_editmode`
- `unity.playmode.state`
- `unity.playmode.set`
- `batch-editmode-tests`
- `batch-build-player`

It does not currently support:

- PlayMode test execution in editor through MCP
- closed-editor batch PlayMode test execution
- player test execution on desktop or mobile targets

The correct expansion path is to split the problem into two architectures:

1. **PlayMode tests in editor**
   - implemented as a new Unity bridge operation inside the current editor-only package
2. **Player tests on built targets**
   - implemented as host-driven batch orchestration through Unity CLI and platform runners
   - not as a runtime bridge extension inside the base package

This split matches the current package boundary:

- `AIRoot/Operations/XUUnityLightUnityMcp/README.md` states `editor-only Unity footprint`
- the same README also states `no runtime/player support in the base package`

## Starting Point For A Live Consumer Project

Verified against one live Unity consumer project:

- editor version:
  - `ProjectSettings/ProjectVersion.txt` -> `6000.0.58f2`
- current project manifest:
  - `Packages/manifest.json` -> `com.unity.test-framework: 1.5.1`
- current MCP package manifest:
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/package.json` -> `com.unity.test-framework: 1.5.1`

## Verified Current Surface

Current code confirms:

- capability registry exposes `editmode_tests`, `compile_player_scripts`, and `playmode_control`
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Core/XUUnityLightMcpCapabilityRegistry.cs`
- operation registry exposes:
  - `unity.tests.run_editmode`
  - `unity.playmode.state`
  - `unity.playmode.set`
  - `unity.compile.player_scripts`
  - `unity.compile.matrix`
  - `unity.scenario.*`
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Core/XUUnityLightMcpOperationRegistry.cs`
- host CLI exposes:
  - `request-editmode-tests`
  - `batch-editmode-tests`
  - `batch-build-player`
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py`
- scenario runner supports:
  - `playmode_set`
  - `tests_run_editmode`
  - no `tests_run_playmode`
  - `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Helpers/XUUnityLightMcpScenarioRunner.cs`

Unity documentation and API surface confirm:

- `TestRunnerApi` supports programmatic `TestMode.PlayMode`
- callbacks must be re-registered after domain reload
- command-line test execution supports:
  - `testPlatform=PlayMode`
  - `testPlatform=<BuildTarget>`
  - `testFilter`
  - `testCategory`
  - `assemblyNames`
  - `playerHeartbeatTimeout`
  - `buildPlayerPath`
  - `testSettingsFile`

Sources:

- `TestRunnerApi`
  - https://docs.unity3d.com/kr/Packages/com.unity.test-framework%402.0/api/UnityEditor.TestTools.TestRunner.Api.TestRunnerApi.html
- test framework command-line arguments
  - https://docs.unity3d.com/kr/Packages/com.unity.test-framework%402.0/manual/reference-command-line.html
- Unity Test Runner manual
  - https://docs.unity3d.com/kr/2018.3/Manual/PlaymodeTestFramework.html

Additional package-version evidence:

- `com.unity.test-framework@1.5` changelog
  - https://docs.unity3d.com/Packages/com.unity.test-framework@1.5/changelog/CHANGELOG.html
- Unity `6000.0` package page says core packages are fixed to a single version matching the editor version
  - https://docs.unity3d.com/kr/6000.0/Manual/com.unity.test-framework.html
- older Unity package pages document alternative compatible lines such as `1.3`, `1.4`, and `2.0.1-*`
  - example: https://docs.unity3d.com/ja/2023.2/Manual/com.unity.test-framework.html

## Goals

Add support for:

1. PlayMode tests in editor through MCP
2. closed-editor PlayMode test execution
3. desktop player test execution through batch lanes
4. future mobile player test support without breaking the editor-only base package contract

## Phase 0: Package Version Research And Stability Sweep

Before implementing PlayMode and player-test support, add a mandatory research and regression gate for `com.unity.test-framework`.

### Why This Is Required

Current state is inconsistent enough that version choice must be proven, not assumed:

- the active project uses `1.5.1`
- current Unity `6000.0` docs say core packages are fixed to the editor-matching version
- package docs and changelogs also expose a `2.0.1-*` line with CLI and runner behavior details that are relevant to this design

That means the implementation plan needs an explicit step to:

1. review release notes from the current version upward
2. identify the realistic candidate set for `6000.0.58f2`
3. run the candidate versions through automated MCP and project regression
4. choose the most stable version that actually behaves well in this editor and project

### Mandatory Release-Notes Review

Do not upgrade blindly from `1.5.1` to a `2.0.1-*` line.

The design plan must include a review of:

- `1.5.1` and `1.5.0`
- `1.4.x` changes that materially affect batchmode, PlayMode, or player runs
- `2.0.0` and `2.0.1`

Important changelog items already visible from official docs:

- `1.5.1`
  - package moved into Unity source as embedded package
  - retry/repeat domain-reload fixes
  - duplicate `TestFinished` fix on domain-reload runs
- `1.4.5`
  - batchmode test runs could hang forever on `WaitForEndOfFrame`, fixed there
  - PlayMode cancel restore fixes
  - domain-reload memory leak fix
- `1.4.2`
  - PlayMode results after first run were fixed
  - some batchmode runs without PlayMode tests could emit `No callbacks received.`
- `1.3.2`
  - batchmode `RunFinished` callback-before-quit fix
- `2.0.0`
  - public cancel API
  - save-result API
  - playmode test support extensions around platform build configurations
- `2.0.1`
  - `RequiresPlayMode` behavior changes
  - performance/filtering changes
  - platform and player-test related fixes

These are directly relevant to the planned MCP work. In particular:

- batchmode completion behavior
- PlayMode result correctness
- domain reload behavior
- command-line and player-run semantics

### Candidate Version Set

The exact candidate set must be confirmed on the active `6000.0.58f2` editor, but the initial sweep should start from:

- baseline:
  - `1.5.1`
- downgrade sanity candidates only if they are still accepted by the editor:
  - `1.4.5`
  - `1.4.4`
- upgrade / alternative line candidates only if the editor resolves them cleanly:
  - `2.0.1-exp.1`
  - `2.0.1-exp.2`
  - `2.0.1-pre.12`
  - `2.0.1-pre.18`

The sweep should prune candidates automatically if:

- Unity Package Manager refuses the version
- the package cannot resolve
- compile breaks immediately after package restore

### New Harness Requirement

Add a host-driven regression harness that can take a `com.unity.test-framework` version, apply it to the project, re-resolve packages, and run a fixed validation suite.

Recommended new command:

- `batch-test-framework-version-regression`

Suggested inputs:

- `projectRoot`
- `version`
- `versionFile` or `versions[]`
- `unityApp`
- `resultFile`
- `batchLogPath`
- `restoreOriginalVersion=true`

### Required Harness Behavior

For each candidate version, the harness should:

1. capture the original package version and lock state
2. patch `Packages/manifest.json`
3. invalidate or remove the relevant lock entry so Unity re-resolves honestly
4. trigger package resolution and project refresh
5. run a fixed regression contract
6. persist structured results
7. restore the original version at the end unless explicitly told not to

### Required Regression Contract For Each Candidate

At minimum, each tested version should run:

1. package resolve success
2. `unity.health.probe`
3. `unity.project.refresh`
4. compile regression:
   - `unity.compile.player_scripts` for at least one target used in the project
5. test regression:
   - focused EditMode regression assembly
   - at least one filtered short-name test run
   - broader EditMode suite already used for MCP validation
6. MCP behavior regression:
   - direct `request-editmode-tests`
   - `batch-editmode-tests`
   - filter normalization path
7. if PlayMode test support has been implemented by then:
   - `unity.tests.run_playmode`
   - `batch-playmode-tests`

### Candidate Evaluation Criteria

Choose the version that scores best on:

1. package resolve reliability
2. compile stability
3. EditMode test correctness
4. batchmode completion reliability
5. no lifecycle regressions in current MCP flows
6. PlayMode correctness once PlayMode support exists
7. absence of known critical regressions from release notes that affect MCP goals

### Expected Outcome

The goal is not "latest version".

The goal is:

- the most stable `com.unity.test-framework` version available today for `Unity 6000.0.58f2`
- validated empirically on the real project
- with MCP regression evidence attached

Only after that selection should PlayMode/player-test implementation be considered version-anchored.

## Non-Goals

Not part of the first milestone:

- Android device orchestration
- iOS simulator/device orchestration
- runtime bridge embedded into tested player builds
- cancellation for PlayMode test runs
- a single unified abstraction that pretends editor PlayMode tests and player tests are the same operational surface

## Architecture Decision

### A. Interactive PlayMode Tests

Add a new bridge operation:

- `unity.tests.run_playmode`

This should mirror `unity.tests.run_editmode` where practical, but it cannot be implemented as a copy-paste variant because PlayMode test execution crosses domain reload and playmode transitions.

### B. Batch PlayMode Tests

Add a new host-side batch lane:

- `batch-playmode-tests`

This should use Unity command-line test execution with:

- `-runTests`
- `-testPlatform PlayMode`
- result-file parsing back into normalized MCP-style JSON

This is a better first batch implementation than building a custom batch `TestRunnerApi` runner because Unity already owns the playmode lifecycle in this lane.

### C. Player Tests

Add a separate host-side batch lane:

- `batch-player-tests`

This should also use Unity command-line test execution, but with:

- `-testPlatform <BuildTarget>`

Player tests should stay host-driven. They should not extend the current editor bridge into runtime transport.

## Rollout Plan

## Phase 1: Interactive `unity.tests.run_playmode`

### Deliverables

- new capability: `playmode_tests`
- new bridge operation: `unity.tests.run_playmode`
- new MCP tool: `unity_tests_run_playmode`
- new scenario step: `tests_run_playmode`

### Required Code Areas

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Core/XUUnityLightMcpCapabilityRegistry.cs`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Core/XUUnityLightMcpOperationRegistry.cs`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Core/XUUnityLightMcpModels.cs`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Operations/`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Helpers/XUUnityLightMcpScenarioRunner.cs`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/server_specs.py`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py`

### Key Design Constraint

PlayMode test runs must survive:

- script domain reload
- playmode transition
- callback re-registration

The current editmode runner relies on static in-memory state:

- `XUUnityLightMcpEditModeTestRunner`
- `XUUnityLightMcpEditModeCallbacks`

That shape is insufficient for PlayMode tests.

### Required Internal Refactor

Before adding `unity.tests.run_playmode`, extract a shared persistent test-run state layer.

Recommended new helper:

- `Editor/Helpers/XUUnityLightMcpTestRunState.cs`

Responsibilities:

- persist active test run metadata under `Library/XUUnityLightMcp/...`
- track:
  - `request_id`
  - `test_mode`
  - `started_at_utc`
  - normalized filter summary
  - completion state
  - response handoff state
- restore state on `[InitializeOnLoad]`
- support callback re-registration after reload

### Operation Contract

Input shape should match EditMode tests:

- `projectRoot`
- `testNames[]`
- `groupNames[]`
- `categoryNames[]`
- `assemblyNames[]`
- `timeoutMs`

Behavior:

- reject when Unity is compiling
- reject when compilation has failed
- reject when open scenes are dirty
- reject when another test run is active
- require current playmode state to be `edit` before starting
- normalize short test names exactly as EditMode does now

### Result Shape

Add a new normalized payload matching the current accounting style:

- `status`
- `total`
- `passed`
- `failed`
- `skipped`
- `failures[]`
- `started_at_utc`
- `completed_at_utc`
- `duration_seconds`
- `validation_evidence`
- `completion_basis`
- `playmode_state_after_settle`

### Special Rule

Do not promise cancellation in v1.

Unity documentation for `TestRunnerApi` explicitly notes that `CancelAllTestRuns` and `CancelTestRun` currently support EditMode tests only.

## Phase 2: `tests_run_playmode` Scenario Step

### Deliverables

- new scenario step kind: `tests_run_playmode`
- validation for the new step in schema and runner
- scenario execution payload normalized like other steps

### Required Code Areas

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/server_specs.py`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package/Editor/Helpers/XUUnityLightMcpScenarioRunner.cs`

### Notes

This should reuse the same filter model as `tests_run_editmode`.

Do not add player-test scenario steps in this phase.

## Phase 3: Closed-Editor `batch-playmode-tests`

### Deliverables

- host command: `batch-playmode-tests`
- normalized result JSON artifact
- NUnit XML capture
- batch summary artifact

### Required Code Areas

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py`
- possibly new result-normalization helpers in the host templates
- `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
- smoke docs if added

### Execution Model

Use Unity CLI, not custom `TestRunnerApi` batch plumbing.

Recommended command ingredients:

- `-runTests`
- `-testPlatform PlayMode`
- `-testResults <xml>`
- `-testFilter <...>` when test-name filtering is used
- `-testCategory <...>` when category filtering is used
- `-assemblyNames <...>` when assembly filtering is used

### Why This Is Preferred

- Unity owns lifecycle and test-platform semantics
- less custom code around playmode transitions
- easier parity with future player-test lane
- better fit for closed-editor deterministic runs

## Phase 4: Desktop `batch-player-tests`

### Deliverables

- host command: `batch-player-tests`
- support at minimum:
  - `StandaloneOSX`
  - `StandaloneWindows64`
- normalized player-test result JSON artifact
- NUnit XML capture
- batch summary artifact

### Required Code Areas

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py`
- host-side result normalization helpers
- `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
- optional new report or operator doc for desktop requirements

### Execution Model

Use Unity CLI player-test support:

- `-runTests`
- `-testPlatform <BuildTarget>`
- `-testResults <xml>`
- `-buildPlayerPath <path>`
- `-playerHeartbeatTimeout <seconds>`
- `-testSettingsFile <path>` when needed

### Why Desktop First

- same-host launch is tractable
- no adb, simulator, signing, or xcodebuild orchestration
- gives a real player-test lane before mobile expansion

## Phase 5: Mobile Player Tests

### Android

Requires at least:

- device/emulator selection
- install/uninstall policy
- launch policy
- result wait and timeout policy
- `logcat` capture
- APK/AAB and architecture options

### iOS

Requires at least:

- simulator versus device split
- signing/provisioning policy
- `xcodebuild` or equivalent orchestration
- deployment and result collection policy

### Recommendation

Do not include Android and iOS player-test orchestration in the first production milestone.

Treat mobile player tests as a separate design and delivery milestone after:

- interactive PlayMode tests
- batch PlayMode tests
- desktop player tests

## API And Tooling Additions

### New MCP Tool: `unity_tests_run_playmode`

Input:

- `projectRoot`
- `testNames[]`
- `groupNames[]`
- `categoryNames[]`
- `assemblyNames[]`
- `timeoutMs`

### New Host Command: `batch-playmode-tests`

Input:

- `projectRoot`
- `testName`
- `groupName`
- `categoryName`
- `assemblyName`
- `unityApp`
- `batchLogPath`
- `resultFile`

### New Host Command: `batch-player-tests`

Input:

- `projectRoot`
- `buildTarget`
- `testFilter`
- `categoryName`
- `assemblyName`
- `buildPlayerPath`
- `playerHeartbeatTimeoutSeconds`
- `testSettingsFile`
- `unityApp`
- `batchLogPath`
- `resultFile`

## File-By-File Work Items

## Interactive PlayMode Tests

1. `templates/unity-package/Editor/Core/XUUnityLightMcpCapabilityRegistry.cs`
   - add `playmode_tests`
   - map `unity.tests.run_playmode`

2. `templates/unity-package/Editor/Core/XUUnityLightMcpOperationRegistry.cs`
   - register `XUUnityLightMcpPlayModeTestsOperation`

3. `templates/unity-package/Editor/Core/XUUnityLightMcpModels.cs`
   - add args and payload models for PlayMode tests
   - add persisted test-run-state model if needed

4. `templates/unity-package/Editor/Helpers/`
   - add persistent test-run-state helper
   - optionally extract shared test filter logic and shared callback aggregation

5. `templates/unity-package/Editor/Operations/`
   - add `XUUnityLightMcpPlayModeTestsOperation.cs`
   - consider refactoring current EditMode test runner to reuse shared test-run infrastructure

6. `templates/server_specs.py`
   - add tool schema for `unity_tests_run_playmode`
   - add lifecycle policy for `unity.tests.run_playmode`
   - add scenario schema step `tests_run_playmode`

7. `templates/server.py`
   - add bridge invocation and normalization for `unity.tests.run_playmode`
   - add command path if a direct request helper is desired

8. `templates/unity-package/Editor/Helpers/XUUnityLightMcpScenarioRunner.cs`
   - validate and execute `tests_run_playmode`

## Batch PlayMode Tests

1. `templates/server.py`
   - add `batch-playmode-tests`
   - add command builder and result normalization
   - add batch summary artifact output

2. host helpers if needed
   - XML parsing helper
   - test filter argument builder

3. docs
   - `README.md`
   - smoke docs if this lane gets automated coverage

## Batch Player Tests

1. `templates/server.py`
   - add `batch-player-tests`
   - build/run command synthesis
   - result normalization
   - heartbeat timeout and timeout reporting

2. docs
   - `README.md`
   - operator notes for desktop prerequisites

## Major Risks

1. **Domain reload breaks PlayMode callback continuity**
   - mitigation:
     - persist active test-run state
     - restore and re-register on load

2. **Bridge lifecycle and test lifecycle diverge**
   - mitigation:
     - add explicit `test_run_active` state or equivalent persisted evidence
     - do not infer solely from editor idle status

3. **False conceptual unification**
   - mitigation:
     - keep editor PlayMode tests and player tests as separate APIs and lanes

4. **Version drift between current package dependency and newer docs**
   - current package depends on `com.unity.test-framework: 1.5.1`
   - docs reviewed also include `2.0.1-exp.2`
   - mitigation:
     - verify exact CLI argument and callback behavior on active Unity `6000` editors before implementation finalization

5. **Mobile scope explosion**
   - mitigation:
     - explicitly defer Android/iOS player orchestration until desktop player tests are stable

## Validation Plan

Minimum regression contract for the new work:

1. passing PlayMode test run in editor
2. failing PlayMode test run in editor
3. short method-name filter for PlayMode tests
4. short fixture-name filter for PlayMode tests
5. no-tests PlayMode result
6. dirty-scene rejection
7. compile-broken rejection
8. playmode domain reload continuity proof
9. closed-editor `batch-playmode-tests` pass case
10. closed-editor `batch-playmode-tests` fail case
11. desktop player-test pass case on one supported standalone target
12. desktop player-test fail case on one supported standalone target

## Recommended Implementation Order

1. package-version research and release-notes review
2. `com.unity.test-framework` version sweep harness
3. version-selection regression run on `6000.0.58f2`
4. shared persistent test-run state extraction
5. `unity.tests.run_playmode`
6. `tests_run_playmode` scenario step
7. `batch-playmode-tests`
8. `batch-player-tests` for desktop only
9. mobile player-test design follow-up

## Decision

Proceed with:

- package-version selection before feature work is anchored
- editor PlayMode tests first
- CLI-backed batch PlayMode tests second
- desktop player tests third

Do not expand the base package into runtime/player bridge support as part of this milestone.
