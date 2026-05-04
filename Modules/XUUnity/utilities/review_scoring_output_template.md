# XUUnity Review Scoring Output Template

Use this template after the findings section of any `xuunity` review that reaches a concrete verdict.

The canonical scoring rules live in:

- `knowledge/review_quality_scoring.md`

This file only standardizes the output shape.

## Template

```md
## Quality Score
- Overall score: `X / 100`
- Distance from top tier: `Y`
- Scope note:
- Scoring confidence:

## Dimension Breakdown
| Dimension | Weight | Score | Why |
| --- | ---: | ---: | --- |
| Correctness and data integrity | 20 |  |  |
| Architecture and ownership clarity | 15 |  |  |
| Safety, resilience, and runtime stability | 15 |  |  |
| Security, privacy, and abuse resistance | 15 |  |  |
| Validation and release confidence | 15 |  |  |
| Observability and operability | 10 |  |  |
| Maintainability and change safety | 10 |  |  |

## Product Interpretation
Short plain-language explanation for non-technical stakeholders.
```

## Narrow-Scope Variant

When the review reweights dimensions because some areas are out of scope, use:

```md
## Quality Score
- Overall score: `X / 100`
- Distance from top tier: `Y`
- Scope note:
- Scoring confidence:
- Reweighting note:

## Dimension Breakdown
| Dimension | Weight | Score | Why |
| --- | ---: | ---: | --- |
| Dimension 1 |  |  |  |
| Dimension 2 |  |  |  |
| Dimension 3 |  |  |  |

## Product Interpretation
Short plain-language explanation for non-technical stakeholders.
```

## Git Change Supplement

For `git_change_review.md`, append this after the canonical score:

```md
## Supplementary Change-Review Lenses
- Core-flow safety:
- Project fit:
- QA readiness:
```

## Notes

- Keep findings primary. The score is synthesis, not the main evidence.
- Do not pretend a narrow score covers the whole project if the review scope was smaller.
- If confidence is low, say so directly.
