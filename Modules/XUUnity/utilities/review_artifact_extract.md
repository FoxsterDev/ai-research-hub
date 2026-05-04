# XUUnity Utility: Review Artifact Extract

## Goal
Turn one or more engineering chats, design discussions, or prior extracted notes into a reusable `Engineering Review Artifact`.

Use this utility when the user wants:
- a structured artifact from a long AI chat
- reusable reviewer guidance extracted from brainstorming
- preservation of risks, tradeoffs, rejected options, and test implications
- a durable review handoff before deciding whether the knowledge should enter `skills/` or `knowledge/`

## When To Use
- complex bug investigations
- architecture discussions
- SDK and native integration reasoning
- concurrency and lifecycle reviews
- refactor planning with important tradeoffs

## Process
1. Read the source chat, notes, or prior artifact.
2. Extract the actual engineering problem, constraints, decisions, and risks.
3. Preserve useful reviewer guardrails, dangerous simplifications, and required tests.
4. Consolidate duplicate insights without losing edge cases or caveats.
5. If prior extracted artifacts are also provided, treat them as valuable prior knowledge:
   - preserve important content unless it is clearly weaker, outdated, contradicted, or strictly redundant
   - prefer the strongest version of each insight
   - keep edge cases, warnings, and caveats even if they appear only once
   - if two sources conflict, keep the tension visible instead of flattening it away
6. Redact literal secret values and confidential config payloads before writing the artifact. Keep only file paths, field names, and minimal masked evidence when needed.
7. Output one clean Markdown artifact in the standard `Engineering Review Artifact` shape.
8. If the artifact contains durable reusable knowledge, recommend a follow-up `knowledge_intake_review.md` pass instead of merging automatically.

## Output
- `Engineering Review Artifact`
- reusable reviewer insights
- suggested follow-up destination if the artifact should later influence `skills/`, `knowledge/`, or project memory

When saving a project-scoped review artifact:
- use `reviews/review_artifact_metadata.md` for the base metadata block
- use `reviews/review_artifact_naming.md` for the default filename shape
- use `utilities/report_export.md` for the destination map

Use this exact section shape:
- `# Engineering Review Artifact`
- `## 1. Problem and Context`
- `## 2. Constraints`
- `## 3. Core Technical Questions`
- `## 4. Key Decisions and Conclusions`
- `## 5. Rejected or Dangerous Alternatives`
- `## 6. Critical Risks and Failure Modes`
- `## 7. Reviewer Checklist`
- `## 8. Testing Strategy and Required Coverage`
- `## 9. Reusable Engineering Principles`
- `## 10. Open Questions and Uncertainties`
- `## 11. Final Reviewer Handoff`

## Rule
Do not reduce this utility to a casual summary.
Preserve technical nuance, reviewer implications, and uncertainty.
This utility produces a reusable artifact, not an automatic integration decision.
Prefer explicit conclusions over generic engineering advice.
