# Project Hook And Batch Build Operator Retro

Date: `2026-05-21`
Status: `public-safe retro`

## 1. Executive Summary

This session did not expose a hard Unity-side validation failure. The key MCP
operations completed: a project-defined hook scenario ran successfully, compile
matrix validation passed, a closed-project Android batch build succeeded, and
the final installed build was manually verified on device.

The useful lesson is operator experience rather than correctness: lifecycle
churn around project refresh was recoverable and correctly journaled, but the
default path still required the operator to know when to ask for final status.
The closed-project batch build was trustworthy, but its long silent interval and
large raw logs made it more expensive than necessary to monitor and summarize.

Exact consumer-project paths, package names, and request ids were inspected
locally and intentionally omitted from this public-safe report.

## 2. Evidence Base

- Chat/session timeline from the completed fix and validation work.
- Request journal events under the consumer project's MCP request journal.
- Compact `request-final-status` evidence for a refresh request that completed
  and was then reclassified after bridge generation changed during post-request
  settle.
- Compact `request-status-summary` evidence after closeout, showing the editor
  offline with stale state classified as recoverable.
- Batch build result JSON for a successful Android DevBuild.
- Raw batch log sizes, with roughly 1 MB of prepare/build logs versus a compact
  sub-1 KB build result.
- Current public docs: `README.md`, `DESIGN.md`, `CONTINUATION.md`,
  `SMOKE_TESTS.md`, and this retro prompt.

## 3. Timeline

1. The operator requested a project-defined MCP hook to regenerate LinkMerge
   XML.
2. The hook was added and run through an MCP scenario.
3. A project refresh crossed a bridge generation change after Unity had already
   completed the refresh.
4. Request journal evidence recorded submitted, started, completed, and
   reclassified events for the same request.
5. `request-final-status` proved `operation_outcome=completed_ok` and
   `result_trust_class=unity_completed_confirmed`.
6. Compile matrix validation passed.
7. A follow-up Android notification icon fix required a real Android batch
   build because script-only compile could not prove resource packaging.
8. The batch build completed successfully and produced a compact build result.
9. The APK was inspected for resource entries, installed on a device, and
   manually verified by the operator.
10. After closeout, `request-status-summary` correctly reported the editor as
    offline/stale with a recover-editor recommendation, not as an ANR or live
    validation failure.

## 4. What Worked Well

- Request journaling had enough information to separate Unity completion from
  bridge lifecycle churn.
- `request-final-status` gave the right terminal answer for the reclassified
  refresh: Unity completed and the result was confirmed.
- Compact status output after closeout classified stale/offline state correctly.
- Batch build output included the authoritative build result, output path,
  identifiers, version code, and warning/error counts.
- The validation lane choice was sound: project hook scenario for editor
  behavior, compile matrix for script safety, Android batch build for packaged
  resource proof, and manual device check for final visual confirmation.

## 5. What Worked Poorly

- The operator still had to know that a reclassified refresh should be followed
  by `request-final-status`; the scenario path did not make that recovery
  obvious enough at the moment of churn.
- The batch build was effectively silent for several minutes from the chat
  operator's point of view.
- The batch build result was compact and useful, but it did not include a
  first-class "artifact probe" section for packaged resources, so the operator
  manually inspected the APK.
- Build validation mutated project-local generated files that had to be
  identified and restored manually.
- Raw logs were large enough that the default operator path should strongly
  prefer compact summaries and targeted probes.

## 6. What Was Not Explicit Enough

- Project-defined hook scenarios need a clearer single-hook success summary:
  hook name, Unity request id class, terminal scenario status, and hook payload
  verdict.
- Refresh lifecycle reclassification should surface as "completed but
  reclassified; run final-status only if you need proof" rather than looking
  like generic churn.
- Batch build wrappers should make "no output yet, still running" an expected
  state with periodic phase/progress hints.
- Batch build closeout should explicitly list generated project files that were
  modified as side effects.

## 7. What The Operator Needed But Did Not Have

- A low-token progress heartbeat for long batch builds.
- A compact artifact-probe contract for APK/AAB resource or manifest checks.
- A post-build dirty-file side-effect report grouped as:
  `expected build mutation`, `unexpected tracked mutation`, and `user-owned
  preexisting dirty state`.
- A recovery hint attached directly to lifecycle reclassification summaries.
- A project-defined hook result summary that can be pasted into closeout without
  reopening raw scenario result JSON.

## 8. Scoring

Scores use `1` as poor and `5` as strong.

- Unity-side execution stability: `4/5`
- Request journaling quality: `5/5`
- Bridge health observability: `4/5`
- Wrapper-to-operator clarity: `3/5`
- Recovery guidance quality: `4/5`
- Transport lifecycle transparency: `4/5`
- End-to-end trustworthiness during churn: `4/5`
- Parallel request handling: `not stressed`
- Token efficiency of the default operator path: `3/5`
- Time-to-diagnosis: `4/5`
- Validation workflow discipline: `5/5`

## 9. Priority Improvements

1. Add batch-build progress heartbeats.
   - Emit a compact line or JSON event at phase boundaries and then at a slow
     interval while Unity is still running.
   - Include elapsed time, current known phase, output log path, and whether the
     process is still alive.

2. Add batch-build artifact probes.
   - Let wrappers declare expected APK/AAB contents such as drawable resources,
     manifest entries, or library artifacts.
   - Return `artifact_probe_summary` in the final build JSON.

3. Add dirty-file side-effect accounting.
   - Before and after batch validation, capture tracked generated files that
     changed.
   - Return a compact `workspace_side_effects` section with suggested cleanup
     commands, without running destructive cleanup automatically.

4. Improve project-defined hook scenario summaries.
   - For a scenario with a single `project_defined_hook`, bubble up hook name,
     hook outcome, and hook payload flags into the top-level scenario result
     summary.

5. Make lifecycle reclassification easier to consume.
   - If final status already proves `unity_completed_confirmed`, phrase the
     top-level operator message as confirmation, not as a warning-first
     lifecycle event.

## 10. Public-Promotion Recommendations

Promote to public docs or wrapper contracts:

- `SMOKE_TESTS.md`: add an "Artifact Probe Smoke" for Android resource and
  manifest checks after batch builds.
- `BUILD_AUTOMATION.md`: document batch-build progress heartbeats and
  workspace side-effect accounting.
- `CONTINUATION.md`: add a mini-playbook for reclassified refresh requests:
  if request completed and final status says `unity_completed_confirmed`, do not
  retry; continue with the next validation step.
- `README.md`: mention that batch builds can produce compact build results plus
  optional artifact probes, and that raw logs are backup evidence.
- Wrapper/runtime templates: add a generic `--artifact-probe` mechanism or a
  project wrapper hook for post-build APK/AAB inspection.

Keep project-local:

- The concrete hook name, resource names, Android package identifiers, build
  output names, and exact request ids.
- Any cleanup commands for generated files in the consumer project.

## 11. Final Verdict

Unity-side execution was stable enough for the work completed in this session.
The MCP request journal and final-status surfaces were sufficient to prove that
refresh lifecycle churn did not invalidate the operation. The main reusable
gap is operator cost: long batch builds and project-defined hook scenarios need
more compact progress, artifact, and side-effect summaries so future sessions
can avoid raw-log inspection and manual APK probing unless something actually
fails.

Concrete reusable changes should focus on wrapper output, not new validation
theory: batch progress heartbeats, artifact probes, dirty-file side-effect
reporting, and better top-level summaries for reclassified-but-confirmed
requests.
