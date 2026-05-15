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
- `BUILD_AUTOMATION.md`
- `SMOKE_TESTS.md`
- `LICENSE.md`
- `Designs/`
- `Retros/`
- `Reports/`

Related `xuunity` protocol guidance:
- `AIRoot/Modules/XUUnity/knowledge/mcp_scenario_authoring.md` for reusable scenario ordering and settle-boundary rules

Current distilled lessons:
- `Retros/2026-05-11_operator_and_backend_lessons.md`

Author:
- Siarhei Khalandachou
- LinkedIn: `https://www.linkedin.com/in/khalandachou/`

## Current Status

This is a working lightweight Unity MCP service with substantial same-host
editor hardening already in place.

It is still not the final production platform, but it is no longer only a thin
prototype.

Current architecture milestone:

- explicit per-project `BridgeRegistry` routing
- explicit per-project `ProjectContext`
- per-project transport selection and transport metadata
- formal discovery and reconciliation across:
  - bridge state
  - host editor session state
  - process-table evidence
  - bridge-enabled project config
- host health and ANR classification scaffold
- structured grouped state while preserving flat compatibility keys
- explicit in-memory context pruning for stale offline project contexts

What exists now:
- install/init script
- public clean-project Unity version-matrix runner
- external stdio server scaffold
- embedded Unity package template
- version-aware package manifest templates for `2021/2022` and `6000+`
- file IPC layout
- Unity editor heartbeat
- Unity capability probe and persisted health report
- Unity-side request handling for:
  - `unity.status`
  - `unity.capabilities.get`
  - `unity.health.probe`
  - `unity.build_target.get`
  - `unity.build_target.switch`
  - `unity.console.tail`
  - `unity.scene.snapshot`
  - `unity.scene.assert`
  - `unity.tests.run_editmode`
  - `unity.tests.run_playmode`
  - `unity.compile.player_scripts`
  - `unity.compile.matrix`
  - host-composed build-config compile matrix routing through `unity.compile.matrix`
  - `unity.editor.quit`
  - `unity.playmode.state`
  - `unity.playmode.set`
  - `unity.game_view.configure`
  - `unity.game_view.screenshot`
  - `unity.edm4u.resolve`
  - `unity.sdk.dependency.verify`
  - `unity.scenario.validate`
  - `unity.scenario.run`
  - `unity.scenario.result`
  - compact host/tool surfaces for low-token polling:
    - `unity_status_summary`
    - `unity_scenario_result_summary`
  - public maintenance cleanup surface:
    - `unity_maintenance_prune`
- MCP `initialize`
- MCP `tools/list`
- MCP `tools/call`
- host-side per-project diagnostics and registry helpers:
  - `project-discovery-report`
  - `request-status-summary`
  - `request-final-status`
  - `request-cancel`
  - `request-stale-cleanup`
  - `request-latest-status`
  - `request-scenario-result-summary`
  - `request-scenario-results-list`
  - `request-scenario-result-latest`
  - `registry-context-report`
  - `registry-prune-contexts`
- additive request-scoped evidence on successful same-host editor responses and
  `request-final-status`:
  - `structured_timing`
  - `artifact_manifest`
- additive host prerequisite reporting on compact discovery/status/final-status
  surfaces:
  - `host_prerequisites`
- additive stale request artifact surfacing on compact discovery/status/final-status
  surfaces:
  - `stale_request_artifacts`
- public wrapper auto-sync of the installed local helper before launch:
  - refresh from the current local `AIRoot` template files instead of trusting a stale `~/.codex-tools` copy
- host-side editor session safety helpers:
  - `request-editor-quit`
  - `restore-editor-state`
  - healthy-editor reuse before forced open
  - post-launch verification that a real editor process appeared for the target project
  - stale bridge and stale lock guards on editor open
  - `batch-compile` for non-interactive compile validation when the target project is closed
  - `batch-compile-matrix` for non-interactive define-matrix validation when the target project is closed
  - `batch-build-config-compile-matrix` for config-driven non-interactive matrix validation when the target project is closed
  - `batch-editmode-tests` for deterministic non-interactive EditMode tests when the target project is closed
  - `batch-test-framework-version-regression` for Phase 0 `com.unity.test-framework` version sweeps across the interactive MCP and closed-project batch lanes
  - `batch-build-player` for plain Unity batch builds when the project is closed
  - `request-edm4u-resolve` for whitelisted External Dependency Manager resolver execution
  - `request-sdk-dependency-verify` for generated SDK dependency artifact checks
  - `arrange-unity-windows` for best-effort macOS tiling of running Unity editor windows
- public reusable smoke runners:
  - `templates/smoke/run_request_abandoned_fault_suite.sh`
  - `templates/smoke/run_transport_matrix_suite.sh`
  - `templates/smoke/run_lifecycle_stress_suite.sh`
  - `templates/smoke/run_lifecycle_fault_injection_suite.sh`
  - `templates/smoke/run_multi_project_acceptance_suite.sh`
  - `templates/smoke/run_phase2_divergence_suite.sh`
  - `templates/smoke/run_phase3_health_policy_suite.sh`
  - `templates/smoke/run_post_change_validation.sh`
  - `templates/smoke/run_playmode_settled_state_regression.sh`
  - `templates/smoke/run_playmode_lifecycle_retry_smoke.sh`
  - `templates/smoke/run_smoke_suite.sh`
- scenario second-wave steps:
  - `assert_scene`
  - `compile_player_scripts`
  - `tests_run_editmode`
  - `game_view_configure`
  - `project_defined_hook`
- public project-action support helpers:
  - `Editor/ProjectActions/XUUnityLightMcpLocalDataCleaner.cs` for reusable editor-side clearing of `PlayerPrefs` and `Application.persistentDataPath`
- public SDK update validation helpers:
  - typed EDM4U resolver execution through whitelisted menu paths
  - generated SDK dependency artifact verification for Android resolver XML, Gradle templates, Podfile.lock, and similar project-local outputs

What does not exist yet:
- production-hardening of the stdio server
- broader real-client validation in Codex and other MCP clients
- richer second-wave read operations
- more polished host-local wrappers and repo-aware helpers
- device/runtime automation layers beyond editor-bound scenario automation
- shared `xuunity` protocol recipes for scenario-driven workflows
- public generic batch-build execution adapters beyond compile validation and build-target switching

What is already materially hardened:

- request recovery across bridge generation/session changes
- per-project routing for more than one Unity consumer
- exact `-projectPath` process ownership matching
- recovery-aware discovery for:
  - `live_process_only`
  - `stale_bridge_state`
  - `stale_host_session`
  - `bridge_disabled`
- health-aware recovery guidance for stale or ANR-suspected editors
- structured state grouping through `transport_state` and `state_groups`

## Goal

Provide one small service that can evolve into the default `xuunity` Unity MCP path with:
- tiny install surface
- zero player-build footprint by default
- no project settings mutation
- easy project removal
- clear project targeting
- easy extension with new tool adapters
- support for more than one AI client

## Quick Operator Rules

Use this README for the canonical surface.
Use the supporting docs when you need the deeper rationale:
- `BUILD_AUTOMATION.md` for lane selection and build-policy rules
- `COMPARISON.md` for backend selection rules
- `Retros/2026-05-11_operator_and_backend_lessons.md` for distilled operator lessons

Default operating rules:

1. Use interactive MCP for:
   - editor status
   - capability and health probes
   - scene inspection
   - compile validation
   - bounded smoke flows
   - play mode and Game View control
2. Use batch helpers for:
   - artifact builds
   - long-running export flows
   - deterministic closed-project compile or EditMode validation
3. For build-sensitive questions, trust:
   - process exit
   - generated artifact and generated manifest/plist output
   - compact build summary artifacts
   over source-only reasoning
4. Prefer backends that produce trustworthy final validation accounting over backends that merely expose more tools

Scenario authoring rule:

- After project-defined hooks or other scenario steps that can mutate build profiles, scripting defines, packages, assets, or project settings, use a settle-aware step such as `project_refresh` before compile, PlayMode, screenshots, scene inspection, or assertions. A hook success means the mutation was requested or applied; it does not by itself prove Unity is settled for the next step.

## macOS Window Arrangement

`arrange-unity-windows` is a host-side helper for tiling already-running Unity
editor windows on the main macOS display. It is intentionally outside the Unity
package because it uses AppleScript and host process inspection.

Run through the wrapper:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  arrange-unity-windows \
  --include-all-running
```

Focus one editor after tiling:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  arrange-unity-windows \
  --include-all-running \
  --focus-pid 12345
```

Use `--required` when a caller should fail if the windows cannot be moved.
Without `--required`, unsupported platforms, no running Unity editors, or missing
macOS Accessibility permission are reported as JSON without failing the command.

On macOS, the process that launches the wrapper must have Accessibility access:

1. Open System Settings.
2. Go to Privacy & Security -> Accessibility.
3. Enable the terminal or IDE process that runs the wrapper.
4. Rerun `arrange-unity-windows`.

## Files

- `init_xuunity_light_unity_mcp.sh`
- `run_multi_project_batch_compile_matrix.sh`
- `run_multi_project_gui_test_subset.sh`
- `run_unity_version_matrix.sh`
- `xuunity_light_unity_mcp.sh`
- `arrange_unity_windows.py`
- `SMOKE_TESTS.md`
- `templates/run.sh`
- `templates/server.py`
- `templates/scenarios/`
- `templates/smoke/`
- `templates/clients/`
- `templates/package-manifests/`
- `templates/unity-package/`
- `Designs/`
- `Retros/`
- `Reports/`

## Unity Version Matrix Runner

Use the public matrix runner when the goal is to create clean projects across
multiple installed Unity editors and run the baseline MCP regression contract.

Canonical entrypoint:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/run_unity_version_matrix.sh
```

Current runner behavior:

- if no Unity versions are passed, it auto-discovers installed editors on the current host
- if specific Unity versions are passed, it runs only those versions
- current default discovery roots are:
  - macOS:
    - `/Applications/Unity/Hub/Editor`
  - Windows:
    - `C:\Program Files\Unity\Hub\Editor`
    - legacy locate-style fallbacks under `C:\Program Files\Unity*`
  - Linux:
    - `~/Unity/Hub/Editor`
    - `/opt/Unity/Hub/Editor`
    - `/opt/unity/Hub/Editor`
- if your Hub editor location is custom, set `XUUNITY_UNITY_EDITOR_ROOTS` to one or more roots separated by the platform path separator

Useful commands:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/run_unity_version_matrix.sh --list-detected
```

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/run_unity_version_matrix.sh \
  2021.3.58f1 \
  2022.3.67f2 \
  6000.0.61f1
```

The runner still needs a valid Unity license for each editor version it opens.

## Multi-Project Batch Compile Runner

Use the public batch compile runner when the goal is throughput across multiple
Unity projects without paying GUI startup cost per project.

```bash
AIRoot/Operations/XUUnityLightUnityMcp/run_multi_project_batch_compile_matrix.sh \
  --repo-root /path/to/repo-with-unity-projects \
  --parallelism 4
```

Current behavior:

- auto-discovers direct child Unity projects under `--repo-root`
- filters to projects that already declare `com.xuunity.light-mcp`
- optionally recovers/closes live editors first
- runs `batch-build-config-compile-matrix` in parallel
- emits compact per-project summaries plus an aggregate final result
- keeps `results_dir` on disk by default so later runners can reuse it

Use explicit selection when the batch should target only a subset:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/run_multi_project_batch_compile_matrix.sh \
  --repo-root /path/to/repo-with-unity-projects \
  --parallelism 2 \
  --project-root BallSort \
  --project-root Sudoku
```

## Multi-Project GUI Test Subset Runner

Use the GUI subset runner after a green batch compile pass when the remaining
work needs a live editor lane.

```bash
AIRoot/Operations/XUUnityLightUnityMcp/run_multi_project_gui_test_subset.sh \
  --repo-root /path/to/repo-with-unity-projects \
  --parallelism 3
```

Recommended route for a true green subset:

1. run `run_multi_project_batch_compile_matrix.sh`
2. reuse its `results_dir`
3. feed that into the GUI subset runner:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/run_multi_project_gui_test_subset.sh \
  --repo-root /path/to/repo-with-unity-projects \
  --from-batch-results /absolute/path/to/results_dir \
  --parallelism 3
```

Current behavior:

- selects projects from explicit roots, a prior batch results dir, or auto-discovery
- runs per project:
  - `recover-editor-session`
  - `ensure-ready --open-editor`
  - `request-editmode-tests`
  - `request-playmode-tests`
  - `restore-editor-state`
- keeps test requests strictly sequential inside each project
- defaults to `--parallelism 3`
- keeps cross-project GUI work parallel while preserving per-project request
  serialization inside each editor session
- auto-arranges Unity editor windows on macOS after `ensure-ready`; override
  with `--window-arrangement off` or make it strict with
  `--window-arrangement required`

## Runtime Timeout Config

Interactive timeout defaults are now loaded from JSON instead of being fixed in
code only.

Public default file:

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/xuunity_light_unity_mcp_runtime_defaults.json`

Override precedence, lowest to highest:

1. public defaults in `AIRoot`
2. repo override:
   - `AIOutput/Operations/XUUnityLightUnityMcp/runtime_config.json`
3. project override:
   - `AIOutput/Projects/<ProjectName>/Operations/XUUnityLightUnityMcp/runtime_config.json`
4. local mutable project override:
   - `<Project>/Library/XUUnityLightMcp/config/runtime_config.json`
5. user override:
   - `~/.codex/xuunity-light-unity-mcp.runtime_config.json`
6. explicit environment override file:
   - `XUUNITY_LIGHT_UNITY_MCP_RUNTIME_CONFIG`

Current public safe defaults when no override is present:

- `unity.project.refresh`: `180000`
- `unity.compile.player_scripts`: `180000`
- `unity.compile.matrix`: `300000`
- `unity.tests.run_editmode`: `300000`
- `unity.tests.run_playmode`: `300000`
- `unity.playmode.set`: `180000`
- `unity.scenario.run`: `600000`

Inspect the merged config actually seen by the installed helper:

```bash
AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  runtime-config-show \
  --project-root /path/to/UnityProject
```

When a request command omits `--timeout-ms`, these merged defaults are now used
for the host request budget and post-reset recovery budget.

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

Wrapper commands for mode switching:

```bash
AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  devmode \
  --project-root /path/to/UnityProject
```

```bash
AIRoot/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh \
  prodmode \
  --project-root /path/to/UnityProject
```

Behavior:

- `devmode` rewrites `Packages/manifest.json` directly to the local `AIRoot` `file:` source:
  - `file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package`
- `devmode` must not create a project-local mirror such as:
  - `<Project>/XUUnityLightMcpPackageSource/com.xuunity.light-mcp`
- `prodmode` rewrites `Packages/manifest.json` to a git-pinned dependency using:
  - the current `AIRoot` `origin` URL
  - the current committed `AIRoot` `HEAD`
- `prodmode` now fails before rewriting the manifest when the current `AIRoot` `HEAD`
  has not yet been published on the remote
- both commands remove the `com.xuunity.light-mcp` entry from `Packages/packages-lock.json`
  so Unity is forced to re-resolve the package honestly on the next refresh/reopen
- `prodmode` intentionally pins committed state only; uncommitted local `AIRoot`
  changes are not part of the resolved package
- project-specific commands should live in a host-local wrapper or adapter
  outside public `AIRoot`

Already-open editor rule after `devmode`:

- if `ensure-ready` reuses an already-open editor session, that does not by
  itself prove Unity has re-resolved the package source switch yet
- in that case, prefer this compact settle path before compile/tests/scenarios:
  1. `ensure-ready`
  2. `request-project-refresh`
  3. `request-status-summary`
  4. only then continue with compile or smoke work
- if the refresh request crosses lifecycle churn and the wrapper loses the final
  payload, recover with:
  - `request-final-status --project-root <project> --request-id <id>`
  - if that summary reports `operation_outcome=submitted_lost_after_lifecycle_churn`,
    verify the effect first, for example bridge health, package resolution, or
    other direct project evidence, before blind retry

## Scaffold Install

Host prerequisites:
- macOS system shell tools are enough for the scaffold checks; `ripgrep` is recommended for faster local checks but not required
- when `rg` is available the shell helpers use it; otherwise they fall back to `grep` and print an install hint
- `python3` must be available; the helper supports the system Python 3.9 line and newer

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
  - directly supports the public `devmode` and `prodmode` package-source switches
  - directly supports `arrange-unity-windows`
  - auto-syncs the installed helper from the local `AIRoot` templates when this
    checkout has git metadata
  - falls back to the installed helper in `~/.codex-tools/` for request commands

Optional Unity project scaffold:
- manifest entry:
  - `"com.xuunity.light-mcp": "file:../../AIRoot/Operations/XUUnityLightUnityMcp/templates/unity-package"`
- local activation file only when explicitly enabled:
  - `<Project>/Library/XUUnityLightMcp/config/bridge_config.json`
- package-declared dependency for the `unity_tests_run_editmode` operation:
  - `com.unity.test-framework`

## Safety Notes

- operator lane-selection and build-evidence rules are defined in:
  - `BUILD_AUTOMATION.md`
- backend-comparison and validation-trust rules are defined in:
  - `COMPARISON.md`
- distilled public lessons from earlier evaluation and onboarding work live in:
  - `Retros/2026-05-11_operator_and_backend_lessons.md`
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

Keep one operating distinction explicit:

- the interactive lane is the control plane for editor-aware work
- the batch lane is the data plane for long-running artifact production

Do not treat `unity.scenario.run` as the primary correctness waiter for
artifact builds. Use batch helpers when success should be judged by process exit
and generated outputs rather than transport survival.

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

For compile-only and EditMode-test-only validation, the public host layer now also exposes an approved closed-project batch lane:
- `batch-compile`
- `batch-compile-matrix`
- `batch-build-config-compile-matrix`
- `batch-editmode-tests`
- `batch-test-framework-version-regression`

That batch lane is intentionally narrower than `interactive_mcp`:
- valid for compile and deterministic EditMode test claims
- not valid for Play Mode, Game View, scene-state inspection, or interactive smoke

Operational note:
- the scenario lane is intentionally serialized
- if a workflow needs parallel long-running work or transport-independent build
  closeout proof, move it to batch helpers instead of stacking more waiting
  logic onto scenarios

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

Bridge version `9` adds host-safe editor closeout support and stronger open-state hygiene:

- `unity.editor.quit` is now a core bridge operation
- the host can track whether it opened Unity for the current validation session
- `restore-editor-state` can now return a host-opened project back to closed
- `restore-editor-state` is bounded on process-exit proof and must surface an
  explicit closeout classification such as `closed_via_unity_editor_quit`,
  `quit_ack_without_exit_sigterm_recovered`, or `quit_ack_without_exit`
- stale bridge state with a dead `editor_pid` is treated as offline instead of reusable
- open-editor no longer blindly launches a second Unity instance for the same project when a stale bridge or lock is present
- scenario-result polling now tolerates transient read glitches during terminal-result waits instead of failing the whole scenario on the first closed response

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

## Unity Version Validation Status

Keep Unity-version claims just as narrow as transport claims:

- report `live-proven` only for Unity editor versions where the clean-project MCP regression was actually run
- do not infer `2021 LTS` or `2022 LTS` support from a successful `6000.x` run
- treat the package manifest minimum as part of the support contract

Current package declaration:

- `templates/unity-package/package.json`
  - `"unity": "6000.0"`

Current compatibility strategy for legacy editors:

- keep the checked-in base package under `templates/unity-package/` as the `6000+` line
- generate a version-aware package source per project when wiring older editors
- select the package manifest from:
  - `templates/package-manifests/unity-package-2021_2022.json`
  - `templates/package-manifests/unity-package-6000.json`

Live-proven on this macOS host by clean-project regression on `2026-05-07`:

| Unity version | Result | Notes |
| --- | --- | --- |
| `2021.3.58f1` | `live-proven` | full clean-project MCP regression passed with the version-aware generated package source |
| `2022.3.62f3` | `live-proven` | full clean-project MCP regression passed with the version-aware generated package source |
| `2022.3.67f2` | `live-proven` | full clean-project MCP regression passed with the version-aware generated package source |
| `6000.0.58f2` | `live-proven` | full clean-project MCP regression passed |
| `6000.0.61f1` | `live-proven` | full clean-project MCP regression passed |
| `6000.2.14f1` | `live-proven` | full clean-project MCP regression passed |
| `6000.3.3f1` | `live-proven` | full clean-project MCP regression passed |
| `2021.3.45f2` | `not live-proven on this host` | clean-project creation was blocked by editor licensing before MCP validation |

Regression contract used for the `live-proven` rows:

1. create clean project
2. add `com.xuunity.light-mcp` as a local `file:` package
3. enable the bridge
4. run `ensure-ready`
5. run `request-status`
6. run `request-health-probe`
7. run `request-capabilities`
8. run `interactive_acceptance_smoke.json`
9. run `refresh_contract_smoke.json`
10. run `compile_contract_smoke.json`

Operational rule:

- if a version has not passed that full clean-project route on the current host, do not label it `live-proven`
- if the target editor is older than `6000`, use the version-aware generated package-source route instead of assuming the checked-in `6000` package manifest is directly consumable
- current pre-`6000` proof is for the generated local package-source route used by installer/devmode, not for the `prodmode` git-pinned route
- the public runner now auto-discovers installed editors on macOS, Windows, and Linux, but `live-proven` still requires an executed host run on that specific machine/OS

Current request-lifecycle event set now includes:

- `request_started`
- `request_completed`
- `request_abandoned`
- `request_reclassified`
- `request_cancelled`
- `request_cancel_requested`

Operational note:

- in one live validation session, repeated `refresh/resolve` alone was not sufficient to hot-pick up the latest file-package code from the external `AIRoot` path
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

Send `unity.status` and return a compact stabilization summary:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-status-summary \
  --project-root /path/to/UnityProject
```

Resolve final disposition for a request id after transport churn:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-final-status \
  --project-root /path/to/UnityProject \
  --request-id <request-id>
```

Request best-effort host-side cancellation for a known request id:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-cancel \
  --project-root /path/to/UnityProject \
  --request-id <request-id>
```

Clean up stale request inbox/outbox artifacts after the lane is stable:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-stale-cleanup \
  --project-root /path/to/UnityProject \
  --dry-run
```

If the wrapper reports a lifecycle reset or response loss, treat that command as
the default next step. Do not retry blindly before resolving the request id.
The returned summary is intentionally bounded on incomplete evidence:

- `operation_outcome=submitted_lost_after_lifecycle_churn` means transport
  submission happened but Unity-journal proof never appeared before the bridge
  stabilized again
- `operation_outcome=retryable_after_lifecycle_reset` means a lifecycle reset
  explicitly reclassified the request as retryable
- `operation_outcome=abandoned_after_lifecycle_reset` means Unity recorded
  abandonment rather than completion
- `operation_outcome=cancelled_before_unity_start` means the host helper removed
  a queued `file_ipc` request before Unity journal ownership was observed
- `operation_outcome=cancellation_requested_in_flight` means the host helper
  recorded cancellation intent, but this lane does not yet claim Unity-side
  interruption of an already in-flight request
- `recommended_recovery_command` should echo the exact follow-up command for the
  same `request_id`
- when payload evidence is available, the returned summary now also includes:
  - `structured_timing`
  - `artifact_manifest`
  - `host_prerequisites`

Current cancellation scope is intentionally narrow:

- `request-cancel` is a best-effort host-side helper for the same-host editor lane
- it can cancel a queued `file_ipc` request before Unity-side `request_started`
  ownership is observed
- for already in-flight work, it records structured cancellation intent and
  relies on `request-final-status` to show whether the request later completed,
  was abandoned, or remained retryable

Current stale-request cleanup scope is also intentionally narrow:

- compact discovery/status/final-status summaries now surface
  `stale_request_artifacts`
- `host_prerequisites.checks.stale_requests` exposes a bounded warning when
  old inbox/outbox files are eligible for cleanup
- `request-stale-cleanup` only removes request artifacts that are old and
  already terminal or clearly unclaimed in the current same-host editor lane

Successful same-host editor operations now add the same two fields directly to
their JSON payloads without replacing the existing operation-specific contract.

Compact status/discovery/final-status summaries now also include a bounded
`host_prerequisites` object for the current same-host editor lane. It reports:

- whether the lane is immediately ready
- blocking prerequisite codes such as `bridge_disabled`, `editor_not_running`,
  `transport_not_ready`, or package wiring issues
- per-check details for bridge enablement, package dependency presence, live
  editor detection, and transport readiness

Recover the latest matching request when the wrapper stalled before surfacing a
usable `request_id`:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-latest-status \
  --project-root /path/to/UnityProject \
  --operation unity.compile.player_scripts \
  --operation unity.compile.matrix
```

Recovery rule:

- if you already have a `request_id`, prefer `request-final-status`
- if you do not have a `request_id`, prefer `request-status-summary` first
- once the bridge is stable, use `request-latest-status` for the relevant
  operation class before blind retry
- retry only after the compact recovery summary says the earlier request did not
  complete
- `request-final-status` is the canonical truth source for lifecycle-reset
  incidents; do not treat the original wrapper error as the final verdict when a
  real `request_id` exists
- when a test request returns `tests_busy`, recover the in-flight run with
  `request-latest-status --operation unity.tests.run_editmode` or
  `request-latest-status --operation unity.tests.run_playmode` before retrying

Request-ownership rule:

- after a request is successfully dispatched, the helper now emits one compact
  stderr acknowledgement before the long wait:
  - `request_submitted`
  - `operation`
  - `request_id`
  - `transport`
  - bridge identity
- treat that acknowledgement as proof that recovery by `request_id` is now
  available even if the final response is later delayed or lost
- if the helper emits `request_not_submitted`, treat that as proof that the
  request never gained Unity-side ownership and recover by bridge/editor status
  first instead of searching for a completed request id
- if a wrapper-side lifecycle-reset path surfaces `result_trust_class`:
  - `unity_completed_confirmed` means Unity completed and the wrapper has direct
    proof
  - `unity_completed_after_lifecycle_reset` means Unity completed across bridge
    churn and the host recovered that truth by `request_id`
  - `wrapper_failed_unity_unproven` means the wrapper/session lost trust in the
    result after Unity accepted the request; that is not equivalent to a
    Unity-side test failure
- for CLI failures, the helper also emits a short human-readable stderr summary
  before the JSON error payload so operators can distinguish:
  - request dispatched
  - request not dispatched
  - next recovery step

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
- `templates/scenarios/compile_contract_smoke.json`

Generic shell runners are provided under:

- `templates/smoke/run_post_change_validation.sh`
- `templates/smoke/run_playmode_lifecycle_retry_smoke.sh`
- `templates/smoke/run_smoke_suite.sh`

The compact post-change runner now applies compile-first discipline. When C#
scripts changed, the fast compile gate is a precondition before EditMode,
PlayMode, scenario, or GUI smoke validation unless the task is explicitly
investigating a compile failure:

1. `ensure-ready`
2. `request-status`
3. `request-health-probe`
4. fast compile gate
5. interactive and contract scenarios
6. optional PlayMode parity and lifecycle-retry smokes when a representative
   PlayMode test is supplied

If a closed-project batch command reports `editor_running_batch_conflict`, treat
that as `unity_outcome=not_started`, not as product or validation failure. Run
the surfaced recovery command, verify the editor process has exited with
`restore-editor-state` or `recover-editor-session`, then rerun the batch compile
gate before starting tests or heavier smoke work.

## Token Discipline

When a compact summary surface exists, prefer it before any raw high-churn
request loop.

Preferred order:

1. `request-status-summary`
2. `request-final-status <request_id>` after lifecycle churn or wrapper-side
   response loss when a real request id is already known
3. `request-latest-status --operation ...` when the wrapper stalled before a
   usable request id was surfaced
4. `unity_scenario_result_summary` for persisted scenario outcome checks
5. `request-scenario-results-list` or `request-scenario-result-latest` for
   host-side browsing of persisted scenario outputs
6. raw `unity.scenario.result` only when the compact summary is insufficient
7. raw `prepare.log` and `build.log` only after compact failure summary surfaces
   are exhausted

Operator rule:

- treat repeated `unity.scenario.result` polling as an expensive fallback, not
  the default steady-state observation path
- if transport continuity was lost and a request id is known, recover by
  `request_id` before retrying the operation
- if transport continuity was lost and no request id is known, stabilize the
  bridge first and then recover by operation class with `request-latest-status`
- if `restore-editor-state` reports `quit_ack_without_exit`, do not treat the
  earlier quit acknowledgement as proof of real shutdown; inspect the surfaced
  `recommended_recovery_command` and verify the remaining editor PID set
- if `request-final-status` reports:
  - `request_submitted=true`
  - `request_observed_in_unity_journal=false`
  - `bridge_changed_since_submission=true`
  - `operation_outcome=submitted_lost_after_lifecycle_churn`
  treat that as a wrapper recovery gap after real transport submission, not as
  proof that Unity definitely did nothing
- if `request-final-status` reports
  `result_trust_class=wrapper_failed_unity_unproven`, treat that as "Unity
  accepted the request, but the wrapper lost trustworthy completion proof"
- a workflow that jumps straight to raw `unity.scenario.result`, `prepare.log`,
  or `build.log` while a compact summary surface already exists is an operator
  experience regression

Persisted scenario result browsing now has two host-side read-only utilities:

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-scenario-results-list \
  --project-root /path/to/UnityProject \
  --scenario-name acceptance_smoke \
  --limit 10
```

```bash
python3 ~/.codex-tools/xuunity-light-unity-mcp/server.py \
  request-scenario-result-latest \
  --project-root /path/to/UnityProject \
  --scenario-name acceptance_smoke
```

Those summaries surface at least:

- `run_id`
- `status`
- `started_at_utc`
- `completed_at_utc`
- `duration_seconds`
- `result_path`
- `artifact_manifest`
- `structured_timing`

Batch rule:

- batch commands print `summary_file` plus a compact `result_summary` or
  `build_result_summary` by default
- on failed prepare/build/validation paths, read the summary artifact first and
  inspect `raw_log_path` only when the summary is insufficient

## Cross-Platform Validation Kit

Public package commands are platform-neutral. A host or project can wrap them in local scripts, but the proof route should stay the same in shape:

1. `ensure-ready`
2. compact post-change validation
3. lifecycle stress
4. request-abandoned fault validation
5. optional transport matrix validation when more than one transport is enabled on that host

For project-local examples of this pattern, see checked-in host wrappers under a project-specific folder such as:

- `AIOutput/Operations/XUUnityLightUnityMcp/smoke/<ProjectName>/`

Those project-local wrappers are evidence routes, not public proof for every host.

## Client Templates

Planned client adapters live under:

- `templates/clients/codex/`
- `templates/clients/claude-code/`
- `templates/clients/cursor/`
- `templates/clients/generic/`

These templates document how different MCP-capable clients should be pointed at
the same local service as the stdio layer becomes validated in real clients.
