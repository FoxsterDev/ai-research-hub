# Compare Feature Bags

Use this prompt after normalized feature bags exist for a local AIRoot module
and one or more external references.

## Inputs

- local feature bag, usually `xuunity_light_unity_mcp`
- reference feature bags
- focus area, for example `ui_primitives`, `transport`, or `build_profiles`
- current design question

## Instructions

1. Compare only capabilities whose `focusAreas` include the target focus.
2. Separate `implemented`, `claimed`, `unknown`, and `contradicted`.
3. Treat `implemented` evidence as actionable only when `directAnalog` is not
   `false`.
4. Treat `implemented` evidence with `directAnalog: false` as design input, not
   backlog.
5. Treat `claimed` evidence as a manual-review task.
6. Do not create backlog candidates from claimed-only or non-direct gaps.
7. Identify:
   - what the local module already does better
   - which references are stronger for the focus area
   - where manual review is required
   - which missing capabilities are backed by actionable evidence
   - which claims are non-actionable
8. Record data-quality caveats when sources were not installed, benchmarked, or
   code-reviewed.

## Direct Analog Checklist

Before calling something a gap, verify:

- the capability status is `implemented`
- the evidence is code/schema/registry/manifest backed
- `directAnalog` is not `false`
- the capability is not only a broad grouped surface
- contradicted evidence is reported separately and never converted to backlog

## Output

Return one JSON object matching:

```text
Modules/AIReferenceWatch/utilities/schemas/comparison_report.schema.json
```
