# XUUnity Extraction Authoritative Approval Checklist

## Purpose
Use this checklist before marking an extraction evaluation run as authoritative.

This checklist is intentionally conservative.
Do not convert a run from `pending_human_approval` to authoritative unless the reviewer can defend every approval step from the saved run bundle, report, and prompt pack.

## Inputs
- the run JSON in `AIOutput/Reports/System/`
- the generated Markdown report for the same run
- the generated prompt pack for the same run
- the current baseline report
- the latest summary JSON if it already exists

## Hard Approval Gates
All of these must be true:

- the run is a real regression run, not smoke, demo, or synthetic
- the run used the intended current extraction workflow
- every case in the golden pack was scored
- `critical_omissions == 0`
- `wrong_critical_destinations == 0`
- `unsafe_shared_leaks == 0`
- no case was marked `fail`
- the reviewer personally inspected the report instead of trusting the summary only

If any item above is false:
- do not mark the run authoritative
- keep `evidence_level` as non-authoritative until fixed or rerun

## Reviewer Validation Checklist
Confirm each item explicitly:

- the run date is correct
- the evaluator identity is present
- the workflow version matches the prompts actually being judged
- the run used the intended golden case pack version
- the prompt pack exists and matches the run JSON case IDs
- the report and summary were generated from the same run JSON
- the case outcomes are plausible when compared with the written findings
- no case appears suspiciously under-scored or over-scored relative to the written notes
- no project-local content was accidentally approved as shared-safe
- no duplicated review artifact or skill proposal was accepted without justification
- no meaningful conflict was flattened into a fake consensus
- baseline comparison was considered when the prompts changed

## Safety Questions Before Approval
The approver should be able to answer `yes` to all:

- Would I defend this run as the current best evidence in a system health review?
- If another engineer sampled the cases, would the scoring still look defensible?
- Did I verify at least the highest-risk boundary cases, not just the average score?
- If this run changed behavior versus baseline, is that change actually better rather than merely different?
- Am I confident that no blocking routing or boundary regression is hidden behind a strong mean score?

If any answer is `no`, do not approve yet.

## Minimum Sampling Guidance
Do not approve based on summary metrics alone.

At minimum, the approver should directly inspect:
- every case with a non-perfect score on a critical dimension
- every boundary-safety or project-leak-risk case
- every duplicate-or-merge case
- every conflict-preservation case
- at least one strong pass case, to verify that success cases are not inflated

## Approval Procedure
1. Open the run JSON and generated report.
2. Confirm the hard approval gates.
3. Sample the required cases from the prompt pack and report.
4. Compare the run against the current baseline if prompts changed.
5. If the run is defensible, update run metadata:
   - `evidence_level` -> `human_scored`
   - `approver` -> real reviewer name
   - `approval_date` -> real approval date
6. Regenerate the report and summary so `knowledge_extraction_eval_latest_summary.json` reflects the approved state.
7. Only then treat the latest summary as authoritative health evidence.

## Do Not Do
- do not mark a run authoritative because the average score is high
- do not approve a run you did not inspect
- do not backfill fake approver names or dates
- do not reuse smoke or synthetic runs as approval evidence
- do not treat absence of failures as proof of strong routing quality without sampling

## Ready-To-Approve Statement
Use this only when all checks pass:

`I reviewed the run bundle, sampled the required cases, found no blocking routing or boundary regressions, and approve this run as authoritative human-scored evidence.`
