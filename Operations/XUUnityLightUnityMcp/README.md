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
- `ROADMAP.md`
- `AI_INTEGRATION.md`
- `SMOKE_TESTS.md`
- `LICENSE.md`
- `Reports/`

Author:
- Siarhei Khalandachou
- LinkedIn: `https://www.linkedin.com/in/khalandachou/`

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
  - host-composed build-config compile matrix routing through `unity.compile.matrix`
  - `unity.playmode.state`
  - `unity.playmode.set`
  - `unity.game_view.configure`
  - `unity.game_view.screenshot`
  - `unity.scenario.validate`
  - `unity.scenario.run`
  - `unity.scenario.result`
- MCP `initialize`
- MCP `tools/list`
- MCP `tools/call`
- host wrapper auto-sync of the installed local helper before launch:
  - refresh from the current local `AIRoot` template files instead of trusting a stale `~/.codex-tools` copy
- scenario second-wave steps:
  - `compile_player_scripts`
  - `tests_run_editmode`
  - `game_view_configure`
  - `project_defined_hook`

What does not exist yet:
- production-hardening of the stdio server
- broader real-client validation in Codex and other MCP clients
- richer second-wave read operations
- more polished host-local wrappers and repo-aware helpers
- device/runtime automation layers beyond editor-bound scenario automation
- shared `xuunity` protocol recipes for scenario-driven workflows

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
- `xuunity_light_unity_mcp.sh`
- `SMOKE_TESTS.md`
- `templates/run.sh`
- `templates/server.py`
- `templates/scenarios/`
- `templates/smoke/`
- `templates/clients/`
- `templates/unity-package/`
- `Reports/`

## License

This service is published under the MIT license.

See:
- `LICENSE.md`

Short form:
- free to use
- free to modify
- no warranty
- author assumes no liability for repository, project, build, device, or automation outcomes

## Package Source

Two package-source modes are now supported for same-host Unity consumers:

- `devmode`
  - local `file:` dependency to the current working tree under `AIRoot`
  - best for fast MCP package iteration on the same machine
- `prodmode`
  - git-pinned dependency to the current `AIRoot` `origin` URL and current committed `HEAD`
  - best for CI, build agents, and any consumer that must not depend on a local `AIRoot` checkout

Default direct local dependency shape:

```json
{
  "dependencies": {
    "com.xuunity.light-mcp": "file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package"
  }
}
```

Git-pinned shape:

```json
{
  "dependencies": {
    "com.xuunity.light-mcp": "https://github.com/FoxsterDev/ai-research-hub.git?path=/Operations/XUUnityLightUnityMcp/templates/unity-package#<commit>"
  }
}
```

Use the direct local `file:` route when the consumer should always see the latest
working-tree version from the local `AIRoot`.

Use the git-pinned route when the consumer must resolve the package without any
local `AIRoot` path on disk.

Host-local wrapper commands for mode switching:

```bash
AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  devmode \
  --project-root /path/to/UnityProject
```

```bash
AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  prodmode \
  --project-root /path/to/UnityProject
```

Behavior:

- `devmode` rewrites `Packages/manifest.json` back to the local `file:` source
- `prodmode` rewrites `Packages/manifest.json` to a git-pinned dependency using:
  - the current `AIRoot` `origin` URL
  - the current committed `AIRoot` `HEAD`
- both commands remove the `com.xuunity.light-mcp` entry from `Packages/packages-lock.json`
  so Unity is forced to re-resolve the package honestly on the next refresh/reopen
- `prodmode` intentionally pins committed state only; uncommitted local `AIRoot`
  changes are not part of the resolved package

## Scaffold Install

Install the external scaffold only:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh
```

Install the external scaffold and wire the Unity project to the package in `AIRoot`:

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

Public convenience wrapper:
- `AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh`
  - delegates to `AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh` when that host-local wrapper exists
  - otherwise falls back to the installed helper in `~/.codex-tools/`

Optional Unity project scaffold:
- manifest entry:
  - `"com.xuunity.light-mcp": "file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package"`
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
- `unity_compile_build_config_matrix` resolves build profiles from the project's Unity `*BuildConfiguration.asset` and drives the full target/profile matrix through `unity.compile.matrix`
- target-specific compile validation still depends on the corresponding Unity platform support module being installed on the host
- `unity_capabilities` and `unity_health_probe` expose the probe report to MCP clients so they can avoid unsupported operations instead of learning by failure
- `unity_game_view_configure` uses Unity internal editor reflection and, by default, refuses to create new custom Game View sizes
- if you opt in with `allowCreateCustomSize=true`, `unity_game_view_configure` may create a matching custom Game View size entry in editor user state
- `unity_game_view_screenshot` uses the Game View render texture directly and includes a vertical-flip correction on graphics backends where `graphicsUVStartsAtTop` is true
- `unity.scenario.*` has been live-smoked on a real Unity consumer project with:
  - a playmode enter/screenshot/exit baseline
  - second-wave `game_view_configure`
  - second-wave `compile_player_scripts`
  - second-wave `tests_run_editmode`
  - project-defined scenario hook execution
- scenario `tests_run_editmode` and `compile_player_scripts` steps evaluate product-level payload status, not only transport-level bridge success

## Local Smoke Route

After installing the Unity package into a project and opening the project in Unity:

Or let the host-side wrapper open the editor and fail fast on startup blockers:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  ensure-ready \
  --project-root /path/to/UnityProject \
  --open-editor \
  --background-open \
  --startup-policy fail_fast_on_interactive_compile_block
```

Supported startup policies:
- `fail_fast_on_interactive_compile_block`
- `auto_enter_safe_mode_preferred`
- `batch_compile_lane`

What this does:
- opens Unity with a deterministic log file path under `Library/XUUnityLightMcp/logs/`
- waits for a fresh healthy bridge heartbeat
- inspects `Editor.log` while waiting
- stops early on package-resolution failures or interactive compile blockers instead of hanging forever

## Stability Contract

The host-side wrapper now treats some operations as lifecycle-sensitive instead of fire-and-forget.

Current behavior:
- `unity.project.refresh`
- `unity.compile.player_scripts`
- `unity.compile.matrix`
- `unity.tests.run_editmode`
- `unity.playmode.set`
- `unity.game_view.configure`
- `unity.game_view.screenshot`
- `unity.scenario.run`

For those operations the wrapper may:
- activate Unity before sending the request
- wait for editor idle before sending work
- wait for a post-request settled idle state before claiming success for synchronous operations

Bridge state now exposes additional lifecycle fields under `bridge-state` and `unity.status`:
- `bridge_session_id`
- `bridge_generation`
- `bridge_bootstrap_attached`
- `is_updating`
- `is_playing_or_will_change_playmode`
- `playmode_state`
- `last_pump_utc`
- `last_processed_request_id`
- `pending_request_count`
- `busy_reason`
- `request_journal_directory`
- `request_journal_head`

This is intended to reduce false-success responses where Unity accepted a request but had not yet settled refresh, compile, or playmode work.

Bridge version `5` extends that with first-class lifecycle-state fields:

- each enabled bootstrap writes a new `bridge_session_id`
- each bootstrap increments `bridge_generation`
- `domain_reload_in_progress`
- `asset_import_in_progress`
- `package_operation_in_progress`
- `package_operation_name`
- `script_reload_pending`
- request lifecycle events are written under:
  - `Library/XUUnityLightMcp/journal/requests/`

Bridge version `6` starts moving settle truth into Unity itself for `project_refresh`:

- the bridge now tracks refresh settle state natively
- `bridge-state` and `unity.status` expose:
  - `refresh_settle_pending`
  - `refresh_settle_request_id`
  - `refresh_settle_started_utc`
  - `refresh_settle_completed_utc`
  - `refresh_settle_phase`
  - `refresh_settle_package_resolve_requested`
- successful refresh payloads can now return:
  - `completion_basis: unity_refresh_settle_watcher`
  - `settle_request_id`
  - `settle_phase: settled`

Bridge version `7` extends native settle tracking to compile operations:

- `bridge-state` and `unity.status` now also expose:
  - `compile_settle_pending`
  - `compile_settle_request_id`
  - `compile_settle_started_utc`
  - `compile_settle_completed_utc`
  - `compile_settle_phase`
  - `compile_settle_operation`
- successful compile payloads can now return:
  - `completion_basis: unity_compile_settle_watcher`
  - `settle_request_id`
  - `settle_phase: settled`
- nested scenario `compile_player_scripts` steps now wait for the same native compile settle contract instead of treating API return as final completion

Bridge version `8` extends lifecycle truth further for package and play mode transitions:

- `bridge-state` and `unity.status` now also expose:
  - `package_operation_phase`
  - `playmode_transition_pending`
  - `playmode_transition_request_id`
  - `playmode_transition_action`
  - `playmode_transition_target_state`
  - `playmode_transition_started_utc`
  - `playmode_transition_completed_utc`
  - `playmode_transition_phase`
- successful `unity.playmode.set` payloads can now return:
  - `completion_basis: unity_playmode_transition_watcher`
  - `settle_request_id`
  - `settle_phase: settled`
  - `settle_target_state`
- pending playmode transition state is now persisted across bridge rebootstrap so `enter` can complete with native watcher evidence even when Play Mode recreates the bridge session

This does not yet provide full reconnect recovery, but it gives explicit evidence for:

- bridge rebootstrap after reload
- which session processed a request
- what the last persisted lifecycle event was before a timeout or reconnect
- host-side classification of bridge lifecycle resets during transport waits
- one-shot retry for explicitly idempotent operations after a retryable lifecycle reset
- retained active-request ownership for deferred async operations so `request_abandoned` can be emitted during real in-flight reloads
- Unity-side refresh settle truth instead of host-only inference
- transport metadata in host lifecycle output so the current `file_ipc` path is explicit and a stronger same-host transport can be added behind the same orchestration contract
- cross-platform transport prototype:
  - `file_ipc` remains baseline and fallback
  - `tcp_loopback` is now the first stronger same-host transport option
  - it is designed around `127.0.0.1` TCP so the same transport class can run on macOS, Windows, and Linux without Unix-socket-only assumptions

## Cross-Platform Validation Status

Keep the current transport claim narrow and explicit:

- `tcp_loopback` is portable by design across:
  - macOS
  - Windows
  - Linux
- but runtime proof is host-specific
- a successful macOS run does not prove Windows or Linux behavior by itself

Practical rule:

- report `live-proven` only for hosts where the smoke and fault routes were actually run
- report `portable by design, not yet host-proven` for platforms that have the right transport shape but no executed host evidence yet

If you only have a Mac host, there are three honest options:

1. run real proof on separate Windows and Linux machines
2. run the same suite inside Windows/Linux VMs as an intermediate check
3. keep Windows/Linux as design-level portability claims only

Recommended validation order for a new host:

1. enable the bridge locally and reopen Unity once
2. run `ensure-ready`
3. run the transport regression route for the project
4. run lifecycle stress
5. run the request-abandoned fault route

The right evidence bar for Windows/Linux is host execution, not protocol inference.

Current request-lifecycle event set now includes:

- `request_started`
- `request_completed`
- `request_abandoned`
- `request_reclassified`

Operational note:

- on the current `ApperfunHub` live session, repeated `refresh/resolve` alone was not sufficient to hot-pick up the latest file-package code from the external `AIRoot` path
- the bridge eventually activated the new package code after a real recompilation/rebootstrap cycle
- operationally, that means file-package updates may require more than plain `refresh/resolve`; they may need an actual script/package recompilation cycle, and in the worst case still a full editor reopen

Read the heartbeat state:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
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

Send a direct file-IPC compile-matrix request from a JSON config file:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-compile-matrix \
  --project-root /path/to/UnityProject \
  --config-file /path/to/compile-matrix.json
```

Resolve build profiles from the project's Unity build-config asset and run the Android/iOS matrix:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-build-config-compile-matrix \
  --project-root /path/to/UnityProject
```

Validate or run a scenario JSON file through the scenario bridge operations:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-scenario-validate \
  --project-root /path/to/UnityProject \
  --scenario-file /path/to/scenario.json

python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-scenario-run \
  --project-root /path/to/UnityProject \
  --scenario-file /path/to/scenario.json

python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-scenario-run-and-wait \
  --project-root /path/to/UnityProject \
  --scenario-file /path/to/scenario.json
```

## Public Smoke Contract

See `SMOKE_TESTS.md` for the public reusable MCP smoke baseline.

Generic example scenario templates are provided under:

- `templates/scenarios/interactive_acceptance_smoke.json`
- `templates/scenarios/refresh_contract_smoke.json`

## Cross-Platform Validation Kit

Public package commands are platform-neutral. A host or project can wrap them in local scripts, but the proof route should stay the same in shape:

1. `ensure-ready`
2. compact post-change validation
3. lifecycle stress
4. request-abandoned fault validation
5. optional transport matrix validation when more than one transport is enabled on that host

For project-local examples of this pattern, see the checked-in host wrappers under:

- `AIOutput/Operations/XUUnityLightUnityMcp/smoke/ApperfunHub/`

Those project-local wrappers are evidence routes, not public proof for every host.

## Client Templates

Planned client adapters live under:

- `templates/clients/codex/`
- `templates/clients/claude-code/`
- `templates/clients/cursor/`
- `templates/clients/generic/`

These templates document how different MCP-capable clients should be pointed at
the same local service as the stdio layer becomes validated in real clients.
