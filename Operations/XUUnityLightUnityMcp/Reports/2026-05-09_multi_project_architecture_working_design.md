# XUUnity Light Unity MCP Multi-Project Working Design

Date: `2026-05-09`
Status: `public-safe working design note`
Scope: `multi-project architecture and refactor guidance`

## Purpose

This document is a working design note for the next architecture evolution of
`XUUnity Light Unity MCP` toward reliable multi-project support.

It is not the final canonical public source of truth.

It exists to preserve the right direction from the supplied technical design
specification while reconciling it with the current public service shape,
current transport/lifecycle behavior, and the implementation that already
exists under:

- `DESIGN.md`
- `README.md`
- `templates/`

## Source Inputs

Primary design input:
- user-supplied `Technical Design Specification: XUUnity Light MCP (v2.0)`

Current local baseline:
- current public design already supports:
  - explicit `projectRoot`
  - transport adapter selection
  - `tcp_loopback` plus `file_ipc`
  - bridge generation/session tracking
  - request journal recovery
  - host editor session state
  - lifecycle reset classification

This draft keeps those working strengths and extends them into an explicit
multi-project architecture instead of treating multi-project support as an
accidental side effect of `projectRoot`.

## Design Position

The supplied specification is directionally correct and should guide future
work.

The main ideas to preserve:

- `Stateless Wrapper / Stateful Bridge`
- explicit multi-project routing through a registry layer
- per-project context keyed by normalized `projectRoot`
- per-project concurrency control
- dynamic TCP as the primary transport
- file IPC as fallback
- generation-based lifecycle reset handling
- cross-platform process liveness and launch rules
- ANR detection as a first-class host concern

The main adaptation required for the current codebase:

- do not throw away the current request-journal, bridge-state, and lifecycle
  recovery model
- evolve them into a registry-based architecture instead of replacing them with
  a new transport stack all at once

## Current Baseline vs Target

### Current baseline

Today the service already has:

- explicit per-request `projectRoot`
- bridge state under `<Project>/Library/XUUnityLightMcp/state/bridge_state.json`
- host session state under `<Project>/Library/XUUnityLightMcp/state/host_editor_session.json`
- transport adapters:
  - `tcp_loopback`
  - `file_ipc`
- lifecycle identity:
  - `bridge_generation`
  - `bridge_session_id`
- request recovery:
  - `request_started`
  - `request_completed`
  - `request_reclassified`
  - `request_abandoned`
  - `request_submitted`

### Target gap

What is still implicit or under-specified:

- there is no explicit `BridgeRegistry` abstraction in the server
- there is no first-class in-memory `ProjectContext` object
- per-project locking is still distributed across command flow rather than
  centralized as a context capability
- discovery is partly implemented through host session files and bridge state,
  but not yet formalized as a reusable routing phase
- ANR policy exists only partially through timeouts and stale-state handling,
  not as a dedicated escalation protocol
- cross-platform process scanning is functional in places but not yet expressed
  as a portable subsystem contract

## Core Architectural Rule

Keep the service model:

- host/server side stays mostly stateless between requests
- Unity bridge remains the state owner for editor execution truth

But add one bounded layer of host state:

- `BridgeRegistry`

This is not business state.
It is only routing, liveness, transport, and concurrency state.

## Target Service Shape

The service evolves into four cooperating layers:

1. MCP request entry layer
2. `BridgeRegistry`
3. per-project `ProjectContext`
4. Unity-side bridge

### 1. MCP request entry layer

Responsibilities:

- validate MCP input
- normalize `projectRoot`
- resolve routing through `BridgeRegistry`
- pass the request to the selected `ProjectContext`

This layer should stay thin.

### 2. BridgeRegistry

Responsibilities:

- map normalized project roots to live in-memory contexts
- perform discovery when a project is first seen
- refresh stale context metadata
- evict dead contexts safely
- expose a single routing API to the server

The registry is host-local and process-local.

### 3. ProjectContext

Responsibilities:

- keep the last known bridge state snapshot
- hold the selected transport adapter for that project
- hold per-project locks
- coordinate request lifecycle for that one Unity editor instance
- own recovery policy for timeouts, generation changes, and reconnects

### 4. Unity-side bridge

Responsibilities:

- publish state truth
- own execution on the Unity main thread
- expose transport listener details
- increment lifecycle generation on rebootstrap
- journal request lifecycle events

## BridgeRegistry Design

## Instance Key

Registry key:
- normalized absolute `projectRoot`

Normalization rules:

- resolve symlinks where feasible
- remove trailing separators
- collapse `.` and `..`
- on Windows:
  - normalize case
  - compare case-insensitively
- keep internal representation stable and deterministic

The key must match the actual Unity project root, not a child path.

## Registry API

Working target interface:

- `get_or_discover(project_root) -> ProjectContext`
- `refresh_context(project_root) -> ProjectContext`
- `forget(project_root)`
- `list_active_contexts()`

## Registry responsibilities in detail

For a miss:

1. normalize `projectRoot`
2. validate it looks like a Unity project
3. run discovery
4. create `ProjectContext`
5. cache it

For a hit:

1. validate context freshness
2. refresh transport/state if needed
3. return existing context

Eviction should happen when:

- host process knows Unity exited
- bridge state is stale and PID is gone
- explicit maintenance or prune command requests removal

## ProjectContext Design

Each context should hold:

- `project_root`
- `instance_key`
- `last_bridge_state`
- `last_host_editor_session_state`
- `active_transport`
- `transport_metadata`
- `request_lock`
- `interactive_lock`
- `last_seen_pid`
- `last_seen_generation`
- `last_seen_session_id`
- `last_refresh_utc`
- `health_classification`

## Locking model

The user-provided specification is correct that one project should not receive
more than one mutating command at a time.

Refined rule for current service:

- one per-project mutation lock
- optionally one lighter read lock policy later

Initial safe classification:

Mutating:
- `unity.project.refresh`
- `unity.compile.player_scripts`
- `unity.compile.matrix`
- `unity.tests.run_editmode`
- `unity.tests.run_playmode`
- `unity.playmode.set`
- `unity.build_target.switch`
- `unity.editor.quit`
- scenario runs that contain mutating steps

Non-mutating:
- `unity.status`
- `unity.capabilities.get`
- `unity.health.probe`
- `unity.console.tail`
- `unity.scene.snapshot`
- `unity.playmode.state`
- `unity.game_view.screenshot`
- summary and maintenance reads

Important constraint:

- even non-mutating operations may still require serialization when Unity is in
  lifecycle churn
- so the lock model should remain policy-driven, not hardcoded forever

## Discovery Sequence

The supplied specification is correct to start from local state files.

Target discovery order:

1. normalize `projectRoot`
2. inspect:
   - `Library/XUUnityLightMcp/state/host_editor_session.json`
   - `Library/XUUnityLightMcp/state/bridge_state.json`
3. if a PID is present:
   - verify it is alive
   - verify it looks like a Unity editor process
   - verify it belongs to the requested project when possible
4. if bridge state is live:
   - bind transport from published metadata
5. otherwise classify as:
   - editor closed
   - stale state
   - bridge disabled
   - host-launchable but not active

## Process matching

Preferred evidence order:

1. live bridge state with live PID
2. host editor session state with live PID
3. process table match against Unity command line and `-projectPath`

The registry should trust process-table discovery only as host routing evidence,
not as proof that the bridge is healthy.

## Cross-Platform Process and Launch Design

The supplied OS-specific section should be kept.

Implementation stance:

- design a thin `HostPlatformAdapter`
- avoid scattering platform branches across lifecycle code

### Windows

Need:

- case-insensitive path comparison
- PID liveness through `OpenProcess`, `tasklist`, or equivalent safe fallback
- detached launch via `subprocess.Popen(..., creationflags=DETACHED_PROCESS)`

### macOS

Need:

- PID liveness via `os.kill(pid, 0)`
- background editor launch via:
  - `open -n -g -a {UnityPath} --args -projectPath {Path}`

### Linux

Need:

- PID liveness via `os.kill(pid, 0)`
- detached launch via `nohup` or `setsid`

### Lock and file-use probing

Do not overfit one host.
Abstract:

- “is editor lock evidence present?”
- “is project filesystem actively held by Unity?”

Possible backends:

- `lsof`
- `flock`
- Unity lockfile presence
- Windows exclusive-open probes

This should be best-effort evidence, not the primary readiness proof.

## Transport Architecture

The target transport model should stay exactly two-tier:

1. `tcp_loopback` as primary
2. `file_ipc` as fallback

## TCP loopback

Keep:

- dynamic port binding
- `127.0.0.1`
- transport metadata published by Unity in bridge state

Per-project implication:

- every Unity editor instance publishes its own port
- the registry binds transport per project context
- there must never be a single global port assumption

## File IPC fallback

Keep:

- per-project inbox/outbox directories
- atomic write/move semantics
- request-id-based response files

The registry should treat fallback transport selection as a context property,
not a global service mode.

## Mixed transport policy

Keep the current useful rule:

- active transport may be `tcp_loopback`
- file IPC may still remain available for fallback or recovery paths

Do not require a hard switch that disables one channel completely.

## State Schema Evolution

The supplied schema is correct in spirit, but the current service already has a
flatter shape that is actively used by scripts and wrappers.

Therefore the evolution rule should be:

- preserve backward-compatible flat keys for now
- allow a more structured logical schema without breaking current consumers

Target logical state groups:

- bridge identity
- process identity
- transport
- health
- editor state
- lifecycle flags

Example logical grouping:

- `bridge_version`
- `bridge_generation`
- `bridge_session_id`
- `editor_pid`
- `health_status`
- `heartbeat_utc`
- transport block
- editor-state block

But until public migration is complete, current flat keys such as:

- `transport`
- `transport_host`
- `transport_port`
- `playmode_state`
- `domain_reload_in_progress`
- `refresh_settle_pending`

should remain readable.

## Multi-Project Routing Contract

Every tool call must remain explicit about `projectRoot`.

No hidden “current Unity project” global should be introduced.

Routing algorithm:

1. request arrives with `projectRoot`
2. server normalizes path
3. registry resolves or discovers context
4. context selects active transport
5. context serializes or rejects according to lock policy
6. request executes
7. lifecycle and journal evidence are mapped back to that same context

This must be deterministic even with several editors open at once.

## Lifecycle and Domain Reload

The supplied specification is correct that generation mismatch is a first-class
event.

Current design already does this well.

Keep and strengthen:

- `bridge_generation`
- `bridge_session_id`
- request journal correlation by `request_id`
- transport outcome separated from Unity outcome

Working rule:

- generation change during in-flight request is not automatically a product
  failure
- it is a transport/lifecycle event first
- final request disposition must be resolved from journal and state

## Retry pattern

The supplied guidance says the agent should retry on `lifecycle_reset`.
That is directionally correct, but current design is safer:

- auto-retry only explicitly idempotent operations
- otherwise return compact recovery data and let the caller decide

This rule should remain.

It is safer for:

- editor quit
- play mode transitions
- build-target changes
- scenarios with side effects

## ANR and Fault Tolerance

The specification correctly calls out ANR handling as first-class host logic.

Target host classification:

- `fresh`
- `stale`
- `anr`

Recommended thresholds for current system:

- `fresh`: heartbeat age `< 5s`
- `stale`: `5s - 15s`
- `anr_suspected`: `15s - 30s`
- `anr`: `> 30s` with live PID and no progress evidence

Progress evidence should include more than heartbeat when available:

- request journal movement
- bridge generation changes
- lifecycle settle flags
- active operation timestamps

## ANR response policy

Do not jump straight from one stale read to process kill.

Escalation order:

1. re-read bridge state
2. inspect request journal movement
3. inspect process liveness
4. inspect editor log tail for startup or compile blockers
5. classify:
   - stale but recovering
   - lifecycle churn
   - hard timeout
   - probable ANR
6. only then consider termination policy

Termination policy should remain policy-driven:

- `observe_only`
- `graceful_terminate`
- `terminate_then_restart`

The supplied `SIGTERM` -> wait -> `SIGKILL` flow is right for Unix hosts.
Windows needs equivalent semantics via process termination APIs.

## Editor Log Diagnostics

The supplied AI-agent guide correctly asks for log-based diagnosis on transport
failures.

This should become a first-class middleware step for:

- startup timeout
- transport connect failure
- stale bridge after launch
- suspected ANR

Design rule:

- prefer compact extracted diagnosis
- do not dump raw large log tails by default

## Async Model

The supplied spec mentions `asyncio.Lock`.

That is the right direction if the server becomes properly async.

For current codebase planning:

- the architecture should be designed around async-safe contexts and locks
- but migration may happen in phases

Suggested phases:

1. introduce `BridgeRegistry` and `ProjectContext` as synchronous abstractions
2. centralize lock ownership per project
3. migrate transport invocation to async-friendly boundaries
4. only then move the outer server loop to true async where it materially helps

This avoids mixing a full async rewrite with lifecycle refactoring in one step.

## Compatibility Rules

Do not break current callers that already depend on:

- explicit `projectRoot`
- current CLI subcommands
- current summary surfaces
- current journal event names
- current bridge-state flat fields

The multi-project evolution should feel like an internal hardening and scaling
step, not a protocol reset.

## Phased Implementation Plan

### Phase 1: Explicit registry and context layer

Implement:

- `BridgeRegistry`
- `ProjectContext`
- per-project request lock
- context refresh on every routed request

No transport contract changes yet.

### Phase 2: Discovery formalization

Implement:

- formal discovery routine
- process-table verification by platform adapter
- host session plus bridge-state reconciliation

### Phase 3: ANR classification layer

Implement:

- explicit stale/anr classification
- editor log diagnostic fallback
- policy-based termination and restart hooks

### Phase 4: Schema and transport hardening

Implement:

- structured state grouping where safe
- stronger per-project transport metadata
- explicit context eviction and stale cleanup

### Phase 5: Public documentation promotion

After local proof:

- promote reusable parts into:
  - `AIRoot/Operations/XUUnityLightUnityMcp/DESIGN.md`
  - `README.md`
  - `ROADMAP.md`
  - `SMOKE_TESTS.md`

## Validation Strategy

The previous version of this draft was too weak on proof.

That is not acceptable for a multi-project refactor of a live MCP surface.

This architecture change must carry an explicit verification contract that
proves two things at the same time:

1. the new multi-project routing works
2. the current single-project behavior did not regress

The validation plan should be treated as part of the architecture, not as a
follow-up task.

## Validation Objectives

Every phase must prove:

- current CLI commands still work
- current MCP tool surfaces still work
- current lifecycle recovery still works
- current transport fallback still works
- routing stays deterministic by `projectRoot`
- no request leaks into the wrong Unity editor instance

## Pre-Refactor Test Harness

Yes, some tests should be added before the main multi-project refactor starts.

Reason:

- the current proof set is strong at integration level
- but `server.py` is now large enough that code-movement-only refactors can
  easily break pure host logic before Unity smoke routes catch it clearly
- a small fast Python-side harness will make file extraction and routing changes
  much safer

Current repository observation:

- there is no visible dedicated Python test suite around
  `AIRoot/Operations/XUUnityLightUnityMcp/templates/server.py`
- current proof relies mainly on live smoke/fault runners

That is not enough for confident internal decomposition of a `3496`-line host
server file.

## Test Strategy Before Large Refactor

The right mix is:

1. small fast host-side unit tests for pure logic
2. focused host-side integration tests against temporary project folders
3. existing live Unity smoke/fault routes kept as the higher layer proof

The goal is not to simulate all of Unity in Python.
The goal is to protect:

- routing correctness
- lifecycle summary correctness
- parser and dispatch stability
- project-local isolation rules

## Recommended Test Technology

For the initial harness, prefer Python standard library `unittest`.

Reason:

- no extra dependency bootstrap is required
- easier to run on any host that already runs the helper
- suitable for pure logic and temp-directory integration tests

Later, moving to `pytest` is acceptable if fixture ergonomics become
meaningfully better, but it should not block the first safety net.

## Recommended Test Location

Suggested location:

- `AIRoot/Operations/XUUnityLightUnityMcp/tests/`

Current runner:

- `AIRoot/Operations/XUUnityLightUnityMcp/run_host_python_tests.sh`

Suggested initial layout:

- `tests/test_bridge_runtime.py`
- `tests/test_status_summaries.py`
- `tests/test_request_recovery.py`
- `tests/test_project_context_helpers.py`
- `tests/test_cli_parser.py`
- `tests/test_tool_dispatch.py`

If keeping tests closer to templates is more practical, a fallback is:

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/tests/`

But a top-level `tests/` folder under the operation root is cleaner.

## What To Test First

### 1. Pure lifecycle summary logic

These tests are the highest value per minute.

Protect:

- `build_bridge_stabilization_summary`
- `build_request_final_status`
- `inspect_bridge_state_liveness`
- `bridge_identity_changed`
- lifecycle recovery classification fields such as:
  - `request_submitted`
  - `request_observed_in_unity_journal`
  - `bridge_changed_since_submission`
  - `recovery_gap_detected`
  - `operation_outcome`
  - `recommended_next_action`

These are ideal for synthetic temp journal/state fixtures.

### 2. Journal lookup behavior

Protect:

- `find_latest_request_event`
- request sorting by `event_at_utc`
- filtering by operation
- handling of invalid JSON files
- handling of missing journal directories

These are likely to break silently during refactor if left untested.

### 3. Project-root and package-alignment helpers

Protect:

- `ensure_project_root`
- package dependency alignment inspection
- manifest missing / invalid / file-based / remote-based cases

These are good candidates to stabilize before moving them out of `server.py`.

### 4. Response normalization helpers

Protect:

- refresh payload normalization
- compile payload normalization
- playmode payload normalization
- test payload normalization

These are pure functions and should be cheap to lock down before extraction
into a separate module.

### 5. Parser and command registration

Protect:

- all expected CLI subcommands still exist
- argument names for critical commands do not drift
- MCP tool list still includes required tools

This is especially useful before extracting:

- `server_cli_bridge.py`
- `server_cli_batch.py`
- `server_mcp_protocol.py`
- `server_mcp_tools.py`

### 6. Tool dispatch and JSON-RPC shell

Protect:

- `call_tool`
- `tools/list`
- `tools/call`
- `initialize`
- validation errors for missing `projectRoot`

These tests should stay shallow and mock internal calls where appropriate.

### 7. Temp-directory project isolation tests

Before `BridgeRegistry` exists, add lightweight context-isolation tests using
two fake project roots with separate:

- `bridge_state.json`
- `host_editor_session.json`
- request journals

Protect:

- no cross-read between project A and project B
- request lookup for A never returns B events
- status summary for A never reads B state

These tests will become the seed for later registry tests.

## What Not To Over-Test Initially

Do not try to fully unit-test:

- real Unity editor launch
- real transport sockets end to end
- full batch build execution
- scenario execution semantics inside Unity

Those remain in the smoke/fault/integration layer.

The initial harness should stay fast and deterministic.

## Minimum Test Set Before Phase 1 Refactor

Before introducing `BridgeRegistry`, at minimum add tests for:

1. `build_bridge_stabilization_summary`
2. `build_request_final_status`
3. `find_latest_request_event`
4. `ensure_project_root`
5. package dependency alignment inspection
6. parser contains the critical commands
7. JSON-RPC `tools/list` and one `tools/call` happy path
8. two-temp-project isolation for journal/state reads

This is enough to make the first file extractions materially safer.

## Minimum Test Set Before Introducing BridgeRegistry

Add on top:

1. temp-context routing for two project roots
2. per-project lock behavior
3. stale-context refresh behavior
4. dead-PID context invalidation behavior with mocked liveness

These should be host-side tests and should not require live Unity editors.

## Test Philosophy During Refactor

Use the following order of confidence:

1. fast Python tests catch logic drift
2. smoke/fault routes catch real Unity integration regressions
3. multi-project acceptance scenarios catch architectural regressions

Do not rely on only one layer.

## Suggested First Extraction Enabled By Tests

Once the fast tests above exist, the first safe extraction is:

- `server_mcp_protocol.py`
- `server_mcp_tools.py`

Reason:

- mostly mechanical separation
- easier to prove unchanged with parser/tool-dispatch tests

After that, the next safe step is:

- `server_project_context.py`

because its helpers become test-protected before `BridgeRegistry` lands.

## Backward Compatibility Contract

The refactor must preserve these external contracts unless a deliberate public
migration is approved:

CLI contract:

- `bridge-state`
- `request-status`
- `request-status-summary`
- `request-latest-status`
- `request-final-status`
- `request-project-refresh`
- `request-compile`
- `request-compile-matrix`
- `request-build-config-compile-matrix`
- `request-editmode-tests`
- `request-playmode-tests`
- `request-scenario-*`
- `ensure-ready`
- `restore-editor-state`
- `batch-*`
- `maintenance-prune`

MCP tool contract:

- `unity_status_summary`
- `unity_request_final_status`
- `unity_scenario_result_summary`
- `unity_maintenance_prune`
- `unity_compile_build_config_matrix`
- `unity_scenario_run_and_wait`
- all direct bridge-backed tools already exposed by `TOOLS`

State contract:

- existing flat keys in `bridge_state.json` must remain readable
- current request journal event names must remain readable
- current recovery semantics by `request_id` must remain valid

Behavior contract:

- explicit `projectRoot` stays mandatory
- `tcp_loopback` remains primary when published and healthy
- `file_ipc` remains fallback
- lifecycle reset remains classified separately from Unity-side operation failure

## Regression Matrix

At minimum, every substantial phase should re-prove the following:

### Core status and routing

- `ensure-ready`
- `bridge-state`
- `request-status`
- `request-status-summary`
- `request-health-probe`

Expected:

- correct project routing
- healthy bridge recovery
- no ambiguity about the active project context

### Compile and validation path

- `request-project-refresh`
- `request-compile`
- `request-build-config-compile-matrix`
- `request-editmode-tests`

Expected:

- request reaches the intended project only
- lifecycle settle still works
- compile-first workflow remains valid

### Lifecycle recovery

- `request-final-status`
- `request-latest-status`
- lifecycle fault route
- request-abandoned fault route

Expected:

- request journal recovery still works by `request_id`
- lifecycle churn is not misreported as product failure
- compact recovery surfaces remain usable

### Interactive operations

- `unity.playmode.state`
- `unity.playmode.set`
- `unity.game_view.configure`
- `unity.game_view.screenshot`
- `unity.scene.snapshot`
- `unity.console.tail`

Expected:

- project isolation remains correct
- interactive operations still bind to the intended live editor

### Batch lane

- `batch-compile`
- `batch-compile-matrix`
- `batch-build-config-compile-matrix`
- `batch-editmode-tests`
- `batch-build-player`

Expected:

- closed-project validation remains intact
- live-editor conflict rules still apply correctly

## Existing Proof Routes To Reuse

The implementation should not invent a brand-new verification universe.
It should reuse current checked-in proof routes where possible.

Primary current routes:

- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_post_change_validation.sh`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_smoke_suite.sh`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_lifecycle_stress_suite.sh`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_lifecycle_fault_injection_suite.sh`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_request_abandoned_fault_suite.sh`
- `AIRoot/Operations/XUUnityLightUnityMcp/templates/smoke/run_transport_matrix_suite.sh`
- any host-local project wrappers that delegate to those public template runners

These routes already prove a large part of the current contract and should
remain the baseline regression set while multi-project support is added.

## New Multi-Project Acceptance Scenarios

Current proof is not enough for multi-project.
The new architecture needs explicit multi-project acceptance scenarios.

### Scenario MP-1: Two healthy editors, correct routing

Setup:

- open Project A
- open Project B
- both publish healthy `bridge_state.json`

Proof:

- `request-status --project-root A` reaches A
- `request-status --project-root B` reaches B
- bridge generation/session ids remain distinct where expected

Accept when:

- no request crosses into the wrong editor

### Scenario MP-2: Serialized mutation inside one project

Setup:

- one live editor for Project A

Proof:

- dispatch two mutating operations toward A close together
- second one is queued, rejected, or deferred by policy

Accept when:

- mutation overlap does not happen in the same project context

### Scenario MP-3: Parallel mutation across different projects

Setup:

- Project A and Project B both live

Proof:

- dispatch one mutating operation to A and one to B

Accept when:

- both can proceed independently
- one project lock does not block unrelated projects

### Scenario MP-4: One stale project, one healthy project

Setup:

- Project A stale or closed
- Project B healthy and live

Proof:

- routing to B still works cleanly
- A returns the right stale/offline classification

Accept when:

- registry isolation prevents one bad project state from poisoning another

### Scenario MP-5: Different active transports across projects

Setup:

- Project A on `tcp_loopback`
- Project B on `file_ipc` fallback

Proof:

- status and refresh work correctly on both

Accept when:

- transport binding is context-local, not process-global

### Scenario MP-6: Lifecycle churn in one project only

Setup:

- induce domain reload or rebootstrap in Project A
- keep Project B healthy

Proof:

- `request-final-status` and journal recovery work for A
- Project B remains routable and healthy

Accept when:

- lifecycle churn stays isolated to the affected context

## Phase Exit Criteria

Each phase must have a hard exit gate.

### Phase 1 exit gate

Required:

- single-project regression suite passes
- no externally visible CLI or MCP surface changed
- routing is still explicit by `projectRoot`

### Phase 2 exit gate

Required:

- discovery works through state files first
- process-table verification works on the current host
- stale/dead PID handling remains correct

### Phase 3 exit gate

Required:

- ANR classification path exists
- log-based diagnosis path exists
- no false-positive kill on normal lifecycle churn

### Phase 4 exit gate

Required:

- at least one two-project proof route passes
- project-local transport selection is correct
- per-project lock behavior is proven

### Phase 5 exit gate

Required:

- public docs are updated only after local proof
- new public guidance matches actual runner evidence

## Verification Artifacts

Every phase should emit concise artifacts, not only chat claims.

Preferred outputs:

- compact smoke summaries
- explicit pass/fail per scenario
- bridge generation/session evidence
- request ids for lifecycle cases
- local markdown audit notes when a phase changes architecture materially

## Server.py Refactor Strategy

The current `templates/server.py` is already too large for safe multi-project
evolution.

Current observed size:

- about `3496` lines

Current problem:

- it is not a pure server entrypoint anymore
- it mixes MCP JSON-RPC plumbing, CLI command handlers, lifecycle orchestration,
  batch tooling, summary shaping, scenario helpers, dependency patching, and a
  version-regression harness

That makes multi-project refactoring riskier than it needs to be.

## Current useful separation that already exists

The codebase already has some good splits:

- `server_bridge_runtime.py`
- `server_editor_host.py`
- `server_runtime_config.py`
- `server_summaries.py`
- `server_specs.py`
- `server_build_config.py`
- `server_core.py`

This is a good start.
The next refactor should continue this direction, not reset it.

## What should move out of server.py next

### 1. Project and routing utilities

Move out:

- `ensure_project_root`
- `find_latest_request_event`
- package-source alignment helpers

Target file:

- `server_project_context.py`
  - project-root normalization
  - Unity project validation
  - request journal lookup helpers
  - package dependency alignment inspection

This file can later grow into:

- `ProjectContext`
- registry-facing helpers

### 2. Bridge invocation orchestration

Keep `server_bridge_runtime.py` as the home for:

- lifecycle policy
- transport invocation
- per-project request serialization
- future `BridgeRegistry`
- future `ProjectContext`

This is the natural destination for the multi-project routing core.

### 3. CLI command handlers

The CLI subcommands should not all stay in `server.py`.

Split into:

- `server_cli_bridge.py`
  - bridge-state
  - status
  - final-status
  - project-refresh
  - compile
  - tests
  - scenario
  - editor lifecycle

- `server_cli_batch.py`
  - batch compile
  - batch matrix
  - batch tests
  - batch build player
  - test framework regression harness

This reduces the main file drastically and makes parser wiring clearer.

### 4. MCP tool adapters

Tool-call wrappers such as:

- `call_unity_status_summary_tool`
- `call_unity_request_final_status_tool`
- `call_unity_compile_build_config_matrix_tool`
- `call_unity_scenario_run_and_wait_tool`

should move to:

- `server_mcp_tools.py`

Reason:

- MCP tool behavior is a separate adapter layer from CLI
- it should not live in the same file as parser construction and batch harnesses

### 5. JSON-RPC protocol plumbing

Move:

- `JsonRpcError`
- `success_response`
- `error_response`
- `emit_message`
- `build_initialize_result`
- `list_tools_result`
- `handle_json_rpc_message`
- `serve_stdio`

to:

- `server_mcp_protocol.py`

Reason:

- this is the actual stdio MCP server shell
- it should depend on a tool-dispatch layer, not on batch logic or compile logic

### 6. Batch and regression helper logic

Large sections around:

- batch summary shaping
- dependency patching
- test framework version sweep
- candidate evaluation

should move to:

- `server_batch_runner.py`
- `server_batch_regression.py`

These are substantial enough to deserve isolation.

### 7. Response normalization helpers

Functions like:

- `normalize_refresh_payload_from_lifecycle`
- `normalize_compile_payload_from_lifecycle`
- `normalize_playmode_payload_from_lifecycle`
- `normalize_tests_payload_from_lifecycle`
- `normalize_response_payload_from_lifecycle`

should move to:

- `server_response_normalization.py`

Reason:

- they are response-shaping rules
- they are not CLI or MCP protocol concerns

## Proposed End-State File Shape

Reasonable target:

- `server.py`
  - minimal entrypoint only
  - imports parser builder and MCP serve function
  - calls `main()`

- `server_project_context.py`
  - project validation
  - journal helpers
  - package alignment helpers
  - future `ProjectContext`

- `server_registry.py`
  - future `BridgeRegistry`
  - context lookup and eviction

- `server_bridge_runtime.py`
  - transport invocation
  - lifecycle orchestration
  - recovery

- `server_cli_bridge.py`
  - interactive bridge commands

- `server_cli_batch.py`
  - batch commands

- `server_mcp_tools.py`
  - MCP tool-call adapters

- `server_mcp_protocol.py`
  - stdio JSON-RPC service shell

- `server_batch_runner.py`
  - generic batch operation helpers

- `server_batch_regression.py`
  - version sweep and candidate comparison logic

- `server_response_normalization.py`
  - lifecycle-aware response shaping

## Refactor Order For server.py

Do not split everything at once.

Safe order:

1. extract `server_mcp_protocol.py`
   - lowest behavioral risk
   - mostly mechanical move

2. extract `server_mcp_tools.py`
   - clean separation between MCP adapter layer and CLI layer

3. extract `server_cli_bridge.py`
   - bridge-facing subcommands only

4. extract `server_cli_batch.py`
   - batch-heavy subcommands next

5. extract `server_batch_runner.py` and `server_batch_regression.py`
   - reduce the heaviest non-core logic

6. extract `server_project_context.py`
   - prepare the ground for `ProjectContext`

7. introduce `server_registry.py`
   - add `BridgeRegistry` only after the surrounding file boundaries are clean

This order reduces merge risk and keeps each step reviewable.

## Refactor Safety Rules

During the split:

- preserve function signatures until behavior is proven unchanged
- prefer moving code first, then renaming
- keep imports explicit
- run regression proof after each extraction step
- do not combine module extraction with behavioral multi-project changes in one
  patch unless unavoidable

## Minimum Proof After Each server.py Split

After each extraction step, rerun at least:

- `request-status`
- `request-status-summary`
- `request-final-status`
- `request-project-refresh`
- `ensure-ready`
- one compile command
- one lifecycle fault route if transport/lifecycle code moved

This keeps refactor risk bounded.

## What Must Not Be Lost

These current strengths must survive the multi-project refactor:

- compact recovery by `request_id`
- clear split between transport failure and Unity failure
- same-host `tcp_loopback` portability
- file IPC fallback
- lifecycle fault-injection proof
- request journal as the strongest reconnect evidence
- compile-first validation discipline
- explicit `projectRoot` routing

## Open Questions

Questions to keep active during implementation:

1. Should `ProjectContext` own transport switching automatically, or should
   transport choice remain primarily Unity-published with host fallback only?
2. How aggressive should ANR auto-kill policy be by default?
3. Which operations are safe enough for automatic retry after lifecycle reset?
4. How much of the structured transport block should be added to
   `bridge_state.json` without breaking existing wrappers?
5. Should background editor launch policy be fully unified across platforms, or
   remain best-effort with host-specific feature flags?

## Working Verdict

The supplied multi-project specification is the correct next architectural
direction.

For this codebase, the right move is not a restart.
It is an evolution:

- keep the current lifecycle and recovery model
- wrap it in `BridgeRegistry` and `ProjectContext`
- formalize cross-platform discovery and ANR policy
- preserve backward compatibility for current operators and wrappers

This document should be treated as the local implementation draft until a
smaller, proven subset is promoted into the public `AIRoot` design surface.
