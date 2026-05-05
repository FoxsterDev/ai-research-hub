# XUUnity Output Cleanup Scorecard Template

Use this template for every meaningful cleanup candidate and for the final cleanup summary.
Prefer one filled scorecard row per candidate artifact.

## Candidate Scorecard
- Project:
- File path:
- Retention family:
- Branch/feature slice:
- Display category:
- Current location:
- Candidate class:
  - `keep`
  - `archive`
  - `delete_candidate`
  - `manual_review`

## Signal Scores
Score each field from `0` to `3`.
- `0` = none
- `1` = weak
- `2` = medium
- `3` = strong

- Age/staleness:
- Superseded by newer artifact:
- Duplicate/redundant:
- Root-noise / wrong storage location:
- Volatility / report churn pressure:
- Historical value:
- Current-truth dependency:
- Runtime or build relevance:
- Structured-folder replacement exists:
- Junk/orphan/placeholder evidence:
- User-risk if removed:

## Safety Case
- Safe to remove:
  - `yes`
  - `no`
  - `unclear`
- Safe to archive:
  - `yes`
  - `no`
  - `unclear`
- Why safe:
- Why action is useful:
- What remains after action:
- Reversible if archived:
  - `yes`
  - `no`

## Decision Math
- Cleanup pressure score:
  - `age + superseded + duplicate + root-noise + volatility + structured-folder replacement + junk/orphan`
- Preservation pressure score:
  - `historical value + current-truth dependency + runtime relevance + user-risk`
- Net cleanup score:
  - `cleanup pressure - preservation pressure`

## Verdict Rules
- `keep`
  - protected path
  - or preservation pressure >= cleanup pressure
  - or current-truth dependency >= `2`
  - or runtime/build relevance >= `2`
- `archive`
  - net cleanup score >= `2`
  - and safe to archive = `yes`
  - and artifact still has non-zero historical value
- `delete_candidate`
  - junk/orphan/placeholder evidence >= `2`
  - or duplicate/redundant >= `3`
  - or superseded by newer artifact >= `2` and volatility / report churn pressure >= `2`
  - and preservation pressure <= `2`
  - and safe to remove = `yes`
- `manual_review`
  - mixed evidence
  - or safe to remove/archive = `unclear`
  - or historical value >= `2` while cleanup pressure is also high

## Confidence
- Confidence:
  - `high`
  - `medium`
  - `low`
- Main reasons:

## Final Recommendation
- Recommended action:
- Apply now:
  - `yes, if approved`
  - `no`
- Approval needed:
  - `archive approval`
  - `delete approval`
  - `manual decision`

## Summary Scorecard
Use once per cleanup run.

- Projects reviewed:
- Candidates scored:
- `keep` count:
- `archive` count:
- `delete_candidate` count:
- `manual_review` count:
- High-confidence decisions:
- Medium-confidence decisions:
- Low-confidence decisions:
- Protected files skipped:
- Estimated clutter reduction:
- Reference rewrites required:
- Estimated risk of false-positive cleanup:
