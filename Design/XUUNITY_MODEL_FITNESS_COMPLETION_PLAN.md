# XUUnity Model Fitness — Completion Plan (P3 → Finish)

Status: ready-to-execute engineering plan.
Parent design: `XUUNITY_MODEL_FITNESS_AND_REDUCED_STACK_GATE_DESIGN.md`.
Scope: everything required to take the system from "measurement machine
proven on synthetic corpora" (P0–P3 complete) to "live adoption grades for
real model profiles and a gated live surface" (design P4 plus the
integration tails the design leaves to the host).

This document is public-safe: host-confidential material (task payloads,
raw transcripts, host paths, product identifiers) is referenced only by
role ("the host", "the host F1 fixture") and never by content.

---

## 1. Current State (inventory, 2026-07-30)

### 1.1 Done and green

| Layer | Location | Content | Tests |
| --- | --- | --- | --- |
| Public module | `AIRoot/Modules/XUUnity` | `xuunity_canonical` (JCS/I-JSON, domain digests), `contract_validator`, `observation_contract` (state taxonomy, groups, delivery), `shell_observer` (bounded fail-closed grammar), `reduced_stack_resolver` / `reduced_stack_loader` / `reduced_stack_gate` (derive/check/reconcile), routing-gate composition, data-driven ruleset + 11 module schemas, `ruleset_check` (ruleset self-hash gate + hand-authored routing probes replayed through the real resolver: minimality tripwire, override-owner and family-routing assertions) | 145 |
| Public operation | `AIRoot/Operations/XUUnityModelFitness` | `model_fitness` package: `baseline` (content-addressed seeds, git-sourced identity, strict comparison keys), `attestation` (session MAC, request-boundary attestation, protected run manifest), `broker` (exclusive authoritative writes, one-use capabilities), `isolation` (seatbelt/bwrap/Null backends, enforcement probes, replay corpus, hermetic materialization), `adapters` (claude/codex normalization, mutation boundary, artifact resolution), `scoring` (5 dimensions, hard-gate precedence, bands), `stats` (exact Clopper-Pearson, order-statistic median bound), `suite` (immutable denominator, replicate bounds, grade caps), `experiment` (preregistered decision, alpha/F6 ledgers), `fixtures` (fixture kit, hermetic oracle harness, `evaluate_run` pipeline); 11 operation schemas; fixture corpus F2/F3/F4/F5 with red+green controls and the 10-attack F5 corpus | 145 |
| Host operation | host-private operation dir | scorer v4 as thin compat layer over public adapters; legacy fixture v2 (diagnostic only); F1 v3 fixture on the public fixture schema: independent static/task oracle (known-bad red, known-good green, explicit producer denominator and untested contexts), receipt-bound compile oracle (`xuunity.f1-compile-receipt.v1`, tree-identity-bound, fail closed), severity-weighted safety validators; F0 regression slices | 67 |

### 1.2 Deliberate open state (all by design, not debt)

- **No numeric fitness score exists anywhere.** Every scored path demands:
  valid axes + F0 calibration for the exact adapter profile + identity
  match + runner-owned oracle. No attempt has ever been executed under the
  P2 runner, so all real evidence is `score_total: null`.
- **F1 compile lane** consumes a receipt that nothing produces yet.
- **F6 blinded holdout** exists as contract + suite-level cap only; no
  rotating payload. Every suite grade is therefore capped at
  `fit_with_supervision`.
- **Live surface untouched**: the session entrypoint has no pointer to the
  reduced-stack gate; live sessions still run the full-stack protocol.
- **Nothing is committed** (public submodule and host repo both carry the
  whole P0–P3 tree as working-copy state).

---

## 2. Work Packages

Dependency order:

```text
W1 compile receipt ─┐
                    ├─> W2 attempt executor ─> W3 P4 repeats/adoption ─> W5 health loop
W8 release eng. ────┘                          │
                                               ├─> W4 F6 holdout (unlocks uncapped fit)
                                               └─> W6 self-improvement loop ─> W9 knowledge loop
W2 conformance evidence ─> W7 live-surface gate adoption
W9 fixture-candidate pipeline (triage side) has no upstream dependency
```

W8 (first commits) should land before W2 produces run evidence, so that
every run result can reference an immutable protocol/engine revision.

---

### W1 — Host compile-receipt producer (close the F1 compile lane)

**Objective.** Make `f1_compile` a real blocking oracle: a genuine host
toolchain compile of the hermetically materialized final tree, bound to
that tree's identity, fail closed on any mismatch.

**Deliverables (host-local).**
1. `oracles/produce_compile_receipt.py` — runner-side producer:
   - input: materialized tree path + output receipt path;
   - computes `baseline.content_identity(tree)` first, then triggers the
     host editor/toolchain batch compile against that exact tree (host
     editor bridge in batch mode; no GUI dependency);
   - captures compiler identity/version, target, defines, error/warning
     diagnostics digest;
   - writes `{"schema_version": "xuunity.f1-compile-receipt.v1",
     "tree_identity": <sha256>, "status": "passed"|"failed",
     "reason_codes": [...], "toolchain": {...}, "diagnostics_sha256": ...}`.
2. Receipt handoff: the runner exports the receipt path via the oracle's
   declared environment variable; the oracle (already implemented)
   re-verifies tree identity and fails closed otherwise.
3. Conformance tests (host): receipt-for-wrong-tree rejected; stale
   receipt rejected; passed/failed statuses propagate to
   `semantic_outcome`; a live smoke compile on the known-good reference
   tree passes and on the known-bad seed still passes compile while the
   static task oracle stays red (compile is necessary, not sufficient).

**Exit criteria.** F1 v3 scores a synthetic end-to-end run with BOTH
blocking oracles live; missing/mismatched receipt yields
`score_total: null` with `compile_receipt_*` reason codes.

**Estimate.** 0.5–1 day (the oracle side already exists).

---

### W2 — Attempt executor: one real run end-to-end (finishes design P2 in practice)

**Objective.** A single command that takes (fixture, adapter profile,
seed) and produces a schema-valid, protected, scored-or-null run result
from a real model CLI execution.

**Deliverables.**
1. Public: `model_fitness/executor.py` — orchestration that composes only
   existing components (no new trust logic):
   - `materialize_seed` into a per-attempt worktree; record seed identity;
   - build session attestation (parent-owned key, never in the model
     namespace);
   - resolve isolation backend; `probe_enforcement`; record
     `enforcement_mode` honestly (`audited` everywhere the probe cannot
     prove a boundary — including Windows);
   - launch the surface CLI (claude stream-json / codex experimental
     JSON) with scrubbed environment and the adapter profile's declared
     contract; capture raw transcript, exit metadata, final tree, diff;
   - request-boundary attestation where the surface supports it;
     otherwise runtime deliveries remain `runtime_delivered_unverified`;
   - `fixtures.evaluate_run(...)` over the captured evidence with the
     hermetic oracle pass (W1 receipt producer plugged in for compile
     oracles);
   - `attestation.build_protected_run_manifest` anchored outside the
     model-writable worktree; persist run dir (host-local raw evidence,
     public-safe projection separated).
2. Public: `adapter-profile` documents for the two supported surfaces
   with parser capability hash = hash of the shipped adapter code path.
3. **F0 live calibration gate**: before any scored batch, run the F0
   corpus (synthetic slices + one sanitized live canary per adapter)
   against the *installed* CLI version; store
   `f0_calibration = {profile_hash, passed, timestamp}`; `evaluate_run`
   consumers pass `f0_calibration_passed` from this record only.
4. Host: thin CLI `run_attempt.py` binding executor to host fixture dirs
   and the host receipt producer.
5. Tests: executor unit tests with a scripted fake CLI (deterministic
   transcript emitter) proving: timeout → `execution_invalid`; protected
   read attempt blocked by namespace (macOS/Linux) or honestly
   `audited`+unenforced (Windows); post-run tree identity recorded; run
   manifest validates; identical seeds → identical
   `task_measurement_key`.

**Exit criteria.** One real attempt per surface (claude, codex) executed
against host F1 v3: claude path produces a numeric score or a
diagnosed-null with true reason codes; codex path reports
`observer_unsupported` / `matched_content_noncontrolled` exactly as the
design predicts. Design acceptance items 10–15, 19–22 demonstrated on
real evidence.

**Estimate.** 2–3 days.

---

### W3 — Design P4 core: preregistered repeats, adoption matrix, baseline resolution

**Objective.** Turn single diagnostic runs into adoption-grade suite
evidence with immutable preregistration.

**Deliverables.**
1. Public: `model_fitness/schedule.py`:
   - `build_attempt_plan(suite, seed_policy, randomization_policy)` —
     materializes the full attempt schedule (fixture × replicate × order,
     timeouts, budgets, stop rule) BEFORE the first attempt; plan is
     content-hashed and stored in the suite document's `attempt_plan`;
   - execution loop over the plan via W2 executor; an invalid attempt is
     recorded and stays in the denominator — never replaced;
   - censoring rules (evaluator-caused vs profile-caused) with cause
     codes feeding `suite.aggregate_suite` unchanged.
2. Public: `model_fitness/baseline_resolution.py`:
   - classify a (candidate run, stored baseline) pair into
     `exact_repeat` / `matched_content_noncontrolled` /
     `historical_stale` from strict/task keys and protocol hashes;
   - stale detection: any constituent hash drift (ruleset, protocol,
     scorer, oracle) → `historical_stale`, never silently comparable.
3. Pilot suite documents (host-authored, schema-valid):
   - smoke suite (3 attempts/fixture) — expected outcome: provisional,
     `statistical_confidence: insufficient`, cap `fit_with_supervision`;
   - full suite (preregistered n per fixture sized by
     `stats.median_lower_bound` attainability at the declared confidence;
     n=30/fixture reference point), F1 required, F2–F5 included, F5
     safety-critical stratum.
4. Tests: schedule immutability (mutating the plan after first attempt is
   an error), denominator invariance, adaptive-replacement rejection,
   baseline staleness on each hash axis, smoke-cannot-produce-fit
   (already covered at suite level — re-asserted end-to-end).

**Exit criteria.** Design acceptance 25–27 hold on real executor output;
one full pilot suite aggregates to a grade (capped by missing F6) with
every attempt accounted for in the immutable denominator.

**Estimate.** 2–3 days + model-run wall time and cost.

---

### W4 — F6 blinded cross-domain holdout

**Objective.** Remove the structural `fit_with_supervision` cap with a
real blinded holdout.

**Deliverables.**
1. Host: one F6 fixture on the public fixture schema:
   - different critical subsystem from F1, ≥2 producers/execution
     contexts, known-bad seed + known-good reference;
   - task payload and oracle stored outside the model namespace
     (protected paths + isolation read-namespace deny already enforce
     this); public fixture document carries only refs + hashes.
2. Rotation and exposure procedure (public doc + host state):
   - every F6 evaluation consumes one exposure in the experiment/F6
     ledger (already implemented in `experiment.py`);
   - exhaustion → quarantine the payload, rotate to a freshly authored
     one, reset the ledger with a new `holdout_ref`;
   - authoring checklist forbids reusing F1–F5 subject matter.
3. Tests: host oracle red/green controls; public-side: suite with
   `f6_included=True` un-caps; exposure overrun still forces
   `inconclusive`.

**Exit criteria.** A full suite including F6 can grade `fit` when the
numbers support it; without F6 the cap provably remains.

**Estimate.** 1–2 days (dominated by authoring a genuinely independent
fixture).

---

### W5 — Health-loop and reporting integration

**Objective.** Fitness results become a standing, sanitized report
surface without contaminating installation health.

**Deliverables.**
1. Public: `render_suite_report` / `render_run_report` already exist —
   add `model_fitness/report.py` aggregation: per-profile fitness page
   (grade, bounds, hard-gate incidents, invalid rate, comparison status,
   reason-code digest) rendered from suite-result documents only (no raw
   evidence).
2. Host: wire the fitness page into the existing health reporting as a
   SEPARATE section; assert (test) that no combined installation+fitness
   scalar exists anywhere in the output.
3. Sanitization test: rendered public report contains no host
   identifiers, no task text, no raw transcript fragments (leak-check
   automated as a unit test over rendered output).

**Exit criteria.** Design acceptance "health never combines installation
and fitness scores" holds by construction and by test.

**Estimate.** 0.5–1 day.

---

### W6 — Controlled self-improvement loop

**Objective.** Close the last P4 bullet: one-candidate protocol A/B with
apply authority separated from acceptance.

**Deliverables.**
1. Runner glue: given an experiment manifest, build control and treatment
   cohorts through W3 scheduling where ONLY the protocol content hash
   differs (`treatment_variable: protocol_content_hash`); everything else
   pinned by strict keys.
2. Candidate lifecycle (host procedure + public state machine doc):
   `accepted` experiment → `candidate_patch` recorded →
   `apply_authorization.state` transitions `not_requested →
   authorized (human) → applied`; the live public core is byte-identical
   until `applied`.
3. Protected regression matrices: a shared-core candidate must pass the
   multi-profile (every supported adapter) and multi-project (every host
   consumer) suite matrix before authorization is even requestable.
4. Tests: cohort builder rejects any second treatment variable;
   family-alpha ledger persists across experiments in one family;
   `applied` without `authorized` is unrepresentable.

**Exit criteria.** Design acceptance items on experiments (single
treatment variable, alpha consumption, candidate-never-auto-applied,
live-core-unchanged) demonstrated on one real (or replayed) A/B.

**Estimate.** 1–2 days.

---

### W7 — Live-surface gate adoption (staged)

**Objective.** Route real work sessions through the reduced-stack gate —
only after the measurement system proves the gate works on the real
surface.

**Stage 0 — conformance evidence (blocker for everything below).**
- Run derive → load → gate → mutate → reconcile manually on ≥3 real
  tasks (one matched high-risk, one unrelated low-risk, one override
  case) on the live host surface with the real ruleset;
- F0 calibration green for the exact installed CLI version;
- capture the runs under W2 so the gate decisions are observed
  mechanically, not self-reported;
- acceptance: unrelated task derives minimal stack (F4 behavior on the
  real ruleset); matched task derives family + project override (F2
  behavior); a deliberately skipped obligation fails the gate.

**Stage 1 — advisory.**
- Add the advisory pointer in the module session entrypoint
  (`tasks/start_session.md`) per the routing note in
  `reduced_stack_gate_contract.md`;
- sessions derive a plan and record gate results; nothing blocks;
- collect ≥2 weeks / ≥N sessions of gate telemetry; measure false-block
  rate against the F4 budget.

**Stage 2 — audited-blocking.**
- Gate `fail` before first mutation becomes a hard stop in the session
  discipline (still `audited` enforcement — no OS boundary claimed);
- reopen signals (`before_closeout`, `on_reconcile`) active;
- rollback switch: removing the pointer restores Stage 0 behavior.

**Exit criteria.** Design end-to-end items 6–9 observed on live
sessions; false-block rate within the declared budget; user-visible
context cost reduced on unrelated tasks (measured delivered bytes).

**Estimate.** 0.5 day engineering + calendar time for Stage 1 telemetry.

---

### W8 — Release engineering

**Objective.** Immutable, reviewable history; CI that keeps the three
suites green cross-platform.

**Deliverables.**
1. Commit series (executed only on explicit owner request):
   - AIRoot submodule: logically staged commits (P0 observer, P1
     reduced-stack, P2 engine, P3 corpus + kit), each leak-checked
     (`grep` gate for host identifiers, absolute paths, secrets) before
     commit; no AI co-author trailer;
   - host repo: scorer compat layer + F1 v3 + receipts + submodule
     pointer bump in one commit;
   - tag the AIRoot state consumed by the first scored run so
     `strict_profile_key` constituents are pinned to a revision.
2. CI matrix (public repo): macOS + Linux + Windows; module + operation
   suites; Windows job additionally asserts the audited degradation path
   (`NullBackend`, unenforced namespace reported, broker refuses
   authoritative); Linux job runs the bwrap argv contract and — where the
   runner image allows — live enforcement probes.
3. `PYTHONDONTWRITEBYTECODE` discipline / pycache exclusion enforced by
   CI check (public tree must stay byte-clean).

**Exit criteria.** Every future run result can name the exact engine
revision; suites green on all three OS targets.

**Estimate.** 0.5–1 day.

---

### W9 — Knowledge-loop integration (self-learning from completed work)

**Objective.** The module's knowledge pipeline (extraction → triage →
integration) feeds the measurement system instead of running beside it:
new skills, roles, and knowledge wire into machine routing under a
mechanical gate, and completed-session incidents become fixtures.

**Already landed with this plan revision.**
- Integration protocol (`utilities/knowledge_integration.md` steps
  7c–7e): machine-routing wiring rules (covered glob → no edit; new
  override → automatic via templates; new family/role → new rule with
  selectors), the mandatory `ruleset_check` gate in the same approved
  change, and the protocol-change staleness rule.
- Triage protocol (`utilities/knowledge_extraction_triage.md` steps 2a /
  3 / 4 / 4b): retrospective identifies replayable incidents; a new
  candidate output type "fitness fixture candidate" with the fixture-kit
  contract (red/green controls, independent oracle, hand-authored
  expected stack) and a public-vs-host placement rule.
- `scripts/ruleset_check.py` + `knowledge/reduced_stack_probes.json`:
  document conformance (schema, self-hash, cycles, unknown selectors,
  `--fix-hash`) plus hand-authored routing probes replayed through the
  real resolver — an unrelated-task minimality tripwire with a byte
  budget, family-routing positives, override-owner assertions.

**Remaining deliverables.**
1. Host probe corpus: a host-local probes file with project-override
   (F2-style) probes against real project `SkillOverrides` and at least
   one probe per keyword family; run it in the host validation loop next
   to the public corpus.
2. Staleness follow-through: after an approved integration batch changes
   the protocol or ruleset hash, affected suite baselines become
   `historical_stale` automatically (comparison keys already guarantee
   this); add the operational step — enqueue a smoke re-run for affected
   profiles so the standing fitness picture never silently refers to the
   previous protocol.
3. Measured knowledge value: a substantial routing or guidance change
   goes through the W6 preregistered A/B (control = previous protocol
   hash, treatment = new) before its value is claimed; the experiment
   record is attached to the integration record; a human applies.
4. Fixture-candidate cadence: every triage retrospective that yields a
   replayable incident produces a fixture skeleton through the public
   fixture kit; accepted fixtures grow the corpus, and cross-domain ones
   feed the F6 rotation pool (W4).

**Exit criteria.** One real integration batch has passed the ruleset
probes, staled its baselines, and (for a routing change) carried A/B
evidence; one triage retrospective has minted an accepted fixture.

**Estimate.** 1–2 days engineering + per-incident fixture authoring.

---

## 3. End-to-End Acceptance Criteria Mapping

Design §"End-To-End Acceptance Criteria" (27 items) → status/owner:

| Items | Status | Where |
| --- | --- | --- |
| 1–5 (observer honesty, null-not-zero, prose earns nothing) | proven on synthetic corpora (P0/P3 tests) | done; re-confirmed on real runs in W2 |
| 6–9 (derivation minimality, override, routing composition, reopen) | proven on synthetic rulesets (P1/P3) | live-surface proof in W7 Stage 0 |
| 10–12 (attestation binding, loose-file audited, authoritative broker) | implemented + unit-proven (P2) | real-run demonstration in W2 |
| 13–15 (request-boundary attestation, hidden fixtures unreadable, default-deny network/replay) | implemented + probe-proven on macOS (P2) | live in W2; Linux probes in W8 CI |
| 16–18 (secret preflight, contract conformance, parallel identity) | done (P1/P2 tests) | — |
| 19–22 (protected mutation invalidates, hermetic oracles, exact comparison keys, F0 per adapter) | implemented (P2/P3) | F0 *live* calibration lands in W2 |
| 23–24 (F2–F5 positive+negative controls, known-bad red / known-good green) | **done (P3)** | — |
| 25–27 (no single-run grades, immutable schedule, bounded fit, smoke≠fit) | suite logic done (P2.4) | real preregistered cohort in W3 |

---

## 4. Risks and Mitigations

1. **Surface drift** (CLI update changes event grammar) — F0 calibration
   is re-run per installed version; a failed F0 blocks scoring instead of
   silently corrupting it. Keep F0 slices under version control per
   adapter version.
2. **Compile-lane flakiness** (editor/toolchain nondeterminism) — receipt
   binds to tree identity and toolchain version; a flaky compile produces
   a failed/absent receipt → null score, cause-coded `measurement_system`,
   suspending grading rather than penalizing the profile.
3. **Cost of full cohorts** — smoke suites first (cheap, capped grade);
   full n only for profiles that survive smoke; budget recorded in the
   preregistered plan.
4. **F6 authoring leakage** (holdout too similar to tuning fixtures) —
   authoring checklist + reviewer sign-off recorded in the fixture doc;
   exposure ledger caps peeking.
5. **Live-gate friction** (Stage 1 shows high false-block) — F4 budget is
   the tripwire; ruleset fixes go through the W6 experiment path, not ad
   hoc edits.
6. **Windows** — remains honestly `audited`; adoption grades for
   authoritative-mode claims are macOS/Linux only until a Windows
   boundary backend exists (out of scope here; declared, not assumed).

---

## 5. Definition of Done

The task is finished when all of the following are true:

1. A real model attempt on the host F1 fixture produces either a numeric
   score or a diagnosed null, with both blocking oracles (static + tree-
   bound compile receipt) live. (W1+W2)
2. F0 live calibration for each supported adapter version gates all
   scoring. (W2)
3. One preregistered full suite per candidate profile aggregates under
   the immutable schedule; smoke cohorts provably cannot grade `fit`.
   (W3)
4. A blinded F6 holdout exists, is consumed through the exposure ledger,
   and un-caps `fit` when included. (W4)
5. Fitness reporting is live and never blended with installation health.
   (W5)
6. One controlled protocol A/B has run end-to-end with acceptance,
   candidate patch, and human-held apply authority demonstrated. (W6)
7. The live session entrypoint routes through the reduced-stack gate at
   Stage 1 (advisory) or beyond, backed by Stage 0 conformance evidence.
   (W7)
8. All of P0–P3 plus the above is committed (public submodule + host
   pointer), leak-checked, tagged, and CI-green on macOS/Linux/Windows.
   (W8)
9. Knowledge integration runs through the mechanical ruleset gate with
   authored probes, stales fitness baselines on protocol change, and
   mints fixtures from replayable session incidents. (W9)

Total engineering estimate: **9–15 days** plus model-run cost and the
Stage 1 telemetry window.
