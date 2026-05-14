# SDK Rollout MCP Portfolio Retro

Date: `2026-05-14`
Status: `public-safe chat retro`
Source prompt: `Retros/CHAT_RETRO_PROMPT.md`

## Executive Summary

The Unity-side MCP operations were mostly successful. The weak part was the
operator-facing SDK rollout lane: it allowed broad portfolio validation to
behave like many independent GUI-editor sessions instead of one controlled SDK
validation workflow.

The strongest evidence is request-journal data from the SDK validation run:
fresh journal entries across the portfolio show `request_submitted`,
`request_started`, and `request_completed` for refresh, EDM4U resolve,
dependency verify, compile, and editor quit requests. That means the core bridge
could execute requests.

The failure class was not a single Unity operation failure. It was insufficient
workflow control and trust accounting around:

- Android build-target precondition before EDM4U Android resolve
- GUI Unity process concurrency
- resolver output freshness and generated-file suspicious diff detection
- quit acknowledgement versus verified process exit
- connected-device and dashboard validation gaps
- compact portfolio-level closeout status

## Evidence Base

Evidence inspected:

- `AIRoot/Operations/XUUnityLightUnityMcp/Retros/CHAT_RETRO_PROMPT.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/README.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/DESIGN.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/CONTINUATION.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/SMOKE_TESTS.md`
- `AIRoot/Operations/XUUnityLightUnityMcp/Designs/XUUNITY_MCP_SDK_ROLLOUT_VALIDATION_DESIGN_2026-05-14.md`
- portfolio request journals under `Library/XUUnityLightMcp/journal/requests/`
- bridge state files under `Library/XUUnityLightMcp/state/bridge_state.json`
- host process-table evidence for editor PIDs referenced by bridge state

Public-safe evidence summary:

- The 2026-05-14 journal set contains request evidence for nine consumer Unity
  projects.
- Eight projects had current bridge-state files during the retro; one project
  had journal evidence but no current bridge-state file.
- Journal counts for the same date included:
  - one project with `28` files and `6` completed requests
  - one project with `53` files and `17` completed requests
  - six projects with `19` files and `6` completed requests each
  - one project with `49` files, `14` completed requests, and one reclassified
    request
- Common operations in the evidence set:
  - `unity.project.refresh`
  - `unity.edm4u.resolve`
  - `unity.sdk.dependency.verify`
  - `unity.compile.player_scripts`
  - `unity.editor.quit`
  - `unity.health.probe`
  - `unity.capabilities.get`
- At retro time, several bridge-state files still referenced editor PIDs that no
  longer existed in the host process table. This indicates stale state or
  incomplete closeout proof, not a proven Unity operation failure.
- User-observed evidence: too many GUI Unity instances were opened during the
  broad run, and some instances only progressed after manual UI interaction.
- User-observed evidence: Android resolver correctness requires switching to the
  Android platform before resolve; this was not enforced by the existing
  resolver lane.
- User-observed evidence: generated Android template removals should be treated
  as suspicious, not as acceptable dependency-update noise.

## Timeline

1. SDK update research identified a candidate mediated SDK update that required
   Android and iOS dependency validation.
2. The first project was updated and validated with package restore, EDM4U
   resolve, dependency verification, compile, and partial build/export checks.
3. The same update was then applied across a portfolio of related Unity
   projects.
4. Portfolio validation used live-editor MCP lanes for refresh, EDM4U resolve,
   dependency verification, compile, and editor quit.
5. The operator observed too many GUI Unity editors open concurrently and had to
   manually click Unity windows before some instances closed or continued.
6. The operator identified that Android resolver output depends on active
   Android build target, which was not enforced by the resolver command.
7. The operator identified that generated Gradle template damage must be treated
   as suspicious even when dependency versions appear correct.
8. A public SDK rollout validation design was added to capture resolver,
   generated diff, GUI concurrency, native artifact, and device validation gaps.
9. This retro converts that session into MCP reliability and operator-surface
   lessons.

## What Worked Well

- Request journaling provided enough evidence to distinguish Unity-side request
  execution from operator uncertainty.
- The bridge successfully handled repeated project refresh, EDM4U resolve,
  dependency verification, and compile requests across a portfolio.
- Compact request summaries and journal files were more useful than raw editor
  logs for proving request lifecycle.
- The existing MCP surface already had useful building blocks:
  - build target switch
  - EDM4U resolve
  - SDK dependency verify
  - compile player scripts
  - editor quit
  - bridge health and capability probes
- The follow-up SDK rollout design captured the correct P0 direction:
  Android target enforcement, batch EDM4U resolve, generated diff guard, GUI
  process cap, and quit-and-wait.

## What Worked Poorly

- The SDK validation workflow was too granular from the operator perspective.
  The operator needed one high-level SDK rollout validation lane, not a manually
  chained sequence of refresh, resolve, verify, compile, and quit calls.
- Android resolver preconditions were not encoded. The command could run without
  proving active Android build target.
- Resolver success was too easy to over-trust. A generated dependency appearing
  in one file did not prove all generated Gradle templates remained healthy.
- GUI concurrency was not controlled. Broad portfolio work could open more Unity
  editors than the host/operator could safely manage.
- `unity.editor.quit` request completion was not equivalent to verified process
  exit. Stale bridge-state PIDs after closeout made this distinction visible.
- Batchmode EDM4U feasibility was not productized. The operator suspected it
  should avoid GUI mode, but the public MCP lane had not yet made it the default
  or proven it through smoke coverage.
- Connected-device validation was outside the public surface, so device smoke
  for ad load/show/reward/revenue/consent remained manual.

## What Was Not Explicit Enough

- `unity.edm4u.resolve --platform android` should say whether it switched to
  Android or refused to run because the active target was wrong.
- Dependency verification should say whether outputs are fresh, stale, missing,
  or suspiciously changed.
- Closeout should report `quit_ack`, `process_exit_verified`,
  `stale_bridge_state_after_quit`, and the exact next recovery command.
- Portfolio validation should report global editor concurrency, active Unity
  PIDs, project ownership, and queueing decisions.
- The operator path should say when live GUI mode is being used only because no
  batch resolver lane is available.
- Reports should explicitly separate:
  - dependency presence
  - generated-file integrity
  - compile compatibility
  - build/export compatibility
  - device runtime behavior
  - dashboard/business metric checks

## What The Operator Needed But Did Not Have

- A single command for SDK rollout validation that owns the standard order:
  package restore, Android target switch, EDM4U resolve, generated diff guard,
  compile, optional export/build, optional device smoke.
- A default GUI process cap and queue for portfolio validation.
- A resolver command that either switches to Android before Android resolve or
  fails with a clear precondition error.
- A generated diff guard with critical-template deletion rules.
- A quit-and-wait command that proves process exit before the next project
  starts.
- A compact portfolio summary showing per-project:
  - request outcome
  - Unity operation outcome
  - active target
  - resolver output freshness
  - suspicious generated changes
  - compile status
  - closeout status
- A device smoke layer for USB-connected Android and iOS devices.

## Scoring

Scale: `1` poor, `5` strong.

| Category | Score | Notes |
| --- | ---: | --- |
| Unity-side execution stability | 4 | Requests generally completed across the portfolio. |
| Request journaling quality | 4 | Journals proved lifecycle for most operations; naming differences still add parsing friction. |
| Bridge health observability | 3 | Health exists, but stale bridge-state PIDs after closeout need clearer classification. |
| Wrapper-to-operator clarity | 2 | Too much lifecycle meaning had to be inferred from separate commands. |
| Recovery guidance quality | 2 | Manual clicking and ad hoc process inspection were still needed. |
| Transport lifecycle transparency | 3 | Journals and bridge generations help, but portfolio closeout is not compact enough. |
| End-to-end trustworthiness during churn | 3 | Unity completion was often provable, but stale state and GUI concurrency reduced confidence. |
| Parallel request handling | 2 | Same-host portfolio work needs a GUI cap and queue. |
| Token efficiency of default operator path | 2 | Many small command checks were required; summary-first portfolio output is missing. |
| Time-to-diagnosis | 3 | Evidence existed but was spread across journals, state files, process table, and user observation. |
| Validation workflow discipline | 3 | Correct order is now designed, but not yet enforced as a single lane. |

## Priority Improvements

### P0: Typed SDK Resolver Lane

Add a first-class SDK resolver flow:

- `sdk.package_restore`
- `sdk.android_resolve`
- `batch-edm4u-resolve`

Required behavior:

- enforce or perform active Android target switch before Android resolve
- run Version Handler when requested
- run EDM4U Android Force Resolve
- wait for resolver output freshness
- report the exact resolver menu/method used
- fail if known previous native dependency versions remain in generated outputs

### P0: Generated Diff Guard

Add `sdk.generated_diff_guard` after resolver and before compile.

It must classify generated changes as:

- expected dependency update
- resolver normalization noise
- suspicious deletion
- unrelated mutation

Default suspicious removals:

- Android `namespace`
- `ndkPath`
- `ndkVersion`
- Maven repositories
- signing blocks
- manifest placeholders
- custom packaging excludes
- custom Gradle plugin declarations

### P0: GUI Process Pool

Add host-side process control:

- global Unity GUI cap, default `3`
- SDK validation GUI cap, default `1`
- per-project open lock
- preflight active PID report
- queue instead of uncontrolled parallel open
- quit-and-wait before moving to the next GUI project

### P0: Closeout Truth Contract

Promote `request-editor-quit-and-wait`.

Pass condition:

- Unity quit request accepted
- target PID exits
- bridge state is removed, replaced, or classified stale
- compact output includes a final closeout classification

### P1: Portfolio SDK Validation Summary

Add a single compact report surface for multi-project SDK validation:

`portfolio-sdk-validation-summary`

Minimum columns:

`Project | Target | Restore | Resolve | Freshness | Generated Diff | Compile | Closeout | Next Action`

### P1: Native Artifact And Device Layers

Add optional lanes:

- Android export/build artifact verification
- Gradle dependency report parsing
- duplicate class detection
- iOS export, pod install, and Podfile.lock verification
- Android `adb` device install/launch/logcat smoke
- iOS attached-device install/launch/log collection when signing allows

### P1: SDK Smoke Hook Contract

Add a debug-only project hook contract for:

- SDK initialization status
- adapter/native SDK versions
- interstitial load/show/fail callbacks
- rewarded load/show/reward/fail callbacks
- banner load/show/fail callbacks
- paid revenue callback continuity
- consent/ATT/TCF state

## Public-Promotion Recommendations

Promote these reusable changes into public MCP docs and wrapper surfaces:

- README: add a short SDK rollout lane summary and link to the SDK rollout
  validation design.
- DESIGN: promote Android resolver precondition, generated diff guard, GUI cap,
  and closeout truth as lifecycle contracts, not only future feature ideas.
- SMOKE_TESTS: add SDK resolver target-switch smoke, generated diff guard smoke,
  GUI cap smoke, and quit-and-wait closeout smoke.
- CONTINUATION: add mini-playbook for broad SDK portfolio validation:
  prefer batch resolver, cap GUI, verify generated diffs, compile, then device.
- Wrapper output: whenever `request-edm4u-resolve --platform android` runs,
  include active target before/after and whether target switching happened.
- Wrapper output: whenever `unity.editor.quit` completes, surface that this is
  not process-exit proof unless quit-and-wait verified it.
- Summary surfaces: add portfolio rollup that avoids repeated raw journal
  inspection.

## Final Verdict

The MCP bridge was strong enough to execute the SDK validation primitives, but
the public operator path was not strong enough for high-risk portfolio SDK
rollout work.

The next improvement should not be another low-level command. It should be a
typed SDK rollout validation lane that owns ordering, resolver preconditions,
generated diff suspicion, GUI process limits, closeout proof, and compact
portfolio reporting.
