# AI Integration Guide

Date: `2026-05-05`
Status: `active public guidance`

## Purpose

Use this guide when an AI agent needs to integrate the lightweight Unity MCP
service into a different repo or Unity project.

This guide is agent-agnostic.
It is written to work for Codex, Claude Code, Cursor, Gemini-style agents, and
future MCP-capable assistants.

Author:
- Siarhei Khalandachou
- LinkedIn: `https://www.linkedin.com/in/khalandachou/`

## What The Agent Should Understand First

This service has two layers:

1. a host-side MCP server
2. an editor-only Unity package

They communicate through file IPC under:

- `<Project>/Library/XUUnityLightMcp/`

The Unity package is:

- editor-only
- disabled by default
- removable
- not intended to affect player builds by default

## Integration Goals

When integrating into a new repo or project, the agent should:

1. install the host-side service
2. install or reference the Unity package
3. enable the bridge only for the target project
4. open Unity
5. verify capability and health
6. stop if capability checks fail
7. only then run validation or automation operations

## Minimum Host Steps

From the repo that contains `AIRoot`:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh
```

If the Unity project is in the same repo:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject \
  --enable-project
```

## GitHub Package Install Route

For projects that want to consume the Unity package directly from GitHub,
the manifest entry should use the package subpath:

```json
{
  "dependencies": {
    "com.xuunity.light-mcp": "https://github.com/FoxsterDev/ai-research-hub.git?path=/Operations/XUUnityLightUnityMcp/templates/unity-package#master"
  }
}
```

Use this route when:

- the consumer repo should not vendor the package files locally
- the team wants a single upstream source of truth

Use the embedded local-package route when:

- the consumer repo wants to modify or pin the package locally
- the team wants zero dependency on GitHub availability during integration

For unpublished host-local verification, Unity also supports a Git FILE-protocol
dependency pinned to a full commit hash. Use that route only as a temporary
same-host fallback when the upstream package source is not published yet.

## What The Agent Should Check After Install

Before doing real work, check in this order:

1. project root is a real Unity project
2. package is present in the manifest
3. bridge config exists and is enabled
4. Unity editor has opened the project
5. `bridge_state.json` exists
6. `capabilities_report.json` exists or can be generated
7. `unity.status` succeeds
8. `unity.capabilities.get` succeeds
9. `unity.health.probe` succeeds

Only after that:

- compile
- tests
- scene inspection
- play mode
- screenshots
- scenario runs

## Agent Behavior Rules

An integrating agent should:

- treat capability probe as authoritative for version-sensitive operations
- keep the bridge disabled unless the current task actually needs Unity-aware validation
- prefer read and validation operations before mutation
- keep install and removal simple
- keep validation gaps explicit when Unity is not running or the bridge is disabled

An integrating agent should not:

- mutate `ProjectSettings` just to make the MCP work
- inject broad scripting defines
- assume Game View reflection works on every Unity version
- treat shell compile as equivalent to Unity validation
- silently install runtime diagnostics into production build paths
- try to click Unity Safe Mode dialogs through fragile GUI automation as a default startup path

## Startup Policy

For interactive editor startup, prefer the host-side `ensure-ready` helper over
blindly waiting for `bridge_state.json`.

Recommended default:
- `fail_fast_on_interactive_compile_block`

Alternative policies:
- `auto_enter_safe_mode_preferred`
- `batch_compile_lane`

Important limitation:
- this service does not auto-click the Unity Safe Mode dialog
- use Unity preferences to auto-enter Safe Mode if that is the team default
- use `--background-open` when the host should avoid Unity stealing focus on macOS

## Required Evidence To Record

After integration, the agent should record:

- Unity version
- package version
- whether the package is GitHub-based or embedded
- whether bridge enablement succeeded
- capability adapter IDs
- supported and disabled operations
- at least one successful:
  - `unity.status`
  - `unity.health.probe`
  - `unity.compile.player_scripts` or `unity.tests.run_editmode`

## Recommended First Validation Pass

For a new consumer project, the recommended first pass is:

1. `unity.status`
2. `unity.capabilities.get`
3. `unity.health.probe`
4. `unity.console.tail`
5. `unity.scene.snapshot`
6. `unity.compile.player_scripts`
7. `unity.tests.run_editmode`

Only after that:

8. `unity.playmode.state`
9. `unity.playmode.set`
10. `unity.game_view.screenshot`
11. `unity.scenario.validate`
12. `unity.scenario.run`
13. `unity.scenario.result`

Scenario extension route:

14. implement `IXUUnityLightMcpScenarioHook` in a project `Assets/Editor/` assembly when the consumer needs project-local automation not worth promoting into the shared package yet

## Where To Extend

If a new consumer project needs custom automation, the agent should prefer:

1. project-defined scenario hooks
2. project-defined adapter operations
3. host-side wrappers

The agent should avoid using generic dynamic code execution as the default
extension model.

## Canonical References

- `README.md`
- `DESIGN.md`
- `ROADMAP.md`
- `COMPARISON.md`
- `LICENSE.md`
- `Reports/`
