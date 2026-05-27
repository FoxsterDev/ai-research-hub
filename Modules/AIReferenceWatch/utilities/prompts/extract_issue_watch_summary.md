# Extract Issue-Watch Summary

Use this prompt when sampling public issues from Tier 1 or focused Tier 2
references.

## Inputs

- source id
- issue list or sampled issue URLs
- sample timestamp in UTC
- labels and keywords used for sampling
- focus area if the issue watch is feature-specific

## Instructions

1. Group issues by recurring technical theme, not by individual ticket.
2. Ignore support noise that does not imply local design or regression risk.
3. Map each issue theme to one local action:
   - `no_local_action`
   - `design_review`
   - `test_gap`
   - `ops_gap`
   - `feature_gap`
4. Record the affected capability area.
5. Mark `xuunityRisk` as:
   - `present`
   - `unknown`
   - `unlikely`
   - `not_relevant`
6. Prefer conservative wording when the issue only suggests a possible risk.

## Output

Return one JSON object matching:

```text
Modules/AIReferenceWatch/utilities/schemas/issue_watch_summary.schema.json
```

Do not mirror an external backlog. The output is only for local design and
regression-check decisions.
