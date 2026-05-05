# XUUnity Light Unity MCP Continuation

Date: `2026-05-05`
Status: `new-chat continuation note`

## What Is Already Implemented

External server:
- minimal stdio MCP layer
- `initialize`
- `tools/list`
- `tools/call`
- local diagnostics helpers

Unity bridge:
- heartbeat state
- request pump
- capability probe
- capability gating
- compile validation
- play mode control
- Game View configure and screenshot

## Important Runtime Files

Inside the target Unity project:

- `Library/XUUnityLightMcp/config/bridge_config.json`
- `Library/XUUnityLightMcp/state/bridge_state.json`
- `Library/XUUnityLightMcp/state/capabilities_report.json`
- `Library/XUUnityLightMcp/inbox/`
- `Library/XUUnityLightMcp/outbox/`
- `Library/XUUnityLightMcp/compile/`
- `Library/XUUnityLightMcp/captures/`

## Key Decisions

- editor-only package
- disabled by default
- no `ProjectSettings` mutation
- no runtime asmdef
- no broad define mutation
- compile checks should use Unity APIs, not platform switching
- version-sensitive features should be probed and gated

## What A New Chat Should Check First

1. project Unity version
2. whether the package is installed
3. whether the bridge is enabled
4. `bridge_state.json`
5. `capabilities_report.json`
6. `unity.status`
7. `unity.capabilities.get`

Only after that:
- tests
- compile matrix
- play mode
- Game View operations

## Expected Next Work

1. onboard the target Unity project in opt-in mode
2. run `unity.health.probe`
3. verify `status`, `capabilities`, `console`, `scene`, `tests`, `compile`
4. measure editor idle overhead
5. decide whether `unity_game_view_cleanup_sizes` is needed
6. add project-specific operational entrypoints only after the generic package is stable
