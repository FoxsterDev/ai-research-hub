# XUUnity Fix Contract Follow-Up Prompt Template

Use this public-safe template to run an evidence-based review cycle after real
`xuunity fix` sessions expose possible protocol gaps.

The goal is to improve the reusable public `xuunity fix` contract only when
real incidents show a repeated contract problem. Do not change public protocol
rules from one ambiguous session unless the triage clearly proves a protocol
failure.

## Public / Host-Local Boundary

This template is public. The evidence it consumes is host-local.

Keep concrete incident reports, replay results, dated baselines, project names,
customer details, private paths, logs, and generated review outputs outside
public `AIRoot`. A host repo can keep them under its own output root, commonly:

- `<host-output-root>/Reports/System/`
- `<host-output-root>/Reports/System/Smoke/`

When using this template, replace every placeholder with a host-local path:

- `<incident-feedback-template-path>`
- `<incident-report-path-N>`
- `<current-fix-contract-baseline-review>`
- `<current-fix-contract-replay-or-smoke-evidence>`
- `<follow-up-review-output-path>`
- `<self-evaluation-output-path>`
- `<single-incident-output-path>`

## When To Use This

Use it when:
- you have suspicious real `xuunity fix` sessions
- you want to decide whether the public contract needs a small correction
- you have enough evidence to compare real incidents against current expected behavior

Do not use it for:
- one-off brainstorming
- broad roadmap planning unrelated to the `xuunity fix` contract
- private project-code debugging where the public protocol behaved correctly
- publishing host-local evidence into public `AIRoot`

## Prerequisites

For a full follow-up review, collect:
- 3-5 real protocol incident reports created from `<incident-feedback-template-path>`
- the current approved fix-contract baseline review
- the current replay, smoke, or other validation evidence for that baseline

For a single-incident triage, one suspicious session is enough.

## Mode 1: Follow-Up Review

Use this when you want the smallest next protocol fix after several real
incidents.

Template:

```text
xuunity system progress review these protocol incident reports:
- <incident-report-path-1>
- <incident-report-path-2>
- <incident-report-path-3>

Compare them against:
- <current-fix-contract-baseline-review>
- <current-fix-contract-replay-or-smoke-evidence>

Focus only on the xuunity fix contract.
Answer only:
- is Validation result still too compressed
- is patch_shape drifting across similar bug families
- is complexity budget preventing orchestration ballast
- what is the smallest next public-core fix
- what should remain unchanged

Use findings-first ordering.
Save the report under <follow-up-review-output-path>.
Do not copy host-local evidence or private paths into public AIRoot.
```

## Mode 2: Scoped Self-Evaluation

Use this when you want a scored protocol audit instead of only the next fix
recommendation.

Template:

```text
xuunity system evaluate the protocol structure using:
- <current-fix-contract-baseline-review>
- <current-fix-contract-replay-or-smoke-evidence>
- <incident-report-paths>

Focus only on the xuunity fix contract, not the whole xuunity system.
Score:
- stability
- quality
- professionalism
- usefulness

Answer with:
- findings ordered by severity
- score table
- what improved since the current hardening baseline
- what still feels weak
- the smallest next corrective action
- what should remain unchanged

Save the report under <self-evaluation-output-path>.
Do not copy host-local evidence or private paths into public AIRoot.
```

## Mode 3: Single-Incident Triage

Use this when you only have one suspicious session and need to decide whether it
is a protocol issue or a project-code issue.

Template:

```text
Use <incident-feedback-template-path> and create a
protocol incident report for this xuunity fix session.

Focus on:
- routing miss
- patch_shape quality
- complexity budget behavior
- validation obligation quality
- closure reporting quality

Say explicitly:
- whether this is really a protocol incident
- whether it should change public AIRoot
- whether it should wait for more evidence

Save the report under <single-incident-output-path>.
Do not copy host-local evidence or private paths into public AIRoot.
```

## Recommended Operating Loop

1. After each suspicious real case:
   - run Mode 3
2. After 3-5 real incident reports:
   - run Mode 1
3. Only when the contract structure itself feels noisy or inconsistent:
   - run Mode 2

## Current Watch Points

The standing watch points are:
- whether `Validation result` is still too compressed
- whether similar bug families still drift in `patch_shape`
- whether `complexity budget` actually prevents queue, flag, or wrapper ballast
- whether closure reporting gives enough validation evidence for the risk level

Update these watch points only when public `xuunity fix` contract changes make a
watch point obsolete or add a new repeated risk.
