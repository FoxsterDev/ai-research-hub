# Model Fitness completion: execution decision record

Status: implementation in progress. Evidence date: 2026-09-08 UTC.
Authority: `XUUNITY_MODEL_FITNESS_COMPLETION_GOAL_PROMPT.md`.
This record distinguishes engineering, diagnostic pilots, qualification, and rollout.

## Baseline and review checkpoint 1

The public baseline is revision `3fb4b640716641119e5cf28d66a0ef6e9522337a`.
Fresh validation ran 178 operation tests (two OS-probe skips), 174 module tests
(no skips), and 67 reference-host tests (three unavailable raw-transcript
replays). These are test counts, not evidence of live model fitness. The host
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

The reviewed code has four material gaps. First, `evaluate_run` defaults
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
but no integrated live path currently justifies operator confidence. These are
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
   and construct the loader bundle. Bundle construction does not prove delivery.
4. Persist a complete schedule before launching: ordered attempt/fixture/profile
   identities, seed allocation, replicate blocks, timeout, aggregate ceiling,
   and stop rule. Create each launch claim exclusively before spawning. A
   second caller or ambiguous interrupted launch cannot spend the same row.
5. Run the CLI with its recorded permissions and bounded lifetime. Capture raw
   stdout, stderr, exit status, terminal events, usage and observed mutations.
   Treat missing/truncated/unknown events as measurement limitations. Probe the
   exact supported execution policy; a probe for another policy gives no credit.
6. Stop the process group before capturing the final tree. Preserve the full
   tree and base-to-final changes, including committed changes. Keep intermediate
   mutation events; an audited CLI cannot claim unobserved transient writes were
   impossible. Reconcile actual paths/signals with the frozen plan.
7. Verify and materialize the captured tree independently. Execute blocking
   oracles there. The compile producer must consume that materialization with
   the permitted host Unity route and check source identity before and after.
   Persist toolchain, target, defines, diagnostics hash and exact tree identity.
8. Score through the existing evaluator with actual execution metadata and
   verified calibration. Unsupported delivery cannot earn numeric credit. Bind
   all evidence to protected provenance after the model process ends. Aggregate
   every scheduled row, including censored and invalid rows, and render reports
   from saved documents. Artifact processing may be repeated without relaunch.

## Identity, failure and recovery

Comparison identity uses existing content and strict-profile keys, not temporary
Git commits or directory names. Engine, parser, ruleset, oracle, toolchain and
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

The installed reference CLI inventory is Codex 0.153.0-alpha.5 and Claude Code
2.1.147. Codex official account login is confirmed. Claude authentication is
not yet established: the first check timed out. Both exposed CLI contracts lack
a verified outbound-request receipt; no new transport mechanism is planned.
Installed help and live evidence take precedence over historical model names.

Persist exact host pilot manifests before any launch. Start with one primary
profile and one canary, then the real host compile path. The bounded primary
plan targets F1/F2/F4 three times each, one F7 attribution case, and two paired
protocol A/B replicates. Add three real-ruleset task cases for gate conformance.
Set explicit launch and wall-time ceilings; never infer a dollar allowance.
Stop on an evaluator defect, exhausted budget, or attempts that cannot answer
a new question. Retain affected schedules; fixes require a new engine identity
and a separately identified schedule, never replacement rows.

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
