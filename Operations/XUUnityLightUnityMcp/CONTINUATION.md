# XUUnity Light Unity MCP Continuation

Date: `2026-05-05`
Status: `active continuation note`

## Current Baseline

This service is past the design-only stage.

It now has:
- a working stdio MCP server
- an editor-only Unity bridge
- capability probing and gating
- compile and test validation
- play mode control
- Game View configure and screenshot support
- asynchronous scenario automation with persisted results
- host-side startup helpers with fail-fast policy for interactive editor startup

The public `xuunity` protocol layer also now understands validation-lane
selection.

## What Is Already Implemented

External server:
- minimal stdio MCP layer
- `initialize`
- `tools/list`
- `tools/call`
- local diagnostics helpers
- `open-editor`
- `ensure-ready`
- `request-editor-quit`
- `restore-editor-state`
- host-local package-source mode switching:
  - `devmode`
  - `prodmode`

Unity bridge:
- heartbeat state
- request pump
- capability probe
- capability gating
- status and health operations
- compile validation
- edit-mode test execution
- console tail
- scene snapshot
- play mode control
- Game View configure and screenshot
- scenario validation
- asynchronous scenario runs
- persisted scenario results

Scenario second-wave steps:
- `compile_player_scripts`
- `tests_run_editmode`
- `game_view_configure`
- `project_defined_hook`

Public reusable smoke assets:
- `templates/scenarios/`
- `templates/smoke/run_post_change_validation.sh`
- `templates/smoke/run_smoke_suite.sh`

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
- `Library/XUUnityLightMcp/logs/`

## Key Decisions

- editor-only package
- disabled by default
- removable with minimal project residue
- no `ProjectSettings` mutation
- no runtime asmdef
- no broad define mutation
- compile checks should use Unity APIs, not platform switching
- version-sensitive features should be probed and gated
- Game View persistence must be opt-in, not default
- interactive startup should fail fast on compile and package blockers instead of hanging on heartbeat waits

## Validation Lane Model

The shared public `xuunity` core now has a canonical lane model:

- `interactive_mcp`
- `batch_compile`
- `scenario`

Relevant public files:
- `../../Modules/XUUnity/knowledge/validation_lanes.md`
- `../../Modules/XUUnity/tasks/start_session.md`
- `../../Modules/XUUnity/tasks/validation_plan.md`
- `../../Modules/XUUnity/skills/tests/unity_test_runner_workflow.md`
- `../../Operations/AI_PROTOCOL_HANDBOOK.md`

Meaning:
- do not re-open the old question of whether shell compile, MCP, and scenario
  automation are equivalent
- lane selection is now part of the protocol contract
- new work should extend that model rather than inventing another validation-path taxonomy

## What A New Chat Should Check First

1. Unity version for the consumer project
2. whether the package is installed through Git or local embedding
3. whether the bridge is enabled
4. `bridge_state.json`
5. `capabilities_report.json`
6. `unity.status`
7. `unity.capabilities.get`
8. `unity.health.probe`

Only after that:
- compile
- tests
- play mode
- Game View operations
- scenario runs

## What A New Chat Should Read First

For reusable MCP work:

1. `README.md`
2. `DESIGN.md`
3. `ROADMAP.md`
4. `AI_INTEGRATION.md`
5. `COMPARISON.md`
6. `Reports/2026-05-05_progress_status.md`
7. `Reports/2026-05-05_xuunity_protocol_integration_status.md`
8. this continuation note

For shared protocol integration work:

1. `../../Modules/XUUnity/knowledge/validation_lanes.md`
2. `../../Modules/XUUnity/tasks/start_session.md`
3. `../../Modules/XUUnity/tasks/validation_plan.md`
4. `../../Modules/XUUnity/skills/tests/unity_test_runner_workflow.md`
5. `../../Operations/AI_PROTOCOL_HANDBOOK.md`

## What Is Already Proven

- the service can connect to a real Unity project
- compile can run for explicit targets without switching active platform
- edit-mode tests can run through the bridge
- play mode can be entered and exited
- Game View can be configured and captured
- scenario runs can persist results
- second-wave scenario steps can run and report structured results
- startup helpers can fail fast on interactive compile blockers and package-resolution failures
- host-opened editor sessions can be restored to the original closed state after validation
- baseline smoke orchestration can be reused from public `AIRoot` templates while keeping consumer-specific fixtures host-local

## What Is Not Yet Proven

- broad multi-client production use
- stable behavior across a wider Unity version matrix
- device automation
- profiler export and analysis
- runtime bottleneck evidence
- resumable long-running automation
- richer scenario assertions beyond the current core

## Current Risk Areas

- stdio layer still needs hardening
- Game View support still depends on reflection
- deeper project inspection surface is still thin
- no runtime evidence pipeline yet
- no device-side artifact capture yet

## Recommended Next Work

1. harden the scenario lane:
   - richer assertions
   - better result summaries
   - clearer failure taxonomy
2. add scenario-result utilities:
   - last-result fetch
   - result listing
   - artifact path surfacing
3. add first runtime evidence adapters:
   - runtime markers
   - frame or state checkpoints
   - controlled project hook outputs
4. design the device layer on top of scenario control:
   - launch
   - screenshot
   - profiler capture
5. broaden proof across more client and host combinations
6. only then move toward autonomous performance and bottleneck workflows

## Important Non-Goals For The Next Chat

Do not spend time re-evaluating:
- heavy third-party Unity MCP backends as the primary solution
- runtime-in-player MCP packaging
- broad reflection-driven dynamic code execution as the default extension model

Those questions are already settled enough for the current phase.
