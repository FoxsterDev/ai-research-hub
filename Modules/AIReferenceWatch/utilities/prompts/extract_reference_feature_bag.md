# Extract Reference Feature Bag

Use this prompt when converting a public AI/MCP reference into a normalized
`xuunity.reference-watch.feature-bag.v1` JSON object.

## Inputs

- source id from `Modules/AIReferenceWatch/reference_sources.yaml`
- source URL
- reviewed files or pages
- reviewed timestamp in UTC
- focus areas to inspect

## Instructions

1. Extract only capabilities supported by source evidence.
2. Prefer code registry, tool schema, manifest, and repo-local docs over README
   marketing text.
3. Mark each capability as one of:
   - `implemented`
   - `claimed`
   - `unknown`
   - `contradicted`
   - `not_a_base_goal`
4. Use `claimed` for public docs claims that were not verified in code.
5. Use `unknown` when reviewed sources do not make a clear claim.
6. Use `contradicted` when docs and code disagree.
7. Do not infer feature parity from a broad phrase such as "editor tools".
8. Decompose grouped tools before treating them as capability evidence.
9. For each capability, decide whether it is a direct analog:
   - `directAnalog: true` when the reviewed reference capability directly maps
     to the target capability.
   - `directAnalog: false` when the reference has related implemented code but
     is broader, narrower, or materially different.
   - Use `analogTarget` and `analogNotes` to explain the mapping.
10. For each capability, include provenance:
   - `confidence`
   - `evidenceType`
   - `focusAreas`
   - `sourceFiles`
   - `sourceLines` when available
   - `extractionMethod`
   - `lastReviewedAtUtc`
   - `reviewer`
   - `notes`

## Evidence Checklist

For every capability, answer these questions in the capability metadata or
notes:

- What exact capability is being evaluated?
- Is this a direct analog to the target capability?
- Which file proves registration, schema, or manifest presence?
- Which file proves implementation?
- Is the capability only documented but not code-confirmed?
- Is a broad grouped tool being decomposed into narrower capabilities?
- What related capabilities were searched but not found?
- Should the status be `implemented`, `claimed`, `unknown`, or `contradicted`?

## Output

Return one JSON object matching:

```text
Modules/AIReferenceWatch/utilities/schemas/feature_bag.schema.json
```

Do not include host-private paths, credentials, downloaded snapshot paths, or
implementation code from the reference repository.
