# XUUnity Lightweight Unity MCP Rider-Grade Lifecycle Design

Date: `2026-05-05`  
Status: `follow-up design after live hardening`  
Scope: push the lightweight Unity MCP lane past the current host-orchestrated stability layer toward a more native backend model

Depends on:
- `historical host-local design source: XUUNITY_LIGHTWEIGHT_UNITY_MCP_SERVICE_DESIGN_2026-05-05.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/DESIGN.md`
- `host-local project lifecycle investigation evidence`

## Current Position

The current lane is already materially stronger than the initial file-IPC prototype:

- readiness is explicit
- activation policy exists
- refresh and play mode now wait for settled state
- compile matrix is build-config aware
- scenario automation is stable enough for checked-in smoke coverage

For the covered `ConsumerProject` lane, this is close to Rider-level usefulness.

It is not yet Rider-grade in lifecycle depth.

## Remaining Structural Gap Versus Rider

### 1. Transport and pump model

Current base:

- file IPC under `Library/XUUnityLightMcp/`
- request pumping on `EditorApplication.update`

Why Rider is stronger:

- its editor/backend connection is not framed as a passive file mailbox that only advances on the generic editor update tick
- its connection model is richer around reconnect, idle, and backend/editor state transitions

### 2. Lifecycle state model

Current exposed state is much better than before, but still shallow.

Still missing as first-class state:

- domain reload in progress
- asset import burst in progress
- package operation in progress
- script compilation requested versus compiling versus settled
- suspected modal dialog stall
- bridge bootstrap not yet reattached after reload

Rider is stronger here because it models more of the editor/backend lifecycle directly, rather than inferring everything from a smaller set of booleans.

### 3. Recovery model

Current lane mostly prevents failures or times out with better evidence.

It still does less than Rider in active recovery:

- no explicit reattach phase after reload
- no generation-based bridge session model
- no stronger reconnect protocol
- no request journal that survives lifecycle turbulence as a first-class protocol feature

## Target Outcome

Move from:

- `host wrapper compensates for a weak bridge`

Toward:

- `bridge exposes native lifecycle truth and host wrapper becomes thinner`

The host wrapper should still coordinate policy, but it should not need to infer most lifecycle truth indirectly.

## Design Changes

### Phase 1. Richer lifecycle state contract

Add new bridge-state fields:

- `bridge_session_id`
- `bridge_generation`
- `domain_reload_in_progress`
- `asset_import_in_progress`
- `package_operation_in_progress`
- `package_operation_name`
- `script_reload_pending`
- `modal_dialog_suspected`
- `bridge_bootstrap_attached`
- `request_journal_head`

Design rule:

- every field should be either direct evidence or clearly documented heuristic
- heuristic-derived fields must say so in docs

### Phase 2. Request journal instead of only inbox/outbox snapshots

Keep file IPC if needed, but add a proper request journal:

- request accepted
- request started
- request lifecycle phase changed
- request completed
- request abandoned due to lifecycle reset

Benefits:

- better reconnect semantics
- better scenario durability
- better postmortem evidence
- lower ambiguity after reloads or long package churn

Implemented start:

- `bridge_version = 5`
- `bridge_session_id`
- `bridge_generation`
- `bridge_bootstrap_attached`
- `domain_reload_in_progress`
- `asset_import_in_progress`
- `package_operation_in_progress`
- `package_operation_name`
- `script_reload_pending`
- `request_journal_directory`
- `request_journal_head`
- persisted journal events:
  - `bridge_bootstrap_attached`
  - `request_started`
  - `request_completed`
  - `request_abandoned`
  - `request_reclassified`

### Phase 3. Generation-aware reconnect protocol

Introduce:

- `bridge_generation`
- `session_epoch`
- request ownership rules across generation changes

Behavior:

- if domain reload or bridge rebootstrap occurs, host detects generation change
- in-flight requests are reclassified cleanly:
  - retryable
  - terminal failed
  - abandoned due to lifecycle reset

This is where the current lane can move beyond “wait and hope the same request id still makes sense”.

Implemented start:

- the bridge now emits generation/session identity in both `bridge-state` and `unity.status`
- host timeout summaries now include generation/session/journal-head evidence
- a live package refresh rebootstrap was previously observed as:
  - lifecycle before refresh on `bridge_version = 3`
  - lifecycle after settle on `bridge_version = 4` with a new session identity
- the next lifecycle-state layer is now live-validated as `bridge_version = 5`
- however, current evidence on `ConsumerProject` shows that an already-open editor session may keep running previously loaded file-package code until a real recompilation/rebootstrap cycle occurs; plain refresh/resolve alone was not enough
- the host now classifies transport waits that cross bridge generation/session changes
- idempotent operations may retry once automatically after a retryable lifecycle reset
- this reconnect path is implemented
- `request_reclassified` is now covered by a dedicated live fault-injection route
- `request_abandoned` still needs a narrower in-flight reload probe if we want explicit proof for that event too

### Phase 4. Native settle watchers inside Unity

Today some settle semantics are still host-derived.

Move more of that inside Unity:

- refresh settle watcher
- compile settle watcher
- package resolve settle watcher
- play mode transition watcher

The host should still enforce timeouts, but Unity should emit more of the completion truth itself.

Implemented start:

- `unity.project.refresh` now starts a Unity-side settle tracker
- live bridge state exposes refresh settle progress and completion fields
- host wrapper now prefers `completion_basis: unity_refresh_settle_watcher` when Unity settle evidence is present
- live `ConsumerProject` validation now shows refresh completing through the Unity watcher instead of only `host_waited_for_editor_idle`
- `unity.compile.player_scripts` and `unity.compile.matrix` now start a Unity-side compile settle tracker
- compile payloads can now report `completion_basis: unity_compile_settle_watcher`
- nested scenario `compile_player_scripts` steps now wait for the same compile settle contract before reporting terminal step success
- `unity.playmode.set` now starts a Unity-side playmode transition watcher
- pending playmode transition state is persisted across bridge rebootstrap
- live `ConsumerProject` stress validation now shows Finder-frontmost top-level `playmode.set enter/exit` completing through `unity_playmode_transition_watcher`
- async request handling now retains active request ownership until deferred completion callback
- live `ConsumerProject` fault validation now proves `request_abandoned` on an in-flight `unity.tests.run_editmode` request during domain reload

### Phase 5. Stronger transport option

The likely end-state is not “delete file IPC immediately”.

Recommended path:

1. keep file IPC as baseline fallback
2. define an internal transport abstraction
3. add a stronger same-host transport option later:
   - localhost HTTP
   - named pipe / domain socket
   - or a lightweight editor-hosted local RPC surface

Decision rule:

- do not replace file IPC until the stronger transport has better crash/reload behavior in real Unity sessions

Implemented start:

- host wrapper now resolves transport through an internal adapter layer instead of hard-wiring lifecycle orchestration directly to file inbox/outbox paths
- current supported adapters are:
  - `file_ipc`
  - `tcp_loopback`
- `tcp_loopback` uses `127.0.0.1` TCP specifically to stay viable on macOS, Windows, and Linux
- lifecycle responses now carry transport metadata, which keeps live evidence attached to the same request/retry/settle path
- `ConsumerProject` live validation after this refactor still passes:
  - compact post-change suite
  - lifecycle stress suite
  - reclassified lifecycle fault suite
  - request-abandoned async fault suite
- live transport proof in this repo is currently on macOS; Windows/Linux are covered by transport choice and implementation constraints, but still need separate host validation runs before claiming runtime proof there
- a checked-in transport-matrix route now exists for this host:
  - `host-local transport matrix smoke runner`
  - it exercises both `file_ipc` and `tcp_loopback`
  - it forces a real reload between transport switches instead of assuming config-only hot pickup

## Stress Validation Plan

To beat Rider on practical reliability, validation must move beyond happy path.

Required stress classes:

1. frontmost app not Unity
2. background refresh
3. background scenario execution
4. repeated `ensure-ready` while editor stays open
5. compile after prior scenario work
6. domain reload during bridge-enabled session
7. package resolve churn
8. simulated reconnect after bridge generation change

## Implemented Start

This follow-up already adds a first host-local lifecycle stress suite:

- `host-local lifecycle stress smoke runner`

Current scope:

- Finder frontmost status
- Finder frontmost refresh
- Finder frontmost contract scenario
- repeated `ensure-ready`
- final status sanity

This is not sufficient for Rider-grade proof yet, but it starts validating the right failure class instead of only happy path.

It also now includes the first public generation-aware protocol layer:

- generation/session identity in bridge state
- persisted request journal events
- host-side timeout/error summaries enriched with bridge identity evidence

## Best-Next Engineering Order

1. Expand bridge state to generation-aware lifecycle truth.
2. Add request journal.
3. Add reload-aware reconnect handling.
4. Move refresh/package/compile settle truth further into Unity.
5. Validate a stronger transport option only after the richer lifecycle contract exists.

## Success Bar

Call this better than Rider only when all of the following are true:

- covered stress suite passes repeatedly
- reload/reconnect semantics are explicit rather than inferred
- package churn and compile churn are first-class states
- scenario automation survives lifecycle turbulence without ambiguous result states
- host wrapper policy is thinner because bridge truth is stronger, not because validation was weakened
