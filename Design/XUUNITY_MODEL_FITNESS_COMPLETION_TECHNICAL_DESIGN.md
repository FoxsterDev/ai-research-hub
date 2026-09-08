# Model Fitness completion: execution decision record

Status: engineering and bounded diagnostic allocation complete; qualification and rollout remain open. Evidence date: 2026-09-08 UTC.
Authority: `XUUNITY_MODEL_FITNESS_COMPLETION_GOAL_PROMPT.md`.
This record distinguishes engineering, diagnostic pilots, qualification, and rollout.

## Baseline and review checkpoint 1

The public baseline is revision `3fb4b640716641119e5cf28d66a0ef6e9522337a`.
Fresh baseline validation collected 178 operation tests (176 passed, two
OS-probe skips), 174 module tests (all passed), and 67 reference-host tests
(64 passed, three unavailable raw-transcript replays). These are test counts, not evidence of live model fitness. The host
and public operation are separate isolated task checkouts; neither is a link
to an active source checkout.

| Capability | Initial status | Existing evidence / smallest remaining action |
| --- | --- | --- |
| W1 compile receipt | partial | Host compile oracle accepts a tree hash; add a permitted real compiler producer, freshness/provenance checks, and final-tree binding. |
| W2 executor | missing | `model_fitness/fixtures.py:evaluate_run` composes parsing and scoring, but no public launcher calls it. Integrate preparation, calibration, process capture, gate reconciliation, and replay. |
| W3 schedule | partial | `suite.py` checks roster and replicates; add prelaunch seed, timeout and budget identity plus atomic launch accounting. |
| W4 holdout | partial | `f6.py` verifies signed results; author a host payload and persist exposure/rotation state. Qualified live exposure requires a suitable surface. |
| W5 reporting | partial | Run/suite renderers exist; render persisted execution accounting and independent fitness health projections. |
| W6 experiments | partial | `experiment.py` evaluates completed arms; execute fixed cohorts and persist family spending with apply authority separate. |
| W7 rollout | missing | Resolver/loader/gate work deterministically; collect live task conformance before adding an advisory route. |
| W8 delivery | partial | Components already have committed history; extend the existing OS CI matrix and pin tested executor revisions. |
| W9 knowledge | partial | Public ruleset probes and integration instructions exist; add host probes and a durable stale-baseline/pending-smoke hook. |

At the initial checkpoint, the reviewed code had four material gaps. First, `evaluate_run` defaults
`f0_calibration_passed=True`, so an omitted argument can authorize scoring.
Second, its hand-authored fixture groups are evaluated without the public
derive/check/reconcile pipeline. Third, it supplies empty execution metadata
to `inspect_run_validity`, losing process timeout and exit evidence. Fourth,
the receipt consumer cannot distinguish a fresh trusted compiler receipt from
an old same-tree document. The existing unit results do not close these gaps.
The original design has **35** end-to-end acceptance criteria; the older
completion plan's 27-item mapping is incomplete.

Code-review judgment for this integration path: 56/100, 34 below the 90-point
target, medium confidence. Dimension contributions: correctness 10/20,
ownership 11/15, resilience 8/15, boundary integrity 8/15, validation 8/15,
operability 4/10, maintainability 7/10. The deterministic components are useful,
but the then-unintegrated live path did not justify operator confidence. These are
engineering review judgments and must never enter the model-fitness score.

## Ownership and selected shape

Use ordinary Python functions and standard-library processes/files. The public
executor owns explicit-input preparation, launch lifetime, capture and replay;
the public schedule owns preregistration and launch claims. Reuse `baseline`,
`attestation`, `isolation`, `adapters`, `fixtures`, `scoring`, `suite`, `stats`
and `experiment`. A host binding supplies confidential seeds, supported CLI
authentication configuration, compiler configuration and output paths. Keep
the legacy scorer for historical diagnostics and converge its launch path onto
the executor after parity checks. Do not copy host fixture identities or
transcripts into this repository.

A new universal provider framework would add a second configuration and
lifecycle system. A transport proxy would disguise absent request-boundary
support. Neither is required. The chosen executor reports capability limits;
only the existing exclusive broker can authorize writes. Native CLI file edits
remain audited even if an outer sandbox passes read/write probes.

## Complete flow

1. Inspect the executable version, official subscription login, launch flags
   and event grammar. Fingerprint parser, executable/profile and calibration
   implementation. Scrub API-key variables and prohibit billing fallback.
2. Run deterministic F0 cases and a bounded live canary. Persist its raw events
   and a calibration record bound to those identities. Distinguish diagnostic
   parser compatibility from scoring eligibility. An unavailable request
   boundary or immutable backend identity stays unavailable.
3. Verify fixture document, task, seed and implementation hashes. Copy the seed
   into an attempt-owned directory and reject path aliases, special files and
   workspace/protected-root overlap. Build the task envelope, derive obligations
   and construct the loader bundle. Freeze host helper bytes in preparation v2;
   replay validates that archive without executing it, while launch also checks
   the live helper. Bundle construction does not prove delivery.
4. Persist a complete schedule before launching: ordered attempt/fixture/profile
   identities, seed allocation, replicate blocks, timeout, aggregate ceiling,
   and stop rule. Create each launch claim exclusively before spawning. A
   second caller or ambiguous interrupted launch cannot spend the same row.
5. Run the CLI with its recorded permissions and bounded lifetime. Capture raw
   stdout, stderr, exit status, terminal events, usage and observed mutations.
   Treat missing/truncated/unknown events as measurement limitations. Probe the
   exact supported execution policy; a probe for another policy gives no credit.
   Declare that the workspace is a source snapshot and the parent owns compilation.
6. Stop the process group before capturing the final tree. Preserve the full
   tree and base-to-final changes, including committed changes. Keep intermediate
   mutation events; an audited CLI cannot claim unobserved transient writes were
   impossible. Reconcile actual paths/signals with the frozen plan.
7. Verify and materialize the captured tree independently. Execute blocking
   oracles there. The compile producer must consume that materialization with
   the permitted host Unity route and check source identity before and after.
   Bind the full capture and the declared source projection separately; generated
   caches are excluded only from the compiler copy. Use bounded licensing
   preflight and the existing host lane fallback. Persist toolchain, targets,
   defines, diagnostics and source identity before/after compilation.
8. Score through the existing evaluator with actual execution metadata and
   verified calibration. Unsupported delivery cannot earn numeric credit. Bind
   all evidence to protected provenance after the model process ends. Aggregate
   every scheduled row, including censored and invalid rows, and render reports
   from saved documents. Artifact processing may be repeated without relaunch.

## Identity, failure and recovery

Comparison identity uses existing content and strict-profile keys, not temporary
Git commits or directory names. Reject workspaces beneath another Git or
automatic-instruction root; an ordinary nested folder otherwise inherits
unregistered parent context. This check does not enforce a read namespace.
Engine, launcher, parser, ruleset, oracle, toolchain and
protocol drift invalidate the corresponding comparison. Moving aliases and
unobserved backend revisions cannot be controlled repeats. Preserve requested
and observed model identity separately.

The parent is the sole state writer during one attempt. The journal's exclusive
claim handles separate OS processes competing to launch; no speculative thread
pool or background daemon is added. Timeouts and cancellation terminate and reap
the child group. An interrupted attempt is explicit, retained and never silently
retried. Local rescoring is a different operation from another model attempt.
Classify evaluator failures, provider/surface failures, model execution failures
and unattributed failures distinctly; mixed evidence suspends grading.

Signing material, fixtures, controls, raw evidence and compiler outputs remain
outside the model namespace where the installed boundary can enforce that.
Unenforced boundaries are reported as such and cannot qualify a holdout or
adoption result. The executor must not infer protection from same-user chmod,
a disposable worktree, or the mere presence of a sandbox binary.

## Pilots, validation and rollout

The installed reference inventory is Codex 0.153.0-alpha.5 and Claude Code 2.1.147.
Both reported local subscription login; the actual secondary request returned
OAuth 401. Local status is not proof a token remains usable. Both CLI contracts
lack a verified outbound-request receipt; no transport proxy is planned.
Installed help and live evidence take precedence over historical model names.

The bounded pilot initially targeted three repeats of F1/F2/F4, a targeted
incident task and paired A/B. Actual failures required smaller, separately
identified schedules within twenty total launch claims. Relative-cwd,
parent-context, compiler-cache and preflight defects retain their original rows.
Two paired A/B replicates and the final diagnostic allocation completed. Fixed manifests bind every prior launch and stop/censor
condition. No dollar allowance is inferred, and failed rows are never replaced.

Validation progresses from existing tests and every authored control (including
all F5 attacks), through the first real vertical slice, to fixed cohorts and
artifact-only reproduction. Review again before repeated pilots and against the
final diff/evidence. Include failure controls for malformed/stale/wrong-tree
receipts, interrupted launches, output drift and missing calibrated identity.
Exercise the OS matrix locally where available and record remote CI gaps.

Author F6 with two producer contexts in a distinct critical subsystem and keep
reference context separate. Persist authenticated exposure identities atomically;
replay is rejected and exhaustion quarantines the revision before rotation.
Do not expose it to a surface that cannot enforce blinding. Experiments may be
inconclusive and acceptance never grants application authority. A shared-core
candidate requires the supported-profile and host-consumer regression matrix.

Advisory routing requires actual F0/conformance evidence. A rollback switch
returns to the prior route; audited blocking additionally requires the declared
observation window and false-block budget. This task cannot manufacture two
weeks of telemetry. Local tested commits are authorized; remote publication,
merging and production application remain distinct actions.

## Implemented checkpoint

The tested public executor is pinned at `cbad984`; calibration also binds launcher
code. Replay v2 tolerates a later live-helper edit only through its unchanged
frozen archive; legacy v1 still needs original helper paths. Actual changed F1
source passed six Unity cells through the corrected producer. The earlier capture's
publication remains unverified by the current oracle; the final capture passes the
separate revision-4 check described below. An unchanged-toolchain receipt validated
the full-capture/source-projection binding. The separate final
review also caught CRLF fixture drift and an unsupported preflight flag; real Git
filter and MCP parser controls cover both. Historical results remain traceable.
Routing controls cover three host cases and an omitted override. A/B is
inconclusive; holdout qualification and live conformance remain unavailable.
Current evidence and all 35 criteria live in the host acceptance ledger.

Final evidence review identified a task-oracle false negative for a local capture
alias with paired volatile publication. The host retains the original fixture and
adds revision 4 with eight independent controls, consumed-accessor checks and
explicitly unverified unsupported forms. The final retained tree passes that
corrected task check and its exact compiler receipt. No original cohort row was
replaced; a fresh live revision-4 cohort remains a later authorized measurement.
