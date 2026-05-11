# XUUnity Light Unity MCP Batch Compile Gate And Recovery Design Patch

Date: `2026-05-11`
Status: `public-safe working design patch`
Scope: `startup, reopen, health diagnosis, closeout, recovery`

## Executive Summary

This patch defines the next reliability slice for `XUUnity Light Unity MCP`.

The immediate problem is not lack of functionality. The problem is that the
current lifecycle path still allows the wrong transition order:

1. batch work mutates project state
2. snapshot restore runs
3. GUI reopen happens immediately
4. Unity hits a compile blocker or modal startup state
5. health/reporting continues to read stale log evidence

That shape is too optimistic for a validation-oriented MCP.

The patch has three `P0` changes:

1. add a non-interactive compile gate before GUI reopen after batch work
2. make editor-log diagnosis session-scoped instead of tail-of-whole-file
3. make closeout verification and stale-state cleanup first-class operator truth

This patch also defines a stricter separation between:

- validation lane
- recovery lane
- manual inspection lane

Generic popup clicking is intentionally out of scope for the default path.

## Why This Patch Is Needed

Current public and project-local behavior already contains most of the right
pieces:

- `templates/server.py` already exposes:
  - `batch-build-config-compile-matrix`
  - `request-build-config-compile-matrix`
  - `request-status-summary`
  - `request-final-status`
- `templates/server_editor_host.py` already distinguishes:
  - `closed_via_unity_editor_quit`
  - `quit_ack_without_exit_sigterm_recovered`
  - `quit_ack_without_exit`
- `templates/smoke/run_post_change_validation.sh` already uses compile-first
  validation ordering

The remaining gap is orchestration quality.

Today `AIOutput/Projects/ApperfunHub/Operations/XUUnityLightUnityMcp/apperfunhub_wrapper_commands.sh`
still reopens the GUI directly after batch work and snapshot restore. That is
the wrong default for a validation wrapper.

At the same time, `templates/server_health.py` diagnoses editor state from a
raw recent tail of `Editor.log` without a session boundary. Old compile blockers
can continue to poison later health summaries even after the code has been
fixed or after a new startup attempt begins.

## Design Goals

1. Never reopen GUI automatically after batch work unless compile preflight is
   green.
2. Treat validation, recovery, and manual inspection as separate lanes with
   explicit policy.
3. Prefer compact structured evidence over log-tail guesswork.
4. Make host closeout truth visible enough that an agent does not need to infer
   whether Unity really exited.
5. Avoid default GUI automation against unknown modal dialogs.
6. Keep the public design generic and reusable across Unity projects, while
   letting host-local wrappers choose stricter defaults.

## Failure Taxonomy

This patch introduces a clearer failure taxonomy.

### 1. `compile_red_after_batch_restore`

Meaning:
- batch work and restore succeeded
- project is not ready for interactive editor startup

Required behavior:
- block GUI reopen
- emit compact compile-gate summary
- return a recovery recommendation

### 2. `interactive_startup_blocked_by_dialog`

Meaning:
- editor process exists
- bridge cannot become healthy because Unity is blocked by compile or safe-mode
  dialog state

Required behavior:
- classify as startup blocker, not generic stale health
- recommend batch compile or manual recovery path

### 3. `quit_ack_without_exit`

Meaning:
- Unity accepted `unity.editor.quit`
- process did not exit in bounded time

Required behavior:
- report this as incomplete closeout
- surface whether host escalation recovered it

### 4. `stale_log_blocker`

Meaning:
- health/status still reports an old compile blocker from `Editor.log`
- current startup attempt may already be different

Required behavior:
- scope diagnosis to the active startup/editor session
- mark fallback mode explicitly when no session cursor exists

### 5. `stale_bridge_after_forced_close`

Meaning:
- host-side process termination happened
- bridge/host session state still implies a live or recently authoritative lane

Required behavior:
- prune stale authority aggressively
- downgrade to offline or recovery-needed state based on current evidence

## Target Behavioral Contract

## 1. Reopen Policy

Introduce explicit reopen policy for any wrapper path that closes Unity,
executes batch work, and may reopen the editor.

Working values:

- `immediate_gui`
- `batch_compile_gate`
- `manual_recovery`

Required default for validation-oriented batch hooks:

- `batch_compile_gate`

Contract:

1. close editor if needed
2. run batch operation
3. restore snapshot
4. run non-interactive compile preflight
5. only on green result:
   - reopen GUI with `ensure-ready --open-editor`
6. on red result:
   - do not reopen GUI automatically
   - return structured summary with recovery guidance

## 2. Session-Scoped Log Diagnosis

Health diagnosis must stop treating the whole recent tail of `Editor.log` as
current truth.

Add a session log scope with:

- `log_session_started_utc`
- `log_session_start_mtime`
- `log_session_start_offset_bytes`
- `log_scope_source`

Working sources:

- `host_opened_editor_session`
- `bridge_bootstrap_attach`
- `tail_fallback`

Rules:

- if the host opened the editor, diagnosis uses the stored file offset/mtime
  boundary
- if a live bridge is already present, diagnosis may additionally use bridge
  bootstrap timestamps as a stronger lower bound
- if no scoped boundary exists, diagnosis may still use the old tail fallback,
  but it must mark the result as fallback-derived

Required summary addition:

- `editor_log_scope`

Example:

```json
{
  "editor_log_diagnosis": {
    "code": "interactive_compile_block_detected",
    "severity": "error",
    "summary": "Compilation errors were detected during interactive startup.",
    "scope": {
      "source": "host_opened_editor_session",
      "start_offset_bytes": 184320,
      "fallback_used": false
    }
  }
}
```

## 3. Closeout Verification Contract

Closeout classification already exists internally. This patch makes it a
required operator-facing truth surface.

Every restore/close path should return:

- `closeout_verified`
- `closeout_classification`
- `close_path`
- `live_project_editor_pids`
- `recommended_next_action`

Required rule:

- if `closeout_verified=false`, no later lifecycle step may treat the editor as
  cleanly restored

## 4. Recovery Lane Contract

Add a dedicated recovery path rather than forcing operators to chain ad hoc
commands.

Working command shape:

- `recover-editor-session --project-root <path>`

Target responsibilities:

1. classify current state
2. verify whether a host-opened session still exists
3. attempt closeout if appropriate
4. prune stale authority if the process is already gone
5. if startup was blocked by compile state:
   - run compile probe in non-interactive lane
6. return one compact structured recovery report

This command belongs in the public MCP surface because the problem is generic.

## 5. Dialog Policy

Introduce explicit dialog policy. Do not default to generic GUI clicking.

Working values:

- `observe_only`
- `known_safe_dialogs_only`
- `manual_recovery_only`

Required default:

- `observe_only`

`known_safe_dialogs_only` is a future, opt-in lane. It should never be part of
the default validation path, and any auto-dismiss result must be surfaced as an
explicit artifact, not hidden behavior.

## File-Level Patch Plan

## Slice A: Compile Gate Before GUI Reopen

Primary files:

- `AIOutput/Projects/ApperfunHub/Operations/XUUnityLightUnityMcp/apperfunhub_wrapper_commands.sh`
- `templates/server.py`
- `templates/server_build_config.py`

Patch:

1. Change the project wrapper reopen path to use a compile gate instead of
   direct `ensure-ready --open-editor`.
2. For `ApperfunHub`, use:
   - `batch-build-config-compile-matrix`
3. On failure:
   - return a compact `compile_gate_summary`
   - set:
     - `editor_reopened=false`
     - `reopen_blocked=true`
     - `reopen_block_reason=compile_red_after_batch_restore`
4. On success:
   - continue to `ensure-ready --open-editor`

Rationale:

- this uses an already existing public capability
- it matches the compile-first validation contract already used by smoke flows
- it avoids opening GUI just to get stuck behind a modal compile blocker

## Slice B: Session-Scoped Log Diagnosis

Primary files:

- `templates/server_editor_host.py`
- `templates/server_health.py`
- `templates/server_summaries.py`

Patch:

1. Extend host session state with log scope metadata captured at editor open.
2. Add scoped log reader support in `server_health.py`.
3. Include `editor_log_scope` in status/health summaries.
4. Downgrade the old tail-only path to explicit fallback mode.

Rationale:

- current stale diagnosis is a correctness bug, not just a UX issue
- it can keep `interactive_compile_block_detected` alive after the underlying
  code was already fixed

## Slice C: Verified Closeout And Stale-State Cleanup

Primary files:

- `templates/server_editor_host.py`
- `templates/server.py`
- `templates/server_discovery.py`
- `templates/server_summaries.py`

Patch:

1. Surface closeout truth in compact summaries and restore responses.
2. After forced termination or verified dead pid:
   - clear stale host-opened session authority
   - downgrade stale bridge authority more aggressively
   - include current `live_project_editor_pids`
3. Prevent stale host session or stale bridge state from being treated as a
   healthy reopen candidate.

Rationale:

- today the raw logic exists, but the operator-facing truth is still too easy to
  misread

## Slice D: Recovery Command

Primary files:

- `templates/server.py`
- `templates/server_editor_host.py`
- `templates/server_health.py`

Patch:

1. Add `recover-editor-session`.
2. Route compile-blocked startup into:
   - verified closeout
   - batch compile probe
   - compact next action
3. Return one concise payload instead of forcing manual command assembly.

Rationale:

- the protocol already has most primitives
- the missing piece is one authoritative recovery composition

## Proposed Output Surface Additions

These fields should become stable compact outputs:

- `reopen_policy`
- `reopen_blocked`
- `reopen_block_reason`
- `compile_gate_summary`
- `editor_log_scope`
- `closeout_classification`
- `closeout_verified`
- `live_project_editor_pids`
- `recovery_classification`
- `recovery_recommended_next_action`

## Validation Strategy

## Unit Tests

Add or extend Python tests for:

- `tests/test_project_health.py`
  - scoped log diagnosis
  - fallback log diagnosis
  - stale-log blocker no longer poisoning fresh session summaries
- new or expanded editor-host tests
  - closeout classification
  - stale host session cleanup
  - recovery-command composition

## Smoke Coverage

Extend:

- `templates/smoke/run_post_change_validation.sh`

With assertions for:

1. compile gate runs before GUI reopen when batch hook requests reopen
2. failed compile gate blocks GUI reopen
3. restore output exposes closeout verification
4. recovery path produces a compact structured recommendation

Project-local smoke extension:

- `AIOutput/Projects/ApperfunHub/Operations/XUUnityLightUnityMcp/smoke/ApperfunHub/run_mcp_post_change_validation.sh`

Should inherit the same compile-first behavior without custom divergence.

## Extraction Potential

Public-core candidates:

- `reopen_policy=batch_compile_gate`
- session-scoped editor-log diagnosis
- closeout verification as compact operator truth
- `recover-editor-session`
- explicit `dialog_policy`

Host-local wrapper candidate:

- `ApperfunHub` choosing `batch-build-config-compile-matrix` as the reopen
  gate default for build-hook flows

This is the right split:

- policy framework is public and reusable
- target compile-lane choice stays project-aware

## Recommended Implementation Order

### `P0`

1. `Slice A`
2. `Slice B`
3. `Slice C`

### `P1`

4. `Slice D`

### `P2`

5. optional whitelist-based dialog handling for manual recovery only

## Non-Goals

This patch does not recommend:

- blind generic popup clicking
- treating GUI reopen as part of compile validation
- trusting old `Editor.log` tail markers as session truth
- keeping stale bridge or host session authority after verified process death

## Decision

Adopt this patch as the next reliability-focused MCP design slice.

The wrapper already has enough functionality to support it. The main work is
policy wiring, scoped diagnosis, and stronger truth surfaces.
