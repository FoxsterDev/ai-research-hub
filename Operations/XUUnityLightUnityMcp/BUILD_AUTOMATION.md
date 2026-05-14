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
- `unity.edm4u.resolve`
- `unity.sdk.dependency.verify`
- `unity_status_summary`
- `unity_request_final_status`
- `unity_scenario_result_summary`
- `unity_maintenance_prune`

Current public scenario hook lane:
- `project_defined_hook`

Current public host-side batch helpers:
- `batch-compile`
- `batch-compile-matrix`
- `batch-build-config-compile-matrix`
- `batch-editmode-tests`
- `batch-build-player`

## Lane Selection Rule

Treat the build and validation surface as two different classes of work:

- interactive control-plane work
- batch data-plane work

Use the interactive MCP lane for:
- `ensure-ready`
- `unity.status`
- `unity.health.probe`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.playmode.*`
- `unity.game_view.*`
- compile validation
- deterministic EditMode tests when the editor must stay open
- project config inspection
- SDK package restore, EDM4U resolver triggering, and generated dependency artifact verification
- project-defined smoke and hook flows that are short-lived and editor-bound

Use the batch lane for:
- artifact builds
- signed package generation
- long-running export pipelines
- end-to-end build flows where success should be judged by process exit and generated outputs

For third-party SDK updates, prefer this validation order:
1. project refresh with package resolve
2. compile validation for affected Android/iOS targets
3. `unity.edm4u.resolve` for Android dependency generation
4. `unity.sdk.dependency.verify` against generated resolver files
5. batch export or player build
6. generated artifact inspection, such as Gradle output, Xcode export, Podfile.lock, manifest, plist, or dependency reports
7. device/runtime validation through project hooks or manual QA when SDK behavior depends on native runtime services

Minimal dependency verification payload:

```json
{
  "stopOnFirstFailure": false,
  "expectations": [
    {
      "id": "android-resolver-package",
      "platform": "Android",
      "path": "ProjectSettings/AndroidResolverDependencies.xml",
      "kind": "android_resolver_package",
      "value": "com.vendor:artifact:1.2.3"
    },
    {
      "id": "android-repository",
      "platform": "Android",
      "path": "Assets/Plugins/Android/settingsTemplate.gradle",
      "kind": "gradle_repository",
      "value": "https://vendor.example/maven"
    },
    {
      "id": "ios-pod",
      "platform": "iOS",
      "path": "Builds/iOS/MyExport/Podfile.lock",
      "kind": "podfile_lock_pod",
      "value": "VendorPod",
      "version": "1.2.3"
    }
  ]
}
```

Do not use the live interactive scenario lane as the primary waiter for
long-running artifact builds. It is the right control plane for editor-aware
inspection and short bounded work, but it is the wrong data plane for build
correctness.

## Scenario Lane Constraint

The interactive scenario lane is intentionally serialized.

Operational implications:
- do not schedule parallel scenario runs against the same project/editor session
- treat `scenario_already_running` as a contract signal, not as a flaky transport error
- wrappers should surface this constraint clearly instead of pretending the lane is fully concurrent

If the workflow needs:
- parallel work
- long waits
- artifact production
- or transport-independent closeout proof

move that work to a batch helper or to a narrower direct request flow instead of
stacking more logic onto `unity.scenario.run`.

This means the public layer already covers:
- current active platform inspection
- deterministic platform switching
- compile validation without switching active build target
- compile and EditMode validation when the target project is closed
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
  batch-compile \
  --project-root /path/to/UnityProject \
  --target Android
```

Define-matrix validation and deterministic EditMode tests use the same closed-project batch lane:

```bash
python3 AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py \
  batch-build-config-compile-matrix \
  --project-root /path/to/UnityProject

python3 AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py \
  batch-editmode-tests \
  --project-root /path/to/UnityProject \
  --assembly-name MyProject.Tests
```

Plain artifact builds still use:

```bash
python3 AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py \
  batch-build-player \
  --project-root /path/to/UnityProject \
  --build-target Android \
  --output-path Builds/Android/MyGame.apk
```

Notes:
- this lane is intentionally plain
- it expects the same Unity project editor to be closed before execution
- another Unity editor process for a different project does not block this lane
- it uses the current project settings and enabled scenes unless scenes are passed explicitly
- it is suitable for simple projects and CI lanes, not for custom per-project restore workflows
- it is valid for compile, compile-matrix, and deterministic EditMode test work
- it is not a substitute for Play Mode, Game View, scene-state inspection, or other interactive editor evidence

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
- the public layer should still own lane selection, timeout posture, artifact collection, and closeout reporting

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
  "profileName": "ProfileA",
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
- emit compact failure summaries for failed prepare/build phases before sending
  callers to raw logs

For profile-aware or custom-tool builds, default automation posture should be
non-destructive:
- do not enable autorun by default for artifact automation
- do not persist version or config mutations by default
- restore tracked project state unless the caller explicitly opts into persistence
- record whether the editor was closed and reopened as part of the automation

Recommended generic automation-policy fields:
- `artifact_only`
- `allow_autorun`
- `persist_version_updates`
- `persist_config_changes`
- `reopen_editor_after_build`

The exact project flags can vary, but the public orchestration contract should
preserve these semantics.

## Evidence Hierarchy

For build-sensitive work, trust generated outputs above source-only reasoning.

Preferred evidence order:
1. process exit code
2. generated artifact presence
3. generated manifest / plist / Gradle / Xcode output
4. compact build summary artifact
5. source manifest or processor inspection

Practical rule:
- if the question is whether a build processor or postprocess step changed the
  produced app correctly, inspect generated output first
- do not claim artifact correctness from source inspection alone when generated
  build evidence is available

This matters especially for:
- Android manifest injection
- network security config generation
- plist or entitlement mutation
- third-party postprocess build hooks
- signed package/export pipelines

## Cleanup and Token Discipline

The public surface should avoid forcing callers to inspect large raw logs.

Preferred pattern:
- read compact status summaries first
- resolve ambiguous lifecycle-reset requests by request id before rerunning them
- read compact scenario summaries second
- inspect full logs only on failure or unresolved ambiguity
- prune old request journals and scenario results routinely

For batch builds, the same rule applies:

- a successful run should end in a compact build result artifact
- a failed run should still end in a compact failure summary artifact with:
  - phase: `prepare` or `build`
  - transport outcome
  - Unity operation outcome when known
  - top actionable error or blocker
  - paths to the next raw logs only as second-line evidence
- batch wrapper stdout should surface that summary artifact path directly instead
  of dumping large raw result payloads or large log tails by default

- the compact result should also name the strongest generated evidence that was
  inspected, for example:
  - artifact path
  - build report path
  - generated manifest/plist path
  - whether tracked state was restored

This keeps operator diagnosis bounded even when `prepare.log` or `build.log`
are large.

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
