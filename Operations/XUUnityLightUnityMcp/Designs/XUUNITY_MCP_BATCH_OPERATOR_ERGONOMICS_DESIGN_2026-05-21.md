# XUUnity MCP Batch Operator Ergonomics Design

Date: `2026-05-21`
Status: `implemented and validated`

## Source Retro

This design comes from:

- `Operations/XUUnityLightUnityMcp/Retros/2026-05-21_project_hook_batch_build_operator_retro.md`

The retro showed that the MCP validation surface was trustworthy, but the
operator path around long batch builds, artifact inspection, workspace
side-effects, project-defined hook summaries, and reclassified refresh requests
still costs too much attention and token budget.

This document turns those findings into a public-safe implementation plan.

## Problem

Current MCP behavior can prove correctness, but the proof is sometimes too
manual:

- long batch builds can run for minutes with no compact progress heartbeat
- batch build result JSON is useful, but does not include artifact-specific
  probes such as "does this APK contain these drawable resources?"
- build validation can mutate generated or profile-sensitive tracked files, and
  the operator must identify those side-effects manually
- project-defined hook scenarios bury useful hook outcomes inside step payloads
- refresh requests that complete and then reclassify across bridge churn are
  technically recoverable, but the operator has to know when to run
  `request-final-status`

The goal is not a new validation lane. The goal is better operator-facing
evidence on the existing lanes.

## Goals

1. Make long batch builds visibly alive without dumping raw logs.
2. Add a generic artifact probe contract for APK/AAB and other build outputs.
3. Report workspace side-effects caused by batch validation.
4. Bubble up single project-defined hook outcomes into compact scenario
   summaries.
5. Make confirmed lifecycle reclassification read as confirmed completion, not
   as ambiguous failure.

## Implementation Status

Completed on `2026-05-21`.

Implemented:

- `BatchProgressReporter` writes compact progress events to a JSONL sidecar and
  can also mirror them to stdout.
- Batch operator arguments are available on batch compile, compile matrix,
  build-config compile matrix, EditMode tests, and plain player build helpers.
- Workspace side-effect accounting is enabled by default for batch helpers when
  Git evidence is available, with `--side-effect-mode off` for explicit opt-out.
- Side-effect allowlisting supports both exact tracked paths and glob patterns
  through a JSON allow file.
- Generic artifact probes are available both as `batch-build-player` options and
  as a standalone `artifact-probe` command.
- P0 probe kinds are implemented for ZIP entries, ZIP globs, files, file text,
  and Android manifest text checks.
- Project-defined hook scenario summaries promote compact hook name, status,
  outcome, boolean flags, and small scalars while redacting secret-shaped fields.
- Scenario step results now carry `hook_name` so summaries do not have to infer
  hook identity from project payloads.
- Final-status recovery summaries include `operator_verdict`, including
  `confirmed_success_after_lifecycle_churn` for trusted Unity completion after
  lifecycle reclassification.
- Public docs and smoke-test docs were updated for the new contracts.

Validation:

- Host Python compile check passed for changed server modules.
- Host unittest discovery passed: `96` tests.
- `run_host_python_tests.sh` passed: `96` tests.
- Unity package self-tests passed against `ApperfunHub` in MCP `devmode`:
  EditMode `6/6`, PlayMode `5/5`.
- `ApperfunHub` MCP post-change validation passed end-to-end after updating its
  stale PlayMode regression selector to the current
  `Apperfun.Core.Tests.PlayMode` assembly and full test name.
- `ApperfunHub` batch compile passed for `Android`: `70` assemblies compiled,
  `0` errors, and no unexpected new dirty paths.

Not covered:

- A full APK/AAB player build and artifact-probe run against a real app artifact
  was not run in this pass.
- Physical-device validation was not part of this design.

## Non-Goals

- Do not add project-specific build profiles, resource names, package ids, or
  product paths to public `AIRoot`.
- Do not make batch builds interactive editor operations.
- Do not automatically revert workspace side-effects.
- Do not replace raw logs; keep them as backup evidence.
- Do not add device automation in this design.

## Current Surface

Relevant public host-side commands already exist:

- `batch-build-player`
- `batch-compile`
- `batch-compile-matrix`
- `batch-build-config-compile-matrix`
- `batch-editmode-tests`
- `request-scenario-result-summary`
- `request-final-status`
- `request-status-summary`

Relevant existing docs:

- `BUILD_AUTOMATION.md`
- `SMOKE_TESTS.md`
- `CONTINUATION.md`
- `DESIGN.md`

## Proposed Additions

### 1. Batch Progress Heartbeat

Add a compact heartbeat stream for long-running batch helpers.

The heartbeat should be written to stdout by wrapper commands and optionally to
a machine-readable sidecar file.

Recommended sidecar path:

```text
Library/XUUnityLightMcp/logs/batch/<run_id>/progress.jsonl
```

Each line is one compact JSON object:

```json
{
  "event": "batch_progress",
  "run_id": "20260521T145431Z_DevBuild_Android",
  "operation": "batch-build-player",
  "phase": "unity_batch_running",
  "elapsed_seconds": 180,
  "process_alive": true,
  "log_path": "Library/XUUnityLightMcp/logs/batch/<run_id>/build.log",
  "last_known_output_path": "",
  "message": "Unity batch build is still running."
}
```

Minimum phases:

- `preflight`
- `prepare_started`
- `prepare_completed`
- `unity_batch_started`
- `unity_batch_running`
- `unity_batch_completed`
- `artifact_probe_started`
- `artifact_probe_completed`
- `side_effect_scan_completed`
- `summary_written`

Default heartbeat interval:

- first event immediately at phase start
- then every `30` seconds while Unity process is still running
- final event at completion

Operator contract:

- no heartbeat means wrapper bug or process failure
- heartbeat does not imply build success
- final result JSON remains authoritative

### 2. Artifact Probe Contract

Add optional artifact probes to batch build helpers.

Public layer owns generic probe types. Project wrappers own specific expected
values.

#### CLI Shape

Support either a JSON file or inline JSON:

```bash
python3 templates/server.py batch-build-player \
  --project-root /path/to/project \
  --build-target Android \
  --artifact-probe-file /path/to/probes.json
```

Optional companion helper:

```bash
python3 templates/server.py artifact-probe \
  --artifact-path Builds/Android/App.apk \
  --artifact-probe-file /path/to/probes.json
```

The companion helper lets a project wrapper inspect artifacts produced by custom
build flows without re-running the build.

#### Probe Input Schema

```json
{
  "version": 1,
  "artifactPath": "Builds/Android/App.apk",
  "stopOnFirstFailure": false,
  "expectations": [
    {
      "id": "android-small-icon-mdpi",
      "platform": "Android",
      "artifactKind": "apk",
      "kind": "zip_entry_exists",
      "path": "res/drawable-mdpi-v4/ic_stat_example.png"
    },
    {
      "id": "android-manifest-permission",
      "platform": "Android",
      "artifactKind": "apk",
      "kind": "android_manifest_contains",
      "value": "android.permission.POST_NOTIFICATIONS"
    },
    {
      "id": "ios-plist-key",
      "platform": "iOS",
      "artifactKind": "folder",
      "kind": "plist_key_exists",
      "path": "Info.plist",
      "key": "NSUserTrackingUsageDescription"
    }
  ]
}
```

#### P0 Probe Kinds

- `zip_entry_exists`
- `zip_entry_absent`
- `zip_entry_glob_exists`
- `android_manifest_contains`
- `file_exists`
- `file_contains`

#### P1 Probe Kinds

- `plist_key_exists`
- `plist_value_equals`
- `json_path_exists`
- `json_value_equals`
- `gradle_dependency_exists`
- `podfile_lock_pod_exists`

#### Artifact Probe Output

```json
{
  "artifact_probe_summary": {
    "enabled": true,
    "artifact_path": "Builds/Android/App.apk",
    "artifact_exists": true,
    "expectation_count": 3,
    "passed_count": 3,
    "failed_count": 0,
    "skipped_count": 0,
    "succeeded": true,
    "failures": [],
    "results": [
      {
        "id": "android-small-icon-mdpi",
        "kind": "zip_entry_exists",
        "passed": true,
        "message": "Entry exists."
      }
    ]
  }
}
```

Failure rules:

- if artifact probing is enabled and any required expectation fails, the batch
  command should return non-zero unless `--artifact-probe-warn-only` is set
- artifact probe failure must not be hidden behind `BuildResult=Succeeded`
- final output should expose both `build_succeeded` and
  `artifact_probe_succeeded`

### 3. Workspace Side-Effect Accounting

Add a before/after workspace scan around batch helpers.

The public layer should not require Git, but when Git exists it can provide the
best tracked-file evidence.

#### Inputs

Optional:

```bash
--workspace-root /path/to/repo
--side-effect-mode git
--side-effect-allow-file /path/to/allowed-side-effects.json
```

Default behavior:

- if `--workspace-root` is omitted, use project root
- if Git is unavailable, return `mode=unavailable`
- do not fail the build only because side-effects exist

#### Allow File Schema

```json
{
  "version": 1,
  "allowedTrackedPaths": [
    "Assets/Plugins/Android/AndroidManifest.xml",
    "ProjectSettings/AndroidResolverDependencies.xml"
  ],
  "allowedPathGlobs": [
    "Assets/StreamingAssets/google-services*.json"
  ],
  "notes": "Project wrappers may pass generated files expected to change during profile-aware builds."
}
```

#### Output Schema

```json
{
  "workspace_side_effects": {
    "enabled": true,
    "mode": "git",
    "workspace_root": "/path/to/repo",
    "preexisting_dirty_count": 2,
    "new_dirty_count": 3,
    "allowed_new_dirty_count": 2,
    "unexpected_new_dirty_count": 1,
    "preexisting_dirty_paths": [
      "ProjectSettings/ProjectSettings.asset"
    ],
    "allowed_new_dirty_paths": [
      "Assets/Plugins/Android/AndroidManifest.xml"
    ],
    "unexpected_new_dirty_paths": [
      "Assets/Generated/Unexpected.asset"
    ],
    "recommended_cleanup_commands": [
      "git restore -- Assets/Plugins/Android/AndroidManifest.xml"
    ]
  }
}
```

Rules:

- never run cleanup automatically
- never recommend cleanup for paths that were dirty before the batch command
- if a path changed before and after, classify it as `preexisting_dirty_paths`
  unless the wrapper can prove the batch command introduced a new diff hunk
- keep literal secret values out of summaries

### 4. Project-Defined Hook Summary Promotion

Improve `request-scenario-result-summary` for scenarios that include
`project_defined_hook` steps.

For each hook step, add a compact summary:

```json
{
  "project_defined_hook_summary": {
    "hook_count": 1,
    "all_hooks_succeeded": true,
    "hooks": [
      {
        "step_id": "regenerate_assets",
        "hook_name": "example.hook",
        "status": "passed",
        "outcome": "completed",
        "payload_flags": {
          "contains_unexpected_test_assemblies": false
        }
      }
    ]
  }
}
```

Generic extraction rules:

- include `hookName`, step id, step status, and top-level hook payload
  `outcome` when present
- include boolean payload fields under `payload_flags`
- include small scalar payload fields under `payload_scalars`
- cap string values and arrays to keep summaries compact
- do not expose project-specific secrets or raw config values

This summary should be additive. Raw scenario results remain available.

### 5. Reclassified Request Summary Clarity

When a request is reclassified after lifecycle churn but final status proves
Unity completion, compact surfaces should lead with confirmed outcome.

Current evidence fields already support this:

- `request_completed=true`
- `operation_outcome=completed_ok`
- `reclassified=true`
- `reclassified_status=settled_after_lifecycle_reset`
- `result_trust_class=unity_completed_confirmed`
- `recommended_next_action=none`

Proposed extra field:

```json
{
  "operator_verdict": {
    "status": "confirmed_success_after_lifecycle_churn",
    "message": "Unity completed the operation; lifecycle reclassification is informational.",
    "should_retry": false,
    "next_action": "continue"
  }
}
```

Rules:

- `operator_verdict.status=confirmed_success_after_lifecycle_churn` only when
  `result_trust_class=unity_completed_confirmed`
- if result trust is `wrapper_failed_unity_unproven`, keep warning-first
  wording and include recovery command
- if `recommended_next_action=none`, do not suggest retry

## Implementation Plan

### Phase 1: Host-Side Progress And Side Effects

Status: `complete`

Primary files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- any helper modules already used by `batch-build-player`
- `Operations/XUUnityLightUnityMcp/BUILD_AUTOMATION.md`

Tasks:

1. Add a reusable `BatchProgressReporter`.
2. Wire it into `batch-build-player` first.
3. Add `WorkspaceSideEffectTracker` with Git-backed implementation.
4. Add final `workspace_side_effects` to batch result JSON.
5. Keep behavior additive and disabled where prerequisites are unavailable.

Acceptance:

- batch build emits progress at start, during long run, and completion
- final JSON includes `workspace_side_effects`
- side-effect tracker does not fail when Git is missing
- no automatic restore happens

### Phase 2: Artifact Probe Core

Status: `complete`

Primary files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- optional new helper: `templates/artifact_probe.py`
- `Operations/XUUnityLightUnityMcp/BUILD_AUTOMATION.md`
- `Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`

Tasks:

1. Implement `zip_entry_exists`, `zip_entry_absent`, and
   `zip_entry_glob_exists`.
2. Implement `file_exists` and `file_contains`.
3. Implement Android manifest text probe as a pragmatic P0 check.
4. Add `artifact_probe_summary` to batch result JSON.
5. Add optional standalone `artifact-probe` command.

Acceptance:

- a built APK can be checked for expected resource entries without manual
  `unzip`
- failed required probes make the command fail
- `--artifact-probe-warn-only` keeps build success but reports probe failure
- probe output is compact enough to paste into chat closeout

### Phase 3: Scenario Hook Summary

Status: `complete`

Primary files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- scenario result summary code path
- Unity scenario result payload shape if needed

Tasks:

1. Detect `project_defined_hook` steps in scenario results.
2. Extract hook status, hook name, outcome, boolean flags, and compact scalars.
3. Add `project_defined_hook_summary` to scenario result summary.
4. Preserve raw scenario result behavior.

Acceptance:

- single-hook scenarios produce a compact top-level hook summary
- multi-hook scenarios list each hook step
- large hook payloads are truncated
- secrets are not surfaced by generic extraction

### Phase 4: Reclassification Operator Verdict

Status: `complete`

Primary files:

- request final/latest/status summary code path
- `Operations/XUUnityLightUnityMcp/CONTINUATION.md`

Tasks:

1. Add `operator_verdict` to final status recovery outputs.
2. Use confirmed-success wording for completed requests reclassified after
   lifecycle churn.
3. Keep warning-first wording for unproven lifecycle failures.
4. Document the retry rule.

Acceptance:

- a completed/reclassified refresh produces `should_retry=false`
- the summary tells the operator to continue, not retry
- unproven requests still surface recovery commands

## Public Docs Updates

Required after implementation:

- `BUILD_AUTOMATION.md`
  - batch progress heartbeat
  - artifact probe input/output
  - workspace side-effect accounting
- `SMOKE_TESTS.md`
  - add Artifact Probe Smoke
  - add Batch Side-Effect Smoke
- `CONTINUATION.md`
  - add mini-playbook for confirmed reclassified requests
- `README.md`
  - mention compact batch progress/probe summaries
- `ROADMAP.md`
  - mark this design as implementation track while in progress

## Smoke Tests

### Artifact Probe Smoke

1. Build or use a small test ZIP/APK fixture.
2. Probe for an existing entry.
3. Probe for a missing required entry.
4. Verify success and failure accounting.
5. Verify warn-only mode.

### Batch Progress Smoke

1. Run a fake or short batch helper with progress enabled.
2. Verify at least start and final heartbeat events.
3. Run a longer synthetic command and verify periodic heartbeat.

### Side-Effect Smoke

1. Create a temporary Git workspace.
2. Mark one file dirty before the command.
3. Mutate another file during the command.
4. Verify preexisting and new dirty paths are separated.
5. Verify no cleanup is run automatically.

### Hook Summary Smoke

1. Run a scenario with one synthetic `project_defined_hook`.
2. Include boolean and scalar hook payload fields.
3. Verify `project_defined_hook_summary` is compact and complete.

### Reclassification Verdict Smoke

1. Use existing lifecycle fault/reclassification suite.
2. Verify completed/reclassified requests produce
   `confirmed_success_after_lifecycle_churn`.
3. Verify unproven lifecycle failures do not get success wording.

## Risks

- Git side-effect tracking can be misleading in dirty worktrees.
  - Mitigation: classify preexisting dirty paths separately and never clean
    automatically.
- Artifact probes may become project-specific if too many kinds are added too
  early.
  - Mitigation: keep P0 to generic ZIP/file/text checks.
- Progress heartbeats can become noisy.
  - Mitigation: use a slow interval and compact JSON lines.
- Hook summaries can leak project-specific fields.
  - Mitigation: include only generic scalar/boolean fields by default and cap
    strings.

## Decisions

- `artifact-probe` is both a public standalone CLI command and a
  `batch-build-player` option.
- Side-effect tracking defaults to enabled for batch helpers that run through
  the shared batch operation path, with an explicit `--side-effect-mode off`
  opt-out.
- Project wrappers classify allowed generated files through JSON config that
  supports both exact tracked paths and glob patterns.
- Progress heartbeat events are JSONL sidecar by default, with stdout enabled by
  default and suppressible through `--no-progress-stdout`.

## Definition Of Done

The design is implemented when:

- batch builds emit compact progress events
- batch build result JSON can include artifact probe summaries
- workspace side-effects are reported without automatic cleanup
- project-defined hook scenarios have top-level hook summaries
- final-status output gives a clear operator verdict for confirmed
  reclassified requests
- docs and smoke tests describe all new contracts

The implementation should be considered incomplete if operators still need to
read raw build logs or manually inspect APK contents for routine artifact
verification.
