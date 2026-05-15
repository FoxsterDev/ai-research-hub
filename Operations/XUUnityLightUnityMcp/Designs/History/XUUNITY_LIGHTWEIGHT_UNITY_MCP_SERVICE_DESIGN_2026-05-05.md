# XUUnity Lightweight Unity MCP Service Design

Date: `2026-05-05`  
Status: `top-level implementation design`  
Scope: define a small, public-safe Unity MCP service that fits `xuunity` better than current heavy community packages

Depends on:
- `historical host-local design source: XUUNITY_UNITY_MCP_EVALUATION_AND_ADAPTER_DESIGN_2026-05-04.md`
- `historical host-local design source: XUUNITY_UNITY_MCP_ADAPTER_CONTRACT_AND_IVAN_SPIKE_DESIGN_2026-05-04.md`
- `historical host-local design source: XUUNITY_UNITY_MCP_FEATURE_MATRIX_AND_POLICY_2026-05-04.md`
- `host-local project runtime-footprint audit evidence`

## Decision

Do not standardize on `IvanMurzak/Unity-MCP` as the long-term `xuunity` Unity MCP backend.

Reason:
- too much dependency mass
- real player-build footprint
- runtime surface we do not want by default
- too broad a capability set for the narrow validation-first workflow that `xuunity` actually needs

Instead, build a custom lightweight Unity MCP service and use existing GitHub projects only as:
- reference implementations
- edge-case research sources
- troubleshooting examples for Unity-specific pitfalls

## Product Goal

Build a small service, structurally similar to `AIRoot/Operations/local MCP operation package/`, that gives Codex a dependable Unity-aware MCP path with:
- tiny install surface
- editor-only project footprint
- no player-build impact by default
- no NuGet restoration
- no Roslyn execution path
- no SignalR/WebSocket/relay stack
- no runtime in-game feature set

The service should optimize for:
- `trust`
- `clarity`
- `small blast radius`
- `fast onboarding`
- `stable validation evidence`

This service must also be:
- easy to extend with new capabilities
- usable from more than one AI client, not only Codex
- able to target Unity `6000.0.58f1` as the baseline supported editor version

## Primary Use Cases

This service exists for the high-value daily `xuunity` loop:

1. verify that Unity is open and reachable
2. inspect current editor state
3. inspect recent console logs
4. inspect active scene snapshot
5. run EditMode tests
6. validate compile matrix across targets and define sets without active platform switch
7. later add bounded read-only project inspection

It does not exist to become a generic AI game platform.

## Non-Goals

Phase 1 must explicitly exclude:
- runtime/in-game MCP
- dynamic C# execution
- reflection method call
- package add/remove
- arbitrary scene mutation
- broad asset mutation
- remote/multi-user deployment
- cloud relay support
- dependency-heavy transport stacks

If a future need appears for any of those, that should be a separate extension, not part of the base service.

Clarification:
- narrow Unity-internal editor reflection is acceptable where Unity exposes no supported public API for the required editor-only workflow
- current examples of acceptable reflection use:
  - reading the Game View render texture for screenshot capture
  - selecting the current Game View size entry

Also exclude from the base service:
- a giant built-in prompt catalog
- agent-specific business logic inside the Unity bridge
- hard coupling between Unity tool code and one AI client product

## Why Build Our Own

The current evidence shows a mismatch between `xuunity` needs and heavyweight Unity MCP packages.

### What we want

- editor-only behavior
- minimal dependencies
- predictable operational surface
- stable JSON outputs
- direct support for `status`, `console`, `scene snapshot`, and `EditMode tests`
- simple same-host Codex integration

### What the heavy package gave us

- successful end-to-end editor validation
- but large dependency and build footprint
- player-facing runtime surface
- broad capability area that exceeds our safe default workflow

So the correct move is not to abandon MCP.
The correct move is to reduce it to the shape we actually need.

## Target Shape

The target should look like a small `AIRoot` operational package, similar in spirit to `local MCP operation package`.

Planned public location:

`AIRoot/Operations/XUUnityLightUnityMcp/`

Planned host-local operational wrapper:

`host-local XUUnityLightUnityMcp wrapper path`

Planned Unity package identity:

`com.xuunity.light-mcp`

## Service Model

The service should have two parts only:

1. a tiny external MCP server process for Codex
2. a tiny Unity Editor bridge package inside the target Unity project

No third process should be required.
No runtime package should be present.
No auto-downloaded binaries should be required.

## Supported Clients

The service should be MCP-client agnostic at the protocol layer.

Primary first-class client:
- Codex

Expected additional clients:
- Claude Code
- Claude Desktop
- Cursor
- Cline / OpenCode-style clients
- Gemini-capable MCP clients

Important rule:
- client support belongs in the external server and setup templates
- client-specific config generation must not leak into the Unity bridge runtime

## Agent Adapter Model

The service should support two extension axes:

1. Unity operation adapters
2. AI client configuration adapters

### 1. Unity operation adapters

Purpose:
- add new MCP tools without bloating the core bridge
- keep each capability isolated and testable

Recommended shape:

```text
Unity bridge core
  -> operation registry
    -> built-in operation adapters
    -> optional project-local operation adapters
```

Adapter examples:
- `status_adapter`
- `console_adapter`
- `scene_snapshot_adapter`
- `editmode_tests_adapter`
- future `assets_find_adapter`

Each adapter should:
- declare `operation_name`
- declare input schema
- execute one narrow Unity behavior
- return one normalized result shape

### 2. AI client configuration adapters

Purpose:
- help users connect non-Codex clients without polluting core logic

Recommended shape:

```text
AIRoot/Operations/XUUnityLightUnityMcp/templates/clients/
  codex/
  claude-code/
  cursor/
  generic/
```

Each client adapter should define:
- MCP config snippet format
- any required run command
- any client-specific notes

This takes the most useful part of `IvanMurzak`'s "configure multiple AI agents" idea, but keeps it outside the Unity plugin.

## High-Level Architecture

```text
Codex client
  -> local stdio MCP server
    -> project-scoped request broker
      -> Unity Editor bridge
        -> Unity Editor APIs
```

### External MCP server

Responsibilities:
- speak MCP to Codex over `stdio`
- validate project targeting
- normalize tool input/output
- manage request IDs and timeouts
- expose only the narrow `xuunity` tool surface

### Unity Editor bridge

Responsibilities:
- run inside Unity Editor only
- poll for requests
- execute supported operations against Editor APIs
- write structured responses
- publish readiness and heartbeat state

## Key Design Choice: Local File IPC First

Phase 1 should use local file-based IPC under the project `Library/` folder, not HTTP.

Recommended project-local IPC root:

`<Project>/Library/XUUnityLightMcp/`

Structure:

```text
Library/XUUnityLightMcp/
  state/
    bridge_state.json
  inbox/
    <request-id>.json
  outbox/
    <request-id>.json
  logs/
    bridge.log
```

### Why file IPC first

- zero network stack
- zero auth/token setup for same-user local use
- no SignalR/WebSocket/HTTP dependencies
- easier cross-platform behavior in early versions
- easier debugging from disk
- lower implementation risk than building transport infrastructure early

### Tradeoff

- not suitable for remote access
- not ideal for multiple simultaneous clients
- less elegant than sockets or HTTP

That tradeoff is acceptable because `xuunity` does not need remote access for Phase 1.

## Why Not HTTP First

HTTP is tempting, but it reintroduces exactly the class of weight we are trying to avoid:
- listener lifecycle issues
- auth and port management
- firewall and collision problems
- more moving parts during editor reloads

HTTP can be added later as an optional transport if the base service proves insufficient.

## Unity Version Support

Baseline target:
- Unity `6000.0.58f1`

Secondary verified target:
- Unity `6000.0.58f2`

Design rule:
- Phase 1 code should be written to work on `6000.0.58f1` first
- any version-dependent API usage must be guarded explicitly
- avoid depending on APIs introduced only in later 6000.x patches

Minimum compatibility practice:
- keep preprocessor guards where needed
- maintain a tiny compatibility shim layer inside the editor bridge
- run smoke validation on both `6000.0.58f1` and `6000.0.58f2` when feasible

## Packaging Strategy

The Unity side must be editor-only and self-contained.

Recommended installation target:

`<Project>/Packages/com.xuunity.light-mcp/`

Recommended manifest entry:

```json
"com.xuunity.light-mcp": "file:Packages/com.xuunity.light-mcp"
```

### Why embedded local package

- self-contained in the Unity project
- no host-private path coupling
- no network registry
- no OpenUPM requirement
- easier to inspect and remove
- public-safe and reproducible

Additional packaging rule:
- the Unity package must use only `Editor/` asmdefs in Phase 1
- there must be no `Runtime/` asmdef at all in the base package

## Removal Contract

The base service must be easy to remove from a Unity project without cleanup archaeology.

Required properties:
- no `ProjectSettings/ProjectSettings.asset` mutation
- no scripting define injection
- no scoped-registry mutation
- no generated code under `Assets/`
- no `Packages/packages-lock.json` dependency fan-out beyond the local embedded package
- all mutable bridge state under `<Project>/Library/XUUnityLightMcp/`

Required uninstall path:
1. remove `"com.xuunity.light-mcp"` from `Packages/manifest.json`
2. delete `<Project>/Packages/com.xuunity.light-mcp/`
3. delete `<Project>/Library/XUUnityLightMcp/`
4. reopen Unity

If more than that is needed, the design is already drifting.

## Idle Performance Contract

The bridge must not impose meaningful editor overhead when it is not in use.

Required properties:
- disabled by default after package install
- no `EditorApplication.update` loop unless a local opt-in config exists
- no log subscription unless the bridge is enabled
- no AssetDatabase scan, scene traversal, or reflection work on startup
- no periodic work outside a small enabled-session heartbeat and inbox poll
- all expensive work happens only on request

Recommended enabled-session defaults:
- heartbeat every `2000ms`
- inbox poll every `500ms`
- bounded console ring buffer only while enabled

## External Runtime Dependencies

Goal:
- none beyond host baseline tooling

Recommended external server implementation:
- Python `3.10+`
- standard library only for Phase 1

Reason:
- already present in our environment
- avoids npm/pip dependency drift
- easy to ship as a small repo-safe script

If MCP protocol handling becomes too noisy by hand, a tiny vendored helper may be considered later.
But the default design should assume no third-party package dependency.

## Unity Bridge Dependencies

Goal:
- Unity built-ins only
- editor APIs only

Avoid:
- NuGet
- Roslyn
- SignalR
- WebSockets
- HTTP client/server stacks
- custom native binaries
- runtime asmdefs

Also avoid:
- background server binary downloads
- package-manager-time dependency restoration
- hidden network calls during first editor startup

Clarification:
- `unity.tests.run_editmode` may depend on the official `com.unity.test-framework` package
- that dependency is acceptable because it is a Unity-owned editor tool dependency, not a third-party transport/runtime stack

## Supported Operations

## Phase 1 stable tool surface

The external MCP server should expose only:

1. `unity.status`
2. `unity.capabilities.get`
3. `unity.health.probe`
4. `unity.console.tail`
5. `unity.scene.snapshot`
6. `unity.tests.run_editmode`
7. `unity.compile.player_scripts`
8. `unity.compile.matrix`

These map directly to the validated `xuunity` contract already defined earlier.

## Phase 2 validated editor-control additions

Only after Phase 1 is stable:

9. `unity.playmode.state`
10. `unity.playmode.set`
11. `unity.game_view.configure`
12. `unity.game_view.screenshot`

Policy:
- `unity.game_view.configure` must not create persistent custom sizes by default
- if the requested size does not already exist, it should fail with an explicit opt-in path
- persistence is allowed only when the caller passes `allowCreateCustomSize=true`

## Phase 3 likely additions

13. `unity.assets.find`
14. `unity.assets.read`
15. `unity.object.inspect`
16. `unity.editor.selection`
17. `unity.tool.run`
18. `unity.tool.result.read`

## Explicitly excluded from base service

- `package-add`
- `package-remove`
- `script-execute`
- `reflection-method-call`
- `script-update-or-create`
- `gameobject-modify`
- `assets-delete`
- runtime connect/build support

## Tool Runner Extension Model

The service should support "run current tool and capture result" without turning the base bridge into a reflection sandbox.

Recommended model:
- each runnable capability is registered as an explicit tool adapter
- tool adapters can be built-in or project-local
- the MCP server can invoke them through a common runner
- results are persisted as structured artifacts for later readback

Example conceptual shape:

```text
unity.tool.run
  input:
    tool_id: "project.validate.addressables"
    args: {...}

unity.tool.result.read
  input:
    run_id: "uuid"
```

Why this matters:
- lets us add project-specific diagnostics incrementally
- supports "write adapters for launching something and collecting results"
- avoids exposing arbitrary code execution

This is the correct replacement for the most attractive part of the heavyweight systems:
- extensibility
- but without `script-execute`
- and without raw reflection calls as the default extension story

## Request / Response Contract

Each request file should be structured like:

```json
{
  "request_id": "uuid",
  "operation": "unity.scene.snapshot",
  "project_root": "/abs/path/to/project",
  "created_at_utc": "2026-05-05T12:00:00Z",
  "timeout_ms": 30000,
  "args": {}
}
```

Each response file should be structured like:

```json
{
  "request_id": "uuid",
  "status": "ok",
  "completed_at_utc": "2026-05-05T12:00:02Z",
  "payload": {
    "backend_id": "xuunity.light_unity_mcp",
    "validation_evidence": "unity_mcp"
  },
  "error": null
}
```

Error shape:

```json
{
  "request_id": "uuid",
  "status": "error",
  "completed_at_utc": "2026-05-05T12:00:02Z",
  "payload": null,
  "error": {
    "code": "editor_not_running",
    "message": "Unity bridge heartbeat is stale."
  }
}
```

## Readiness Model

The Unity bridge should write `bridge_state.json` periodically.

Example fields:

```json
{
  "bridge_version": 1,
  "project_root": "/abs/path/to/project",
  "editor_pid": 12345,
  "unity_version": "6000.0.58f2",
  "is_compiling": false,
  "is_playing": false,
  "heartbeat_utc": "2026-05-05T12:00:01Z",
  "last_error": null
}
```

The external MCP server should treat a stale heartbeat as `editor_not_running` or `mcp_unreachable`.

## Capability Probe Model

On first enabled editor session for a given project and Unity version, the bridge should run a lightweight health probe and persist:

`<Project>/Library/XUUnityLightMcp/state/capabilities_report.json`

Purpose:
- detect whether version-sensitive surfaces still match expectations
- especially for reflection-backed editor integrations
- disable unsupported operations before clients rely on them

The probe report should include:
- Unity version
- probe version
- capability records
- adapter IDs
- supported operations
- disabled operations

Important rule:
- risky operations should not assume support based only on the bridge being reachable
- they should be gated by the current capability report

This is the right place to grow per-Unity adapters later.
Example:
- `game_view_reflection_v1` for current Unity 6000 reflection shape
- future `game_view_public_api_v1` if Unity exposes a stable public API later

## Valuable Patterns To Keep From IvanMurzak

The heavy package is still a useful reference.
These are the parts worth keeping conceptually and rewriting in a smaller form.

### 1. One-command operator workflow

Valuable idea:
- install
- open
- wait-for-ready
- run tool

What to keep:
- explicit operator lifecycle
- predictable CLI flow

What to change:
- remove hidden server downloads
- remove package restore side effects
- keep setup local and transparent

### 2. Attribute-driven capability registration

Valuable idea:
- annotate tools/resources/prompts/skills
- generate registration from explicit declarations

What to keep:
- declarative registration
- low-friction addition of new capabilities

What to change:
- keep only operations we need
- no giant mixed catalog by default
- use a smaller adapter registry instead of one massive all-purpose tool universe

### 3. AI-client onboarding helpers

Valuable idea:
- generate MCP config for different clients
- generate project-specific support files

What to keep:
- reusable per-client config templates

What to change:
- move this completely outside the Unity bridge
- keep it in `AIRoot/Operations/.../templates/clients/`

### 4. Structured test execution path

Valuable idea:
- tests are a first-class operation

What to keep:
- explicit EditMode test runner
- normalized counts and failures

What to change:
- keep the implementation small
- only support the validation-first path initially

### 5. Clear operational status signal

Valuable idea:
- a real readiness/status probe

What to keep:
- explicit bridge state file
- editor/compile/playmode visibility

What to change:
- no hidden transport complexity
- no dependence on external relay/server binaries

## Valuable Pattern To Keep From DevAccelerationSystem

The most valuable compile-validation idea from `FoxsterDev/DevAccelerationSystem` is:

- use `PlayerBuildInterface.CompilePlayerScripts`
- pass explicit `ScriptCompilationSettings`
- vary `BuildTarget`, option flags, and extra defines per configuration
- collect compiler errors from `CompilationPipeline.assemblyCompilationFinished`
- do not switch the active build target just to answer "will this compile for platform X?"

That pattern is the correct basis for `xuunity` compile validation because it gives:
- platform-aware compile checks
- define-aware compile checks
- no `PlayerSettings` define mutation
- no active platform churn

Constraint:
- it still depends on the host having the target platform support module installed

## Valuable Patterns To Avoid From IvanMurzak

- runtime/player support in the base package
- NuGet dependency restore inside Unity startup
- broad package mutation tools in the same default surface
- dynamic code execution as a routine tool
- reflection call as a normal path
- hidden runtime binary download/unpack
- automatic build-target-wide define mutation
- deep dependency tree for simple validation tasks

## Console Strategy

The Unity bridge should own console collection itself.

Recommended method:
- subscribe to `Application.logMessageReceivedThreaded`
- append structured log entries to a bounded local buffer
- serve `tail` requests from that buffer

Why:
- avoids scraping Editor UI state
- gives more predictable structured output

Guardrail:
- do not implement log clearing in Phase 1

## Scene Snapshot Strategy

Return only a lightweight scene summary:
- active scene name
- scene path
- dirty state
- root object count
- root object names

Do not attempt deep recursive hierarchy export in Phase 1.

Reason:
- keeps payloads small
- avoids accidental complexity
- sufficient for most validation and orientation tasks

## EditMode Test Strategy

Use Unity Test Framework APIs directly from the editor bridge.

Requirements:
- run EditMode only in Phase 1
- normalize results into stable counts
- keep `no_tests` distinct from `passed`
- keep infrastructure failures distinct from test failures

Phase 1 does not need PlayMode automation.

## Compile Validation Strategy

Use Unity `PlayerBuildInterface.CompilePlayerScripts` directly from the editor bridge.

Requirements:
- no active build-target switch
- no project-wide scripting-define mutation
- support one-off extra defines per compile request
- support `ScriptCompilationOptions` flags such as `DevelopmentBuild`
- report normalized file/line/column compiler errors
- report `target_support_missing` distinctly when the host lacks the platform module

Recommended tools:
- `unity.compile.player_scripts`
- `unity.compile.matrix`

This is the correct replacement for ad hoc "switch platform then see if editor compiles" workflows.

## Versioned Adapter Strategy

Some capabilities should be treated as adapter-backed, not timeless implementation facts.

Current example:
- Game View control and screenshot capture are currently served by adapter:
  - `game_view_reflection_v1`

Design rule:
- every version-sensitive capability should declare an `adapter_id`
- health probe should record that adapter in the capability report
- clients should treat the adapter record as evidence of what path is active, not just whether the tool exists

Future path:
- add Unity-version-specific adapters only where probe evidence shows real divergence
- prefer public Unity APIs when they become available
- keep old adapters only as long as supported host Unity versions require them

## Integration Pain Points Observed In The Heavy MCP Path

These issues were encountered during real integration and should directly shape the new design.

### 1. Player-build footprint appeared immediately

Observed:
- several MCP-related DLLs entered Android build artifacts

Desired better outcome:
- zero player-build footprint by default

Design response:
- editor-only package
- no runtime asmdef

### 2. Hidden dependency and binary behavior

Observed:
- runtime unpack/download behavior for the server binary
- large DLL tree under `Assets/Plugins/NuGet`

Desired better outcome:
- no hidden downloads
- no NuGet materialization into project assets

Design response:
- standard-library external server
- embedded editor-only Unity package

### 3. Compile blocker during onboarding

Observed:
- onboarding failed until `com.unity.modules.physics` was added because of package code assumptions

Desired better outcome:
- base package should not assume unrelated runtime modules

Design response:
- keep the bridge narrow
- avoid broad converter/runtime code paths
- test against `6000.0.58f1` baseline explicitly

### 4. Startup noise and unclear readiness path

Observed:
- transient connection-refused churn before readiness

Desired better outcome:
- deterministic readiness model
- one obvious heartbeat file

Design response:
- file IPC
- bridge heartbeat
- explicit request/response lifecycle

### 5. Tool payload quality was uneven

Observed:
- some tools returned weaker payloads than expected, for example incomplete scene-root information

Desired better outcome:
- every supported operation should have a hand-designed normalized payload

Design response:
- narrow operation set
- explicit schemas per adapter

### 6. Local setup required more machinery than the use case justified

Observed:
- token/bootstrap/open/wait lifecycle was useful
- but too much platform was dragged in around it

Desired better outcome:
- keep the useful operator workflow
- remove the unnecessary platform layers

Design response:
- retain the CLI lifecycle
- strip transport and dependency complexity

### 7. Build-target-wide state mutation is unacceptable by default

Observed:
- `UNITY_MCP_READY` was applied broadly across build targets

Desired better outcome:
- no project-wide build define churn for base validation tools

Design response:
- no runtime gating defines
- editor-only bridge assembly
- local opt-in config under `Library/`, not project-wide state mutation

### 8. Compile validation should not require platform churn

Observed:
- shell-only compile fallback is weak once the question becomes target-specific or define-specific
- active platform switching is slow, noisy, and changes editor state

Desired better outcome:
- ask Unity to compile for a requested target in place
- vary option flags and extra defines per request
- keep the current editor target untouched

Design response:
- expose `unity.compile.player_scripts` and `unity.compile.matrix`
- use `PlayerBuildInterface.CompilePlayerScripts`
- collect compiler diagnostics through `CompilationPipeline.assemblyCompilationFinished`

## Preferred Developer Experience

This is how the new system should feel when it is working correctly.

### Install

One explicit command:

```bash
bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh --project-root /path/to/project
```

What it should do:
- install external MCP server locally
- copy the editor-only package into the Unity project
- patch manifest if needed
- leave the bridge disabled until explicitly enabled
- emit clear enable, disable, and uninstall steps

### Open and verify

One explicit command:

```bash
xuunity-light-unity-mcp status --project-root /path/to/project
```

If Unity is closed:
- say so plainly

If Unity is open:
- return structured readiness immediately

### Run validation

Simple commands:

```bash
xuunity-light-unity-mcp console-tail --project-root /path/to/project
xuunity-light-unity-mcp scene-snapshot --project-root /path/to/project
xuunity-light-unity-mcp tests-run-editmode --project-root /path/to/project
```

### Extend

To add a new capability, a developer should:
1. add one Unity-side operation adapter
2. register it in the bridge registry
3. add one external-server schema mapping
4. optionally add one client-facing template note if needed

That should be enough.

It should not require:
- package restores
- server binary builds inside the Unity project
- runtime-player considerations
- giant prompt catalogs

## Safety Model

This service should be intentionally narrow and local.

### Trust assumptions

- same host
- same user
- explicit project root
- no remote access

### Safety rules

- one request maps to one concrete project root
- the external server must reject ambiguous project selection
- only allow operations on the configured project root
- no write or delete operations in base service
- no shell fallback may be labeled as Unity validation

## Codex Integration Model

The external process should be installable similarly to `local MCP operation package`.

Planned public package contents:

```text
AIRoot/Operations/XUUnityLightUnityMcp/
  README.md
  init_xuunity_light_unity_mcp.sh
  templates/
    server.py
    run.sh
    config.toml.snippet
    unity-package/
      package.json
      Editor/
        ...
```

### Install behavior

The init script should:
- install the external server into local Codex tools home
- install or update the Codex config block
- optionally copy the Unity bridge package into a target project
- optionally patch the project manifest

### Similarity to `local MCP operation package`

Like `local MCP operation package`, the public package should:
- contain no secrets
- contain no host-private paths
- carry reusable setup and templates only

## Host-Local Layer

Keep repo-specific wrappers out of `AIRoot`.

Planned host-local operational folder:

`host-local XUUnityLightUnityMcp wrapper path`

Responsibilities:
- repo-specific helper commands
- adapter policy wrappers
- project-selection helpers
- migration tooling from heavy MCP experiments

## Proposed Tool Names

Public MCP tool names:
- `unity_status`
- `unity_console_tail`
- `unity_scene_snapshot`
- `unity_tests_run_editmode`

Internal `xuunity` names may remain:
- `unity.status`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.tests.run_editmode`

This separation keeps MCP tool names client-friendly and adapter names workflow-friendly.

## Reference Use Of Existing GitHub MCP Projects

Existing projects should be treated as source references, not runtime dependencies.

### Use as reference for

- Unity test execution quirks
- console capture edge cases
- scene and object serialization boundaries
- editor lifecycle and reload handling
- MCP client ergonomics
- custom tool registration patterns

### Do not inherit blindly

- runtime support
- package mutation defaults
- dynamic code execution defaults
- heavyweight dependency graphs
- remote relay infrastructure

## Reference Mapping

| Source | Use it for |
| --- | --- |
| `IvanMurzak/Unity-MCP` | editor lifecycle, test running, broad Unity tool examples, tricky Unity API edge cases |
| `CoplayDev/unity-mcp` | cleaner MCP surface ideas, extensibility comparisons, custom-tool patterns |
| official Unity MCP docs | protocol direction, project targeting ideas, custom tool concepts |

## Implementation Phases

## Phase 0: contract freeze

Produce:
- final tool list
- final JSON request/response schema
- final folder layout
- final operation adapter interface
- final client adapter interface

Exit criteria:
- no unresolved questions about base scope

## Phase 1: tiny editor bridge

Build:
- editor-only Unity package
- bridge heartbeat
- file IPC inbox/outbox
- `unity.status`
- operation registry

Exit criteria:
- Codex can reliably see Unity open/closed/compiling state

## Phase 2: core validation surface

Build:
- console tail
- scene snapshot
- EditMode test execution
- result artifact persistence for tool runs

Exit criteria:
- replaces current heavy backend for the validation-first workflow

## Phase 3: public `AIRoot` operational package

Build:
- `AIRoot/Operations/XUUnityLightUnityMcp/`
- install/init script
- Codex config template
- generic MCP client config templates
- copy-to-project bridge install path

Exit criteria:
- another repo can install and use it without host-private assumptions

## Phase 4: second-wave read operations

Build:
- asset find/read
- object inspect
- selection state
- pluggable project-local tool adapters

Exit criteria:
- enough read surface for richer debugging without mutation creep

## Rejection Criteria

Stop or redesign if any of the following becomes true:

- the Unity bridge requires runtime asmdefs
- NuGet becomes required
- external binaries become required
- base install starts changing player builds
- the service needs broad mutation to stay useful
- file IPC proves too flaky even for same-host use

If those happen, the design is drifting away from the original goal.

## Success Criteria

This project is successful if:

1. install footprint is visibly smaller than current community packages
2. player build footprint is zero by default
3. Codex can run the full validation-first loop reliably
4. setup is understandable from one small `AIRoot/Operations/` package
5. the service can be removed from a project cleanly
6. package install does not create noticeable editor idle overhead before explicit enable

## Bottom Line

The right replacement is not "another full Unity MCP platform."

The right replacement is:
- a tiny external stdio MCP server
- a tiny editor-only Unity bridge
- a very small, high-trust tool surface
- packaged publicly like `local MCP operation package`

That shape fits `xuunity` materially better than the heavy existing solutions.
