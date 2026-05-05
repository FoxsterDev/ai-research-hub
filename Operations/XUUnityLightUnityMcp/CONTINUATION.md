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
- scenario validation, asynchronous scenario runs, and persisted scenario results

## Important Runtime Files

Inside the target Unity project:

- `Library/XUUnityLightMcp/config/bridge_config.json`
- `Library/XUUnityLightMcp/state/bridge_state.json`
- `Library/XUUnityLightMcp/state/capabilities_report.json`
- `Library/XUUnityLightMcp/inbox/`
- `Library/XUUnityLightMcp/outbox/`
- `Library/XUUnityLightMcp/compile/`
- `Library/XUUnityLightMcp/captures/`
- `Library/XUUnityLightMcp/scenarios/active_run.json`
- `Library/XUUnityLightMcp/scenarios/results/`

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
- scenario runs

## What A New Chat Should Read First

For reusable MCP work:

1. `README.md`
2. `ROADMAP.md`
3. `AI_INTEGRATION.md`
4. `Reports/2026-05-05_progress_status.md`
5. `Reports/2026-05-05_xuunity_protocol_integration_status.md`

For protocol-integration work:

1. shared `xuunity` protocol guidance
2. this continuation note
3. the public integration-status report

## Expected Next Work

1. switch consumer projects from embedded copy to GitHub package consumption where appropriate
2. wire scenario guidance into shared `xuunity` protocols
3. add richer scenario assertions and scenario result utilities
4. measure editor idle overhead with scenario layer enabled
5. decide whether `unity_game_view_cleanup_sizes` is needed
6. add device/runtime automation layers on top of scenario control plane
7. add project-specific operational entrypoints only after the generic package is stable
