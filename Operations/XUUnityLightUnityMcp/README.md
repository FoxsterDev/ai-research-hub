# XUUnity Light Unity MCP

This folder contains the public-safe lightweight Unity MCP service
designed for `xuunity`.

It is intentionally smaller than the current heavyweight Unity MCP packages:
- editor-only Unity footprint
- disabled-by-default bridge activation
- no runtime/player support in the base package
- no NuGet restore path
- no SignalR or relay stack
- no Roslyn execution path

Canonical location:

- `AIRoot/Operations/` because this package is reusable, public-safe setup
- it contains no host-private paths, secrets, or mutable local state

Related public docs:
- `DESIGN.md`
- `CONTINUATION.md`
- `COMPARISON.md`

## Current Status

This is a minimal working MCP service, not a production-hardened one.

What exists now:
- install/init script
- external stdio server scaffold
- embedded Unity package template
- file IPC layout
- Unity editor heartbeat
- Unity capability probe and persisted health report
- Unity-side request handling for:
  - `unity.status`
  - `unity.capabilities.get`
  - `unity.health.probe`
  - `unity.console.tail`
  - `unity.scene.snapshot`
  - `unity.tests.run_editmode`
  - `unity.compile.player_scripts`
  - `unity.compile.matrix`
  - `unity.playmode.state`
  - `unity.playmode.set`
  - `unity.game_view.configure`
  - `unity.game_view.screenshot`
- MCP `initialize`
- MCP `tools/list`
- MCP `tools/call`

What does not exist yet:
- production-hardening of the stdio server
- broader real-client validation in Codex and other MCP clients
- richer second-wave read operations
- more polished host-local wrappers and repo-aware helpers

## Goal

Provide one small service that can evolve into the default `xuunity` Unity MCP path with:
- tiny install surface
- zero player-build footprint by default
- no project settings mutation
- easy project removal
- clear project targeting
- easy extension with new tool adapters
- support for more than one AI client

## Files

- `init_xuunity_light_unity_mcp.sh`
- `templates/run.sh`
- `templates/server.py`
- `templates/clients/`
- `templates/unity-package/`

## Scaffold Install

Install the external scaffold only:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh
```

Install the external scaffold and copy the Unity package template into a project:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject
```

Install into a project and enable the bridge for the next editor session:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject \
  --enable-project
```

Disable the bridge and remove its local `Library/` state:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject \
  --disable-project
```

Uninstall it from the Unity project:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject \
  --uninstall-project
```

Preview first:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh \
  --project-root /path/to/UnityProject \
  --dry-run
```

## What It Installs

External scaffold:
- `~/.codex-tools/xuunity-light-unity-mcp/server.py`
- `~/.codex-tools/xuunity-light-unity-mcp/run.sh`

Optional Unity project scaffold:
- `<Project>/Packages/com.xuunity.light-mcp/`
- manifest entry:
  - `"com.xuunity.light-mcp": "file:Packages/com.xuunity.light-mcp"`
- local activation file only when explicitly enabled:
  - `<Project>/Library/XUUnityLightMcp/config/bridge_config.json`
- package-declared dependency for the `unity_tests_run_editmode` operation:
  - `com.unity.test-framework`

## Safety Notes

- the init script does not install a Codex MCP config block by default
- the current external server implements a minimal stdio MCP layer, but should still be treated as early-stage
- client config templates are still intentionally conservative
- the Unity package is editor-only in this scaffold
- the Unity package stays idle unless a local `Library/XUUnityLightMcp/config/bridge_config.json` exists with `"enabled": true`
- on first enabled editor session for a given project and Unity version, the bridge runs a capability probe and persists:
  - `Library/XUUnityLightMcp/state/capabilities_report.json`
- version-sensitive operations are gated by that report instead of assuming reflection-based paths are always valid
- remove path is intentionally simple: no build defines, no package-registry mutation, no player/runtime asmdef, no project settings writes
- `unity_tests_run_editmode` intentionally uses the official Unity Test Framework instead of a custom test runner path
- `unity_compile_player_scripts` and `unity_compile_matrix` use Unity `PlayerBuildInterface.CompilePlayerScripts` to validate platform-specific compile paths without switching the active build target or mutating project scripting defines
- target-specific compile validation still depends on the corresponding Unity platform support module being installed on the host
- `unity_capabilities` and `unity_health_probe` expose the probe report to MCP clients so they can avoid unsupported operations instead of learning by failure
- `unity_game_view_configure` uses Unity internal editor reflection and, by default, refuses to create new custom Game View sizes
- if you opt in with `allowCreateCustomSize=true`, `unity_game_view_configure` may create a matching custom Game View size entry in editor user state
- `unity_game_view_screenshot` uses the Game View render texture directly and includes a vertical-flip correction on graphics backends where `graphicsUVStartsAtTop` is true

## Local Smoke Route

After installing the Unity package into a project and opening the project in Unity:

Read the heartbeat state:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  bridge-state \
  --project-root /path/to/UnityProject
```

Send a direct file-IPC `unity.status` request:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-status \
  --project-root /path/to/UnityProject
```

Read the persisted capability report:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-capabilities \
  --project-root /path/to/UnityProject
```

Force a fresh Unity-side health probe:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-health-probe \
  --project-root /path/to/UnityProject
```

Send a direct file-IPC compile validation request:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-compile \
  --project-root /path/to/UnityProject \
  --target StandaloneOSX \
  --option-flag DevelopmentBuild \
  --extra-define MY_DEFINE
```

## Client Templates

Planned client adapters live under:

- `templates/clients/codex/`
- `templates/clients/claude-code/`
- `templates/clients/cursor/`
- `templates/clients/generic/`

These templates document how different MCP-capable clients should be pointed at
the same local service as the stdio layer becomes validated in real clients.
