# Build Automation Surface

This document defines the public-safe build automation surface for
`AIRoot/Operations/XUUnityLightUnityMcp`.

The goal is to keep the public contract generic enough for:
- plain Unity projects that only need normal batch builds
- projects with build profiles or config assets
- projects with custom build tooling that still want to reuse MCP orchestration

## Implemented Now

Current public operations:
- `unity.build_target.get`
- `unity.build_target.switch`
- `unity.compile.player_scripts`
- `unity.compile.matrix`
- `unity_status_summary`
- `unity_request_final_status`
- `unity_scenario_result_summary`
- `unity_maintenance_prune`

Current public scenario hook lane:
- `project_defined_hook`

Current public host-side batch helper:
- `batch-build-player`

This means the public layer already covers:
- current active platform inspection
- deterministic platform switching
- compile validation without switching active build target
- compact polling/status surfaces
- request-level recovery follow-up after transport churn
- cleanup of request/scenario/capture artifacts
- typed project hook execution inside scenarios

## Build Tiers

Promote public behavior in three tiers.

### 1. Plain Batch Build

Use for simple Unity projects with no custom build profiles.

Expected contract:
- build from current editor state or explicit target
- optional target switch before build
- optional artifact-only mode
- optional reopen-editor behavior handled by the host wrapper

The public layer should own orchestration, not project-specific settings mutation.

Current minimal host-side command:

```bash
python3 AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py \
  batch-build-player \
  --project-root /path/to/UnityProject \
  --build-target Android \
  --output-path Builds/Android/MyGame.apk
```

Notes:
- this lane is intentionally plain
- it expects the Unity project editor to be closed before execution
- it uses the current project settings and enabled scenes unless scenes are passed explicitly
- it is suitable for simple projects and CI lanes, not for custom per-project restore workflows

### 2. Profile-Aware Batch Build

Use when a project exposes named build profiles or config assets.

Expected adapter surface:
- list profiles
- resolve profile by name
- apply profile using the project's real apply flow
- build after apply

Important rule:
- the public layer must not assume a specific asset path, profile schema, or profile names
- the project adapter owns those details

### 3. Custom Tool Build

Use when the project already has a full custom build pipeline with versioning,
SDK sync, signing, third-party processors, evidence collection, or restore logic.

Expected split:
- public MCP layer owns orchestration and typed phases
- project adapter owns the actual tool-specific build behavior

## Typed Hook Phases

When exposing project build hooks through MCP, prefer typed phases over
one-off ad hoc hook names.

Recommended phases:
- `pre_apply`
- `post_apply`
- `pre_build`
- `post_build`
- `collect_evidence`
- `restore_state`

Hook payload shape should stay JSON-only:

```json
{
  "phase": "pre_build",
  "target": "Android",
  "profileName": "ReleaseDebug",
  "context": {
    "artifactOnly": true
  }
}
```

Hook response shape should stay JSON-only:

```json
{
  "outcome": "completed",
  "changedFiles": [
    "ProjectSettings/ProjectSettings.asset"
  ],
  "evidence": {
    "bundleVersion": "1.2.3"
  }
}
```

## State Safety Rules

Public orchestration should assume build automation is stateful and risky.

Default expectations:
- do not leave target switches ambiguous
- do not acknowledge success before the real outcome is known
- prefer batch execution for artifact-only builds
- define explicit restore boundaries for project-managed files
- emit compact summaries so callers do not need to read large logs

## Cleanup and Token Discipline

The public surface should avoid forcing callers to inspect large raw logs.

Preferred pattern:
- read compact status summaries first
- resolve ambiguous lifecycle-reset requests by request id before rerunning them
- read compact scenario summaries second
- inspect full logs only on failure or unresolved ambiguity
- prune old request journals and scenario results routinely

Current cleanup command:

```bash
python3 AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py \
  maintenance-prune \
  --project-root /path/to/UnityProject \
  --dry-run
```

## What Stays Project-Local

Do not promote these into public `AIRoot`:
- project-specific asset paths
- project-specific profile names
- project-specific restore file lists
- custom signing conventions
- product-specific output validation rules
- project-private SDK knowledge
