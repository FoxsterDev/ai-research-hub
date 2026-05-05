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
