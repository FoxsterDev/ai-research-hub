# XUUnity Model Fitness Completion Goal Template

Use this prompt as the goal of a new implementation task in an isolated host-repository worktree with its own AIRoot checkout. It covers review, technical design, implementation, validation, and bounded real pilots.

## Goal

Finish XUUnity Model Fitness as a usable, trustworthy harness for evaluating how a specific model and execution surface apply the XUUnity protocol. Review the existing implementation, choose the smallest defensible completion design, implement it, run real pilots, fix material findings, and leave reproducible commands and evidence.

This is an execution goal. Do not stop after producing a design, a task list, or passing unit tests. Continue through implementation and pilots within the available authorization. Resolve routine design choices independently and keep progressing on unaffected work when a dependency is blocked.

Apply Pareto: prioritize measurement correctness, one working end-to-end path, useful pilots, and maintainability. Complete the engineering capabilities behind W1–W9, while reporting statistical qualification and staged rollout as separate evidence gates. Small pilots do not establish autonomous model fitness or substitute for the prescribed observation window.

## Working context and boundaries

1. Resolve the host repository and AIRoot from the actual checkout and applicable routers. Load the nearest `AGENTS.md` and the full `Modules/XUUnity/tasks/start_session.md`; then load only the relevant planning, implementation, validation, and review owners.
2. The work spans public `AIRoot/Operations/XUUnityModelFitness/`, public `AIRoot/Modules/XUUnity/`, and the host-private Model Fitness operation. Discover the host operation through its router and existing references. An AIRoot-only checkout is insufficient for the host F1 compile integration.
3. Work in isolated task branches/checkouts for both repositories. Verify resolved paths and submodule ownership before editing; a symlink back to the owner's active checkout is not isolation. If the task started in AIRoot alone, establish the companion host worktree through the supported workflow before host mutations. Preserve unrelated changes.
4. Keep provider configuration, host fixtures, raw transcripts, compiler output, and unsanitized pilot evidence host-local. Public code accepts explicit paths/configuration and contains no private project identities or credentials.
5. Run model-generated changes and deliberately broken controls only in disposable fixture workspaces. A benchmark patch must never silently become a production-project change.
6. Use existing supported CLI authentication and the applicable quota/budget policy. Do not request secrets in chat or silently fall back to paid API billing. Local implementation and validation should continue when a live surface is unavailable.

Read these existing inputs before designing replacements:

- `AIRoot/Design/XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md`
- `AIRoot/Design/XUUNITY_MODEL_FITNESS_COMPLETION_PLAN.md`
- `AIRoot/Operations/XUUnityModelFitness/README.md`
- `AIRoot/Modules/XUUnity/knowledge/reduced_stack_gate_contract.md`
- The host operation README, current fixture contracts, and latest relevant health/fitness report.

Treat their implementation status, estimates, model identifiers, and test counts as historical claims to verify. Existing source and fresh evidence determine current state. Retain the measurement and safety invariants; challenge proposed file names, abstractions, and sequencing when a simpler implementation satisfies the same contract.

## First checkpoint: review and a compact technical design

Begin with a bounded inspection and baseline validation. Record a W1–W9 table with `implemented`, `partial`, `missing`, or `blocked`, concrete code/evidence references, and the smallest remaining action. Do not reconstruct unrelated XUUnity history.

Review the paths most likely to produce false confidence:

- Whether legacy launchers actually use the current public evaluation pipeline.
- Whether live evaluation can inherit a permissive default such as `f0_calibration_passed=True` instead of requiring a verified calibration record.
- Requested versus observed identity, runtime-injected context, truncated tool output, unknown events, and ambiguous or transient mutations.
- The actual read/write/network boundary around the model process; verify that probes cover the policy used for execution.
- Tree capture, compile receipts, protected manifests, oracle independence, denominator accounting, and evidence replay.
- What `suite` and `experiment` already enforce, and which guarantees still depend on an unimplemented caller.

Check the real installed surfaces early, before completing the runner design: version, event grammar, authentication, tool permissions, identity observability, request-boundary access, and provider-versus-tool network separation. Determine which can produce diagnostic evidence and which, if any, can satisfy adoption-grade requirements. Do not design a new transport proxy or OS security platform to hide an unsupported capability.

Write one concise technical design, preferably about 1,000–1,500 words plus the acceptance table, covering:

1. The current execution path and verified gaps.
2. The chosen public/host ownership split and concrete functions/modules to reuse or change.
3. The complete flow: calibration → preparation → immutable schedule → execution → final-tree capture → independent validation → scoring → aggregation → report.
4. Identity, process lifetime, timeout/cancellation, interruption recovery, protected evidence, and failure classification.
5. Exact pilot selection, cost controls, validation lanes, review checkpoints, and rollback.

Compare alternatives only for decisions that materially change correctness, feasibility, or maintenance. Then implement the chosen shape; the design is a working decision record, not a separate approval ceremony. For a genuine authorization gap, prepare the concrete action first, explain the exact blocker, and continue independent work.

## Implementation priorities

### 1. Close one complete execution path first: W1 + W2

Compose the existing `baseline`, `attestation`, `isolation`, `broker`, `adapters`, `fixtures`, and `scoring` components. Prefer a thin public executor and a thin host binding. Reuse or converge existing host launcher logic instead of maintaining two independent runners.

Provide discoverable CLI operations for calibration, preparation, execution, scoring, aggregation, and experiments. Follow the existing CLI contract where practical. Keep write destinations explicit and validate inputs before launching a provider or mutating a fixture. Do not add commands whose only purpose is forwarding arguments between wrappers.

The real execution path must:

- Verify fixture implementations and materialize the attested seed into an attempt-owned workspace.
- Require F0 calibration bound to the installed adapter/parser/profile identity; invalidate it when relevant identity changes.
- Derive and check the required stack before mutation, then reconcile it against the captured changes. A loader manifest proves bundle construction; only verified evidence at the real request boundary proves runtime delivery. Do not infer delivery from a claimed file read or fabricated attestation.
- Apply and record the supported isolation and permission policy honestly. Keep secrets, signing keys, answer keys, reference controls, and protected artifacts outside the model namespace.
- Mint `authoritative` only when the existing broker actually controls writes under a verified OS boundary. A disposable Git worktree, same-user file permissions, or passing loose-file gate is insufficient. Preserve evidence of intermediate mutations, including mutate-then-restore.
- Capture events, terminal state, exit status, timeout/cancellation, mutation evidence, and the final tree without relying on the model's self-report.
- Run independent oracles against a verified materialization of that final tree and persist protected provenance before releasing disposable state.
- Return an evaluated result or a diagnosed `null`, with stable cause codes distinguishing evaluator, provider/surface, and model execution failures.
- Handle interruption without losing or silently rerunning an attempt that may already have reached the provider. Prefer an explicit interrupted result to a complex resume engine.

Implement the host F1 compile-receipt producer using the existing permitted Unity validation route. Inspect host/project validation rules before selecting a lane. The actual compiler must consume the same materialized source state the receipt attests; compiling the owner's live editor project is not equivalent. Record toolchain identity, target/defines, diagnostics digest, and exact tree identity. Check source identity around compilation or otherwise prove generated files cannot invalidate the claimed binding.

Prove missing, stale, malformed, failed, and wrong-tree receipts behave correctly. A static oracle pass or an invented successful receipt is never a live compile result. Keep compile success and task correctness independent: a compilable known-bad solution must still fail its task oracle.

### 2. Finish scheduling, comparisons, and reports: W3 + W5

Use the existing suite/statistics contracts. Persist the complete attempt roster, fixture/profile identities, seed allocation, order, timeout, budget, replicate blocks, and stop rule before the first launch. Every scheduled attempt remains accounted for, including unlaunched/censored work under the declared stop rule, crashes, and invalid measurements. Never replace failures with successful retries.

Add the smallest durable execution journal needed to bind actual launches to the plan and reject duplicate execution or conflicting resumption. Distinguish a safe retry of local artifact processing from a new model attempt.

Resolve baseline compatibility from the existing content and profile keys. Changes to protocol, ruleset, scorer, oracle, adapter, or other declared identity constituents must invalidate the appropriate comparison. Moving aliases or unobservable backend identities must not be presented as controlled repeats.

Build reports from persisted results, reusing the existing renderers. Include schedule accounting, per-fixture outcomes, null reasons, enforcement, comparison eligibility, bounds, hard-gate incidents, and observed cost/time where available. Separate installation health from model fitness. A report must be reproducible without another model call; leak-check the sanitized projection.

### 3. Complete the bounded qualification and improvement paths: W4 + W6 + W9

Implement one host-private F6 fixture from a different safety-critical subsystem, with at least two declared producer/execution contexts, an independent oracle, and known-good/known-bad controls. Keep the author/reference context separate from the evaluated model session. Use the existing signed F6 artifact contract and a minimal atomically persisted exposure ledger; prove replay rejection and the exhaustion/rotation procedure.

A surface without the required isolation cannot run a qualified blinded F6. Complete authoring and deterministic integration checks, record the live qualification blocker, and retain the cap; do not downgrade the definition of a holdout.

Connect the existing experiment evaluator to real cohort execution. Demonstrate one small protocol A/B with exactly one declared treatment variable, preregistered metrics, and non-regression budgets. Persist alpha/exposure accounting. `accepted`, `rejected`, and `inconclusive` are all legitimate outcomes; a small pilot is not expected to prove improvement. Keep statistical acceptance, candidate creation, and authorization to apply that candidate distinct.

For knowledge integration, add real host routing probes and a small durable mechanism that marks affected baselines stale and records pending smoke re-evaluation after a protocol change. Exercise one integration-to-fixture or integration-to-re-evaluation path. A callable hook plus a persisted pending-run record is sufficient; a daemon or task-queue service is unnecessary. Inspect whether existing incident fixtures already satisfy the fixture-creation acceptance case before authoring another.

Before recommending application of a shared-core candidate, exercise the required supported-profile and host-consumer regression matrix. Keep unsupported or unavailable entries visible. Do not patch the owner's active protocol as a side effect of benchmark acceptance.

### 4. Make adoption and delivery operational: W7 + W8

Capture derive → load → gate → mutate → reconcile on at least three representative real task cases: a matched risk family, an unrelated low-risk change, and a project override. Include an intentionally omitted obligation that fails for the expected reason. Measure delivered bytes and record false-block evidence.

Connect advisory routing only after the required live calibration and conformance evidence exists. Keep a simple rollback switch and collect real session telemetry. Implement/document the later blocking transition without enabling it prematurely. A single task cannot manufacture two weeks of observation or claim the later rollout stage is complete.

Extend the existing CI workflow so the relevant protocol/fitness tests actually run on macOS, Linux, and Windows, rather than relying on setup smoke coverage. Exercise supported OS enforcement and the honest unsupported/Windows degradation paths. Explicitly account for skipped probes and unavailable remote CI execution. Preserve the byte-clean public tree discipline.

Record immutable tested engine/protocol revisions for pilot evidence. Prepare scoped local commits in each task-owned repository when allowed by the task's delivery authority. Keep remote publication, merging, and production application separate from local validation; do not imply they occurred.

## Pilot plan: small, fixed, and useful

Choose installed profiles from observed capability and existing authorization, not historical model names. Start with one primary surface. Verify the second supported adapter with a live calibration/compatibility canary when available; report its actual support ceiling.

Before any live launch, persist the complete pilot plan with the exact number of attempts, fixtures, versions, budgets, and stop conditions. A reasonable default is a primary smoke suite of **F1 + F2 + F4, three attempts per fixture**, plus one targeted F7 or F8 case, the bounded F6 validation, and one small paired A/B. Reduce redundant additional runs by reusing eligible evidence only where the preregistered identity and exposure contracts explicitly allow it.

Set an aggregate launch/time/token or supported quota ceiling from current authorization and realistic per-run estimates. Do not infer a dollar spending allowance. Do not launch a broad cross-model tournament or default to 30 attempts per fixture during this completion task. Implement full-cohort execution and sample-size validation so later statistical qualification can use it without new engineering.

Run in this order:

1. Existing deterministic suites and every shipped fixture's authored controls, including all F5 attack cases. A scripted CLI is appropriate for process-boundary failures while the owned evaluator remains real.
2. One real canary through the complete executor and one real host F1 compile path. Resolve evaluator defects before spending on repeated runs.
3. The fixed smoke cohort, targeted review/attribution case, eligible holdout work, and the paired A/B declared above.
4. Artifact-only rescoring/report reproduction and interrupted-run recovery checks, followed by the final regression set justified by the changes.

If a pilot reveals an evaluator bug, retain all affected evidence, fix the bug, and start a separately identified schedule against the new engine identity. Do not repair a cohort by swapping its bad rows or reinterpret a provider outage as poor model fitness. Stop further paid/quota-consuming attempts when they cannot answer a new question or the declared budget is exhausted.

## Review and simplification gates

Use three review checkpoints: the current trust boundaries before implementation, the first working vertical slice before repeated pilots, and the final diff plus pilot evidence. A fresh review pass must challenge both existing and new code. Use an independent reviewer when permitted and useful; otherwise perform a separate review pass with explicit findings and evidence.

Fix all findings that can corrupt measurement, leak protected evidence, execute in the wrong checkout, lose attempt accounting, or leave the advertised workflow unusable. Resolve material maintainability findings on the changed path; record justified low-value deferrals. After fixes, rerun affected checks and finish with the relevant combined regression suite. Do not repeatedly rerun already-green suites without a changed condition.

For every new persistent artifact, dependency, abstraction, or control-plane layer, identify the concrete acceptance criterion it serves. Reuse the existing schemas, hashes, capability checks, statistics, renderers, and project validation tools. Add a schema field only when required evidence cannot otherwise be represented, with explicit compatibility handling.

Prefer ordinary functions, standard-library process handling, and atomic local files. Avoid a plugin system, web dashboard, database, distributed scheduler, universal agent framework, broad unrelated refactor, new cryptographic protocol, or Windows sandbox implementation. Do not relax validity, secrecy, denominator, or qualification rules in the name of simplicity. Tests should exercise real owned behavior and the important negative cases, not mirror implementation or inflate a test count.

## Acceptance and closeout

Keep one compact acceptance ledger. For each W1–W9 capability and each relevant original acceptance criterion, record its implementation, validation command/result, evidence artifact, and unresolved dependency. Separate these outcomes:

- **Engineering completion:** the required capabilities are integrated, reviewed, and reproducible from explicit inputs.
- **Pilot completion:** the planned real executions and Unity validation ran and their evidence is valid for the stated diagnostic or qualification claim.
- **Model qualification:** only grades and confidence supported by the immutable cohort, identity, enforcement, and F6 rules.
- **Live rollout:** the actual conformance/advisory/blocking stage and observation window completed.

A diagnosed `null` can prove honest handling of an unsupported surface; it does not by itself prove successful task evaluation. Require real execution evidence and a usable diagnostic report. A numeric result, if produced, must come through the verified pipeline. Never weaken a gate just to produce the first number. Smoke qualification remains provisional, and an unfavorable model result does not imply the harness is broken.

Deliver:

1. The implemented public/host changes and the compact technical design updated to the final shape.
2. A short operator runbook with commands that were actually executed, setup requirements, output locations, expected failures, and recovery/rollback steps.
3. The acceptance ledger, review findings and their dispositions, test results including skips, and sanitized pilot/suite/A/B results with host-local raw-evidence references.
4. Updated READMEs, completion-plan status, and design-registry references. Remove stale readiness percentages, obsolete uncommitted-state claims, and superseded numerical fitness claims from current-status descriptions without destroying historical evidence.
5. A concise final report: what now works, what the pilots demonstrated, what was simplified, exact remaining statistical/rollout/environment gates, and the next executable command.

Do not declare the original design fully complete while a required engineering capability or live validation is still missing. Do not leave implemented functionality untested just to finish a document. Complete everything that can be completed within the task; identify external blockers with attempted routes and exact missing evidence, and keep legitimate later statistical and observation-window gates visible.
