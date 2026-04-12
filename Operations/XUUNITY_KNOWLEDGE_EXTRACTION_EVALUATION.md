# XUUnity Knowledge Extraction Evaluation

## Purpose
This framework evaluates whether `xuunity extract ...` reliably captures important knowledge, routes it to the correct destination, and avoids unsafe promotions.

Use it for:
- prompt changes to extraction or intake workflows
- regression checks after prompt cleanup
- evaluating new destination-routing logic
- verifying that critical insights are not lost during compression

This evaluation should be treated as an input into:
- `xuunity system health review`
- `xuunity system progress review`

## What Good Looks Like
A strong extraction result:
- captures all critical rules and caveats
- avoids promoting project-local details into shared prompts
- routes content to the right destination
- preserves reviewer warnings and testing implications
- avoids duplicating existing skills or review artifacts

## Evaluation Layers

### 1. Critical Gate
These are hard-fail conditions.

Fail the run if any case has:
- `critical_omission_count > 0`
- `wrong_destination_for_critical_items > 0`
- `forbidden_shared_leaks > 0`
- `conflict_flattening_count > 0`

### 2. Core Metrics
Score each case from `0` to `5`:
- `critical_recall`
  - were all critical rules, caveats, and failure modes captured
- `precision`
  - was useful content extracted without too much noise
- `routing_accuracy`
  - was each item routed to the correct destination
- `semantic_preservation`
  - was the meaning preserved without unsafe simplification
- `duplication_safety`
  - did the system avoid proposing duplicate or weaker copies
- `boundary_safety`
  - did the system keep project-local content out of shared prompts
- `actionability`
  - did the review package make the next approval step clear

### Metric Anchors
Use these anchors to reduce evaluator drift.

`critical_recall`
- `5`
  - all critical rules and caveats captured
- `3`
  - one important but non-blocking nuance weakened or partially missed
- `1`
  - one or more critical rules missed

`precision`
- `5`
  - little noise, almost every extracted item is useful
- `3`
  - some generic or weak items mixed in
- `1`
  - noisy output obscures the useful content

`routing_accuracy`
- `5`
  - critical items routed correctly and non-critical routing is mostly clean
- `3`
  - one or two non-critical routing mistakes
- `1`
  - critical routing mistakes or broad destination confusion

`semantic_preservation`
- `5`
  - meaning preserved with warnings, caveats, and constraints intact
- `3`
  - some simplification but still mostly safe
- `1`
  - flattening changed the engineering meaning materially

`duplication_safety`
- `5`
  - correctly prefers merge or no action when overlap already exists
- `3`
  - duplication risk is visible but not severe
- `1`
  - confidently proposes duplicate or weaker copies

`boundary_safety`
- `5`
  - project-local and vendor-local content kept out of shared destinations
- `3`
  - one ambiguous boundary decision but no unsafe promotion
- `1`
  - unsafe shared leak occurred

`actionability`
- `5`
  - approval package is clear, destination-specific, and easy to apply
- `3`
  - mostly usable but some destination ambiguity remains
- `1`
  - reviewer cannot approve safely without redoing the triage mentally

### 3. Weighted Score
Use this weighted score for non-failing cases:

`total_score = 0.30*critical_recall + 0.15*precision + 0.20*routing_accuracy + 0.15*semantic_preservation + 0.10*duplication_safety + 0.10*boundary_safety`

Interpretation:
- `4.5-5.0`
  - strong, production-ready extraction quality
- `4.0-4.49`
  - good, with minor cleanup opportunities
- `3.5-3.99`
  - usable but fragile
- `<3.5`
  - not reliable enough

### 4. Portfolio Summary
For a full regression pass, track:
- pass rate
- fail count
- average weighted score
- critical omission count
- routing error count
- unsafe shared leak count
- duplicate proposal count

## Expected Destinations
The framework assumes these main destinations:
- `review_artifact`
- `skill`
- `shared_knowledge`
- `project_only`
- `no_action`

## Golden Dataset Structure
Each test case should define:
- source artifact
- expected durable rules
- expected critical rules
- expected destination map
- forbidden promotions
- allowed ambiguity notes

Use the case template in:
- `AIRoot/Templates/XUUNITY_KNOWLEDGE_EXTRACTION_CASE_TEMPLATE.yaml`

Seed cases live in:
- `AIRoot/Operations/XUUNITY_KNOWLEDGE_EXTRACTION_GOLDEN_CASES.yaml`
- `AIRoot/Operations/XUUNITY_KNOWLEDGE_EXTRACTION_GOLDEN_CASES.json`

## Recommended Case Types
The golden set should include at least:
- `skill_heavy`
- `review_heavy`
- `mixed_destination`
- `project_leak_risk`
- `duplicate_existing_knowledge`
- `conflicting_guidance`
- `high_noise_low_value`
- `single_occurrence_critical_caveat`

Recommended v1 target:
- at least `12` cases
- at least `2` mixed-destination cases
- at least `2` boundary-safety cases
- at least `2` duplicate-or-merge cases
- at least `2` conflict-preservation cases
- at least `2` low-value rejection cases

## Manual Evaluation Workflow
1. Pick or add a golden case.
2. Run the current extraction workflow against the source.
3. Compare the output against expected critical rules first.
4. Check forbidden promotions and routing errors.
5. Score the remaining dimensions.
6. Record the result in the report template.
7. If a hard fail occurred, treat the prompt change as regression until fixed.

## Harness Workflow
Use the local harness when you want a repeatable run bundle and a generated report.

Initialize a run:

```bash
python3 AIRoot/Operations/knowledge_extraction_eval.py init \
  --run-name knowledge_extraction_eval_2026-04-04 \
  --evaluator your_name
```

This creates:
- a run JSON bundle in `AIOutput/Reports/System/`
- a prompt pack folder with one prompt file per case

For smoke or demo runs, set:

```bash
python3 AIRoot/Operations/knowledge_extraction_eval.py init \
  --run-name smoke_knowledge_extraction_eval_2026-04-04 \
  --evaluator your_name \
  --run-type smoke \
  --evidence-level synthetic \
  --output-dir AIOutput/Reports/System/Smoke
```

After filling the evaluation fields in the run JSON, generate the report:

```bash
python3 AIRoot/Operations/knowledge_extraction_eval.py report \
  --run-json AIOutput/Reports/System/knowledge_extraction_eval_2026-04-04.json \
  --write-back
```

The harness:
- validates gate and score fields
- computes weighted totals
- classifies cases as `pass`, `warning`, or `fail`
- writes a Markdown report next to the run JSON
- writes a machine-readable health summary JSON next to the run JSON
- updates `AIOutput/Reports/System/knowledge_extraction_eval_latest_summary.json` only for authoritative human-scored runs

Before converting a run to authoritative human-scored evidence, use:
- `AIRoot/Operations/XUUNITY_EXTRACTION_AUTHORITATIVE_APPROVAL_CHECKLIST.md`

## Reviewer Checklist
- Did the result capture every critical rule from the source?
- Did it preserve caveats that appear only once?
- Did it keep reviewer guidance separate from reusable skill rules?
- Did it avoid flattening meaningful conflicts into fake consensus?
- Did it keep project-specific details out of shared destinations?
- Did it suggest merge instead of duplicate creation when overlap exists?
- Did the approval package make destination-specific apply decisions clear?

## Release Rule
Do not treat extraction changes as safe merely because the average score improved.
Any critical omission or unsafe routing is a blocking failure even if the mean score looks good.

## Reporting
Use:
- `AIRoot/Templates/XUUNITY_KNOWLEDGE_EXTRACTION_REPORT_TEMPLATE.md`

Store completed run reports in:
- `AIOutput/Reports/System/`

Recommended filename shape:
- `knowledge_extraction_eval_YYYY-MM-DD.md`

## Baseline Policy
Maintain one named baseline report for the current extraction workflow.

Recommended file:
- `AIOutput/Reports/System/knowledge_extraction_eval_baseline_v1.md`

When prompts change:
1. rerun the golden pack
2. compare against the baseline
3. update the baseline only after human review confirms the new behavior is better, not merely different
4. use the authoritative approval checklist before changing the latest summary into approved health evidence

## Health Review Integration
When running `xuunity system health review`, check:
- whether a baseline exists
- whether a more recent regression run exists after extraction-routing changes
- whether any hard-fail gates are currently non-zero
- whether repeated weak areas show structural prompt problems

Preferred evidence file:
- `AIOutput/Reports/System/knowledge_extraction_eval_latest_summary.json`

Non-authoritative runs:
- smoke runs
- demo runs
- synthetic placeholder runs

These runs are useful for harness validation but must not be treated as production health evidence.

Suggested health-review status:
- `current`
  - baseline exists and recent runs show no blocking regressions
- `stale`
  - extraction workflow changed but no recent regression run exists
- `failing`
  - the latest run contains blocking regressions
