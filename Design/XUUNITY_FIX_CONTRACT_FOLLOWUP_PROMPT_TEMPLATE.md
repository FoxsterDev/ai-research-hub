# XUUnity Fix Contract Follow-Up Prompt Template

Use this file when you want to run the next review cycle after several real `xuunity fix` sessions.

Do not use it for:
- one-off brainstorming
- a single fresh bug-fix session with no incident artifact yet
- broad roadmap planning unrelated to the `xuunity fix` contract

Prerequisites:
- you already have 3-5 real incident reports created from:
  - `AIOutput/Reports/System/xuunity_protocol_incident_feedback_template.md`
- you want to compare real incidents against the current synthetic baseline:
  - `AIOutput/Reports/System/xuunity_fix_contract_proving_review_2026-04-24.md`
  - `AIOutput/Reports/System/Smoke/xuunity_fix_contract_replay_2026-04-24.md`

## Mode 1: Follow-Up Review

Use this when you want the smallest next protocol fix after a few real incidents.

Template:

```text
xuunity system progress review these protocol incident reports:
- AIOutput/Reports/System/xuunity_protocol_incident_<date>_<slug1>.md
- AIOutput/Reports/System/xuunity_protocol_incident_<date>_<slug2>.md
- AIOutput/Reports/System/xuunity_protocol_incident_<date>_<slug3>.md

Compare them against:
- AIOutput/Reports/System/xuunity_fix_contract_proving_review_2026-04-24.md
- AIOutput/Reports/System/Smoke/xuunity_fix_contract_replay_2026-04-24.md

Focus only on the xuunity fix contract.
Answer only:
- is Validation result still too compressed
- is patch_shape drifting across similar bug families
- is complexity budget preventing orchestration ballast
- what is the smallest next public-core fix
- what should remain unchanged

Use findings-first ordering.
Save the report under AIOutput/Reports/System/xuunity_fix_contract_followup_review_<date>.md
```

## Mode 2: Scoped Self-Evaluation

Use this when you want a scored protocol audit instead of just the next fix recommendation.

Template:

```text
xuunity system evaluate the protocol structure using:
- AIOutput/Reports/System/xuunity_fix_contract_proving_review_2026-04-24.md
- AIOutput/Reports/System/Smoke/xuunity_fix_contract_replay_2026-04-24.md
- the latest AIOutput/Reports/System/xuunity_protocol_incident_*.md reports

Focus only on the xuunity fix contract, not the whole xuunity system.
Score:
- stability
- quality
- professionalism
- usefulness

Answer with:
- findings ordered by severity
- score table
- what improved since the 2026-04-24 hardening pass
- what still feels weak
- the smallest next corrective action
- what should remain unchanged

Save the report under AIOutput/Reports/System/xuunity_fix_contract_self_evaluation_<date>.md
```

## Mode 3: Single-Incident Triage

Use this when you only have one suspicious session and want to decide whether it is a protocol issue or just a project-code issue.

Template:

```text
Use AIOutput/Reports/System/xuunity_protocol_incident_feedback_template.md and create a protocol incident report for this xuunity fix session.

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

Save the report under AIOutput/Reports/System/xuunity_protocol_incident_<date>_<slug>.md
```

## Recommended Operating Loop

1. After each suspicious real case:
   - run Mode 3
2. After 3-5 real incident reports:
   - run Mode 1
3. Only when structure itself feels noisy or inconsistent:
   - run Mode 2

## Current Watch Points

As of the 2026-04-24 proving review, the main watch points are:
- whether `Validation result` is still too compressed
- whether similar bug families still drift in `patch_shape`
- whether `complexity budget` actually prevents queue/flag/wrapper ballast

Current baseline artifacts:
- `AIOutput/Reports/System/xuunity_fix_contract_proving_review_2026-04-24.md`
- `AIOutput/Reports/System/Smoke/xuunity_fix_contract_replay_2026-04-24.md`
- `AIOutput/Reports/System/Smoke/xuunity_fix_contract_replay_2026-04-24_summary.json`
