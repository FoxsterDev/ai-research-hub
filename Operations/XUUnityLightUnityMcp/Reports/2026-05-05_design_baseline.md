# XUUnity Light Unity MCP Design Baseline

Date: `2026-05-05`
Status: `public baseline report`

## Scope

This report captures the current baseline design for the reusable lightweight
Unity MCP service.

## Core Shape

The service is intentionally split into:

1. host-side stdio MCP server
2. editor-only Unity bridge package

Transport:

- file IPC under `<Project>/Library/XUUnityLightMcp/`

## Baseline Design Rules

- editor-first
- disabled by default
- removable
- no player-build footprint by default
- no project-settings mutation
- no broad define injection
- capability-gated for version-sensitive operations

## Baseline Operation Surface

Current implemented baseline:

- `unity.status`
- `unity.capabilities.get`
- `unity.health.probe`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.tests.run_editmode`
- `unity.compile.player_scripts`
- `unity.compile.matrix`
- `unity.scenario.validate`
- `unity.scenario.run`
- `unity.scenario.result`
- `unity.editor.quit`
- `unity.playmode.state`
- `unity.playmode.set`
- `unity.game_view.configure`
- `unity.game_view.screenshot`

## Key Design Choice

This service is not designed as a giant "do everything in Unity" tool.

It is designed as:

- a narrow evidence-first surface
- a stable validation layer
- a foundation for future automation

## Key Constraint

Some Unity APIs are version-sensitive or internal.

For those cases, support must come through:

- capability probes
- adapter IDs
- clean disablement when unsupported

That rule is already active for the Game View path.

## Current Strengths

- tiny baseline surface compared to heavier community MCPs
- good install/remove story
- no default runtime contamination
- explicit capability gating
- compile validation without active platform switching
- reusable public smoke runners
- host-side editor-state restore for host-opened validation runs

## Current Design Gaps

- richer scenario assertions and result utilities still missing
- no runtime diagnostics companion
- no device pipeline
- no artifact comparison layer
- no profiler export path

## Canonical Source

For the full current design, use:

- `../DESIGN.md`
