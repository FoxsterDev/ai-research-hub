# XUUnity Light Unity MCP Retro: PlayMode Verdict Recovery And Single-Project Launch Safety

Date: `2026-05-15`
Status: `applied`

## Executive Summary

The PlayMode verdict recovery work produced a usable day-to-day MCP validation
surface, but the closeout exposed one operator-facing startup safety gap:
`open-editor` could still create a second Unity splash for the same project
during a narrow launch/closeout race. Unity then showed an interactive modal
instead of letting the MCP path recover non-interactively.

The issue was not a Unity test failure. It was an MCP host workflow failure:
the operator path mixed recovery, direct launch, and manual process cleanup for
one same project before proving that the previous editor session had fully
exited or become reusable.

## Evidence Base

- Live MCP package self-tests passed through the same-host editor lane:
  EditMode `6/6`, PlayMode `5/5`.
- The PlayMode verdict recovery proof suite passed and verified:
  passed verdict counts, persisted scenario reconciliation after polling
  timeout, started runtime timeout classification, cleanup guidance, and final
  healthy/edit state.
- A Unity modal was observed stating that another Unity instance was already
  running with the same project open.
- `recover-editor-session --open-editor` also exposed a host-side Python helper
  mismatch, now covered by regression tests.
- The proof smoke initially cleaned its nested generated assembly folder but
  left the generated root/meta assets; the cleanup was tightened and re-run.

## Timeline

1. P0/P1/P2 recovery code and package self-tests were added.
2. Live PlayMode runtime-timeout proof left the editor in a dirty Test Runner
   scene after a deliberately interrupted run.
3. The operator tried a temporary scene-cleanup hook, then graceful quit, then
   recovery, then direct reopen.
4. The recovery helper crashed before finishing its `--open-editor` path.
5. A direct open path was used while the same project had not been cleanly
   proven closed or reusable, producing Unity's multiple-instance modal.
6. The editor state was recovered, package self-tests and proof smoke were
   re-run, and generated proof artifacts were removed.
7. The public host now has regression coverage for both the recovery helper and
   same-project launch-in-progress reuse.

## What Worked Well

- Request journals and final-status recovery were sufficient to distinguish
  Unity-side test outcomes from wrapper/runtime outcomes.
- The compact PlayMode verdict fields made the important result visible without
  raw log digging.
- `request-playmode-set --action exit` was the correct cleanup command for a
  PlayMode timeout; `restore-editor-state` alone was not enough for that case.
- Package self-tests are a useful fast regression gate for ordinary MCP changes.

## What Worked Poorly

- The operator path escalated too quickly from MCP recovery to direct process
  management and direct editor open.
- `restore-editor-state` was used as if it were a PlayMode cleanup command. It
  only owns host-opened editor closeout.
- `recover-editor-session --open-editor` was not covered by a regression test
  and crashed on a helper return-shape mismatch.
- `open-editor` did not mark launch-in-progress before invoking Unity, leaving
  a race where a second open could be attempted for the same project.
- The proof smoke did not initially verify that its own generated root folder
  was removed from the consumer project.

## What Was Not Explicit Enough

- Opening an editor and recovering a running editor are different operations.
- A same-project Unity launch must be single-flight: if an editor is launching,
  the next open attempt must reuse/wait, not spawn a second process.
- PlayMode timeout cleanup should prefer `request-playmode-set --action exit`.
- After a runtime-timeout proof, the next validation step should explicitly
  assert a clean scene or reopen only after closeout is verified.

## What The Operator Needed

- A non-interactive guard preventing a second same-project Unity open during
  launch/closeout races.
- A compact answer for whether the MCP is ready for normal day-to-day work.
- A reusable proof command that validates recovery behavior and cleans up its
  generated assets.
- Documentation that explains which recovery command applies to PlayMode state
  versus editor lifecycle state.

## Scoring

| Category | Score | Notes |
| --- | ---: | --- |
| Unity-side execution stability | 8/10 | Normal EditMode/PlayMode self-tests and proof lanes pass. |
| Request journaling quality | 9/10 | Sufficient for final-status and scenario reconciliation. |
| Bridge health observability | 8/10 | Transport and request-flow state are clear after P2. |
| Wrapper-to-operator clarity | 7/10 | Verdicts are clear; startup modal prevention needed the new guard. |
| Recovery guidance quality | 8/10 | PlayMode cleanup command is now concrete. |
| Transport lifecycle transparency | 8/10 | `tcp_loopback` default and `file_ipc` fallback wording are clear. |
| End-to-end trustworthiness during churn | 8/10 | Proofed for requested verdict paths; launch race was the main gap. |
| Parallel request handling | 7/10 | Per-project locks exist; launch single-flight needed tightening. |
| Token efficiency | 8/10 | Compact summaries reduced raw-log dependence. |
| Time-to-diagnosis | 7/10 | Good evidence existed, but operator flow still wandered. |
| Validation workflow discipline | 7/10 | Package/proof gates are good; closeout ordering needed docs. |

## Priority Improvements Applied

1. `recover-editor-session --open-editor` now uses a distinct helper that
   returns both parsed JSON and process status.
2. Host tests cover the recovery helper regression.
3. `open-editor` now writes a short launch-in-progress host session before
   invoking Unity.
4. A second `open-editor` during that window reuses the in-progress launch
   instead of spawning another Unity instance.
5. Host tests cover the launch-in-progress reuse path.
6. The proof smoke removes both its generated proof folder and generated root
   meta asset when it created the root.
7. README and CONTINUATION document the day-to-day readiness and startup safety
   rule.

## Remaining Ordinary Day-To-Day Risks

- If a human manually opens Unity at the same time the helper opens it, Unity's
  own launcher can still race outside MCP's process. The MCP side now avoids
  creating that race itself.
- If Unity shows an OS-level modal, the bridge cannot dismiss it; the operator
  should close the modal and run `project-discovery-report` or `ensure-ready`
  rather than retrying `open-editor`.
- Runtime-timeout PlayMode proofs intentionally stress the Test Runner harder
  than normal development. Ordinary package self-tests and scenario runs should
  use the compact recovery flow before retrying.
- Closed-project batch lanes must still refuse to run while the same project
  editor is open.

## Public-Promotion Recommendations

- Keep package self-tests as the default post-change MCP validation gate.
- Use the PlayMode verdict recovery proof suite for lifecycle/verdict changes,
  not for every small doc-only edit.
- Document the split:
  - PlayMode cleanup: `request-playmode-set --action exit`
  - host-opened editor cleanup: `restore-editor-state`
  - editor startup/reuse: `ensure-ready --open-editor`
- Keep startup helpers single-flight per project.

## Final Verdict

The MCP is suitable for normal day-to-day same-host development operations
after this work: status, compile, project refresh, EditMode tests, PlayMode
tests, scenario runs, and package self-tests have a usable compact operator
surface and recovery story.

It is not yet a fully unattended production orchestration platform. The
remaining risks are mostly around human/manual Unity interaction, OS-level
modals, and intentionally adversarial lifecycle tests.
