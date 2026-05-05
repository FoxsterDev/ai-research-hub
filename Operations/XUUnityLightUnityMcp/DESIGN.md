# XUUnity Light Unity MCP Design

Date: `2026-05-05`
Status: `active public design`

## Goal

Build a small Unity MCP service for `xuunity` with:
- editor-only footprint
- zero player-build impact by default
- no project settings mutation
- easy install and removal
- stable validation-focused operations
- support for more than one MCP client

## Service Shape

The service has two parts:

1. local stdio MCP server
2. embedded Unity editor-only bridge package

Transport between them:
- file IPC under `<Project>/Library/XUUnityLightMcp/`

No runtime/player package is part of the base service.

Phase 5 start:
- host wrapper now uses an internal transport adapter layer
- current active adapter is `file_ipc`
- lifecycle orchestration is no longer hard-wired directly to inbox/outbox paths, which makes a future same-host transport option possible without rewriting retry, settle, and reconnect policy
- the first stronger transport path is now `tcp_loopback` on `127.0.0.1`
- this choice is intentionally cross-platform for macOS, Windows, and Linux; the design avoids Unix-domain-socket-only assumptions

## Lifecycle Contract

The wrapper is responsible for the host-local lifecycle gaps that the Unity package alone cannot close.

Current design intent:
- use `bridge-state` and `unity.status` as readiness evidence, not only request transport
- surface editor busy reasons explicitly
- activate Unity before focus-sensitive interactive operations
- wait for editor idle before and after lifecycle-sensitive synchronous operations
- distinguish request acceptance from settled editor completion
- carry bridge session identity and generation in state
- persist a lightweight request journal for reconnect and timeout evidence

This keeps the lightweight lane closer to Rider-style behavior without depending on Rider runtime internals.

Current public bridge-state baseline includes:

- `bridge_session_id`
- `bridge_generation`
- `bridge_bootstrap_attached`
- `domain_reload_in_progress`
- `asset_import_in_progress`
- `package_operation_in_progress`
- `package_operation_name`
- `script_reload_pending`
- `request_journal_directory`
- `request_journal_head`
- `refresh_settle_pending`
- `refresh_settle_request_id`
- `refresh_settle_started_utc`
- `refresh_settle_completed_utc`
- `refresh_settle_phase`
- `refresh_settle_package_resolve_requested`
- `compile_settle_pending`
- `compile_settle_request_id`
- `compile_settle_started_utc`
- `compile_settle_completed_utc`
- `compile_settle_phase`
- `compile_settle_operation`
- `package_operation_phase`
- `playmode_transition_pending`
- `playmode_transition_request_id`
- `playmode_transition_action`
- `playmode_transition_target_state`
- `playmode_transition_started_utc`
- `playmode_transition_completed_utc`
- `playmode_transition_phase`

Current request journal baseline includes:

- `bridge_bootstrap_attached`
- `request_started`
- `request_completed`
- `request_abandoned`
- `request_reclassified`

This is intentionally a first protocol layer, not the final reconnect model.

Known current weakness:

- an already-open Unity session may not hot-pick up external file-package source edits reliably through `AssetDatabase.Refresh()` plus `Client.Resolve()` alone
- in current live evidence, pickup required a real recompilation/rebootstrap cycle before the new package code became active
- editor reopen is not always required, but plain refresh/resolve is still too weak as the only update path

Current reconnect policy:

- the host classifies a request as `request_lifecycle_reset` when bridge generation/session changes before a response is observed
- explicitly idempotent operations can be retried once automatically
- non-idempotent operations stay fail-fast and surface the lifecycle-reset evidence instead of retrying blindly
- deferred async operations now retain active-request ownership until their completion callback, which makes `request_abandoned` reachable during real in-flight reloads instead of only in theory
- host lifecycle output now records transport metadata for each request attempt
- mixed-mode response routing is allowed: when `tcp_loopback` is active, direct socket-backed requests use the live connection, while file-IPC requests can still be served as fallback through the same bridge

Current native settle-watcher start:

- `unity.project.refresh` now starts a Unity-side settle tracker
- settle completion is based on package/import/script/update state observed inside Unity
- host still waits for idle as a guard, but successful refreshes can now report `completion_basis: unity_refresh_settle_watcher`
- `unity.compile.player_scripts` and `unity.compile.matrix` now start a Unity-side compile settle tracker
- successful compile payloads can now report `completion_basis: unity_compile_settle_watcher`
- nested scenario `compile_player_scripts` steps use the same compile settle watcher instead of treating synchronous API return as final completion
- `unity.playmode.set` now starts a Unity-side playmode transition watcher
- successful playmode payloads can now report `completion_basis: unity_playmode_transition_watcher`
- pending playmode transition state persists through bridge rebootstrap so `enter` can still complete on the native watcher path after Play Mode recreates the bridge session

## Stable Surface

Core validation operations:
- `unity.status`
- `unity.capabilities.get`
- `unity.health.probe`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.tests.run_editmode`
- `unity.compile.player_scripts`
- `unity.compile.matrix`

Validated editor-control additions:
- `unity.playmode.state`
- `unity.playmode.set`
- `unity.game_view.configure`
- `unity.game_view.screenshot`

## Compile Validation

Compile validation uses Unity:
- `PlayerBuildInterface.CompilePlayerScripts`
- explicit `ScriptCompilationSettings`
- per-request `BuildTarget`
- per-request `ScriptCompilationOptions`
- per-request `extraScriptingDefines`

This enables:
- target-specific compile checks
- define-specific compile checks
- development-build compile checks

Without:
- switching active build target
- mutating project-wide scripting define symbols

Constraint:
- the corresponding Unity platform support module must be installed on the host editor

## Capability Probe Model

Version-sensitive operations are not trusted by default.

On the first enabled editor session for a given:
- project
- Unity version

the bridge runs a lightweight capability probe and persists:

- `Library/XUUnityLightMcp/state/capabilities_report.json`

The report stores:
- `probe_version`
- `unity_version`
- `adapter_id` per capability
- `supported_operations`
- `disabled_operations`
- structured capability records

Risky operations are gated by this report before execution.

## Versioned Adapter Strategy

Some capabilities must be treated as adapters, not permanent assumptions.

Current example:
- `game_view_reflection_v1`

Design rule:
- every version-sensitive capability should expose an `adapter_id`
- health probe decides whether that adapter is supported
- unsupported adapters disable their operations cleanly

Future path:
- add Unity-version-specific adapters only where probe evidence shows real divergence
- prefer public Unity APIs when Unity exposes them

## Game View Policy

`unity.game_view.configure` is intentionally conservative:

- by default it does not create a new custom size
- if the requested size is missing, it fails explicitly
- persistent editor user-state change requires:
  - `allowCreateCustomSize=true`

This keeps reflective editor-state mutation opt-in.

## Extension Model

Two extension axes are intended:

1. Unity operation adapters
2. MCP client config adapters

Unity adapters should stay narrow and explicit.
Client adapters live under:

- `templates/clients/codex/`
- `templates/clients/claude-code/`
- `templates/clients/cursor/`
- `templates/clients/generic/`
