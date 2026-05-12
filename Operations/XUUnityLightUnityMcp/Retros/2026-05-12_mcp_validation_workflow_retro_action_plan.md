# MCP Validation Workflow Retro Action Plan

Date: `2026-05-12`
Status: `implemented`
Source artifact:
`Operations/XUUnityLightUnityMcp/Retros/2026-05-12_mcp_validation_workflow_chat_retro.md`

## Purpose

This plan converts a public-safe MCP validation workflow retro into concrete
operator and runtime hardening actions.

Private project names, local repository paths, branch names, commit ids,
product-specific test names, request ids, and local Unity `Library` artifacts
are intentionally excluded.

## Execution Contract

- `primary_task`: harden MCP validation workflow and closeout guidance
- `overlay_tasks`: validation lane discipline, batch conflict recovery,
  closeout truth, commit hygiene
- `primary_validation_lane`: public wrapper unit tests and source inspection
- `expected_evidence_class`: source artifact plus runtime/docs test coverage
- `public_boundary`: reusable public MCP behavior and xuunity delivery guidance

## Action Summary

| ID | Priority | Destination | Action | Outcome |
| --- | --- | --- | --- | --- |
| A1 | P0 | Public wrapper runtime | Add concrete recovery command to batch prepare conflict summaries | Operators know the next exact command after `editor_running_batch_conflict` |
| A2 | P0 | Public wrapper runtime | Make quit acknowledgement versus process exit explicit in short summaries | Operators do not treat `unity.editor.quit` acknowledgement as shutdown proof |
| A3 | P1 | Public docs and smoke contract | Strengthen compile-first precondition for changed C# scripts | Tests, scenarios, and GUI smoke are not attempted before a compile gate |
| A4 | P1 | Public post-change runner/docs | Add a compile-first closeout recipe | One command path handles status, lane decision, compile, then tests |
| A5 | P1 | XUUnity change delivery guidance | Add staged-file hygiene self-review before commit | Unrelated staged files are caught before commit |

## Detailed Actions

### A1. Batch Conflict Recovery Command

Target files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- `Operations/XUUnityLightUnityMcp/templates/server_batch_reporting.py`
- `Operations/XUUnityLightUnityMcp/tests/`

Implementation shape:

- Extend `editor_running_batch_conflict` details with:
  - `recommended_next_action=close_same_project_editor_or_use_interactive_lane`
  - `recommended_recovery_command=xuunity_light_unity_mcp.sh request-editor-quit --project-root {project_root} --timeout-ms 30000`
  - a note to verify process exit before rerunning the batch command
- Update batch prepare failure summaries to propagate the same next action and
  recovery command when the exception details provide them.
- Keep the summary generic and public-safe.

Acceptance checks:

- Batch prepare failure JSON contains `transport_outcome=batch_prepare_blocked`,
  `unity_outcome=not_started`, and a concrete `recommended_recovery_command`.
- Existing callers without recommendation details still get the generic
  `next_step`.
- Unit coverage simulates a live-editor batch conflict and verifies the
  recommendation fields.

### A2. Closeout Truth In Short Operator Output

Target files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- `Operations/XUUnityLightUnityMcp/tests/`

Implementation shape:

- Preserve the distinction between `closeout_verified` and
  `closeout_classification`.
- Ensure short summaries surface closeout mismatch details:
  - `closeout_classification=quit_ack_without_exit`
  - `closeout_verified=false`
  - `recovery_command=...`
- Prefer existing `restore-editor-state` and `recover-editor-session` paths
  over a second closeout mechanism.

Acceptance checks:

- A restore closeout mismatch prints both classification and recovery command.
- JSON payloads distinguish `quit_acknowledged` from
  `process_exit_verified`.
- No summary claims editor shutdown success unless process exit was verified.

### A3. Compile-First Precondition In Public Docs

Target files:

- `Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`
- `Operations/XUUnityLightUnityMcp/CONTINUATION.md`
- optionally `Operations/XUUnityLightUnityMcp/README.md`

Implementation shape:

- Tighten compile-gate language from preference to operator precondition for
  changed C# scripts:
  - run the fast compile gate before EditMode, PlayMode, scenario, or GUI smoke
  - exception: the task is explicitly investigating compile failure
- Keep target/profile specifics out of public docs.
- Reference compact summaries as the first evidence source before raw logs.

Acceptance checks:

- Public docs say changed scripts require compile-first ordering before heavier
  validation.
- Docs leave project-specific matrix selection to host-local or project-local
  routing.
- No project-specific paths, profile names, request ids, or session timestamps
  are promoted.

### A4. Compile-First Closeout Recipe

Target files:

- `Operations/XUUnityLightUnityMcp/README.md`
- `Operations/XUUnityLightUnityMcp/CONTINUATION.md`

Implementation shape:

1. Inspect editor state with `request-status-summary` or project discovery.
2. If the same project editor blocks batch, run `request-editor-quit`.
3. Verify process exit with `restore-editor-state` or
   `recover-editor-session`.
4. Run batch compile.
5. Only after compile passes, run batch tests or heavier validation.

Acceptance checks:

- The documented sequence can be followed without interpreting raw logs.
- The sequence treats batch conflict as `not_started`, not validation failure.
- The sequence makes process-exit verification mandatory before rerunning a
  closed-project batch lane.

### A5. Staged-File Hygiene Before Commit

Target file:

- `Modules/XUUnity/tasks/change_delivery.md`

Implementation shape:

- Add a self-review checkpoint before committing:
  - compare `git diff --staged --name-only` to the current commit unit file set
  - if unrelated staged files exist, unstage or move them to another commit unit
  - if generated files or lockfiles are staged, state why they belong
- Keep this as general xuunity delivery guidance, not MCP runtime guidance.

Acceptance checks:

- Change delivery guidance blocks accidental unrelated staged files.
- Existing commit-unit and staged-diff checks remain intact.
- The rule does not require reverting unrelated user work.

## Implementation Result

Applied public files:

- `Operations/XUUnityLightUnityMcp/templates/server.py`
- `Operations/XUUnityLightUnityMcp/templates/server_batch_reporting.py`
- `Operations/XUUnityLightUnityMcp/tests/test_server_protocol_and_parser.py`
- `Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`
- `Operations/XUUnityLightUnityMcp/CONTINUATION.md`
- `Operations/XUUnityLightUnityMcp/README.md`
- `Modules/XUUnity/tasks/change_delivery.md`

Validation:

- `python3 -m unittest Operations.XUUnityLightUnityMcp.tests.test_server_protocol_and_parser`
- `python3 -m unittest discover -s Operations/XUUnityLightUnityMcp/tests -p 'test_*.py'`

Result:

- Focused protocol tests passed.
- Full Python test suite passed.
