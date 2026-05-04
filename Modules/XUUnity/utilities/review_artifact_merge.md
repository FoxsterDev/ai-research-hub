# XUUnity Utility: Review Artifact Merge

## Goal
Merge two or more `Engineering Review Artifact` documents into one stronger reusable artifact without losing technical nuance.

Use this utility when the user wants to:
- merge multiple chat-derived review artifacts
- consolidate repeated findings and reviewer guidance
- strengthen an old artifact with newer evidence
- preserve rare edge cases and caveats during consolidation

## When To Use
- multiple AI sessions explored the same bug or subsystem
- an old review artifact needs to be updated with new findings
- several artifacts overlap and should become one canonical reusable document

## Process
1. Read all source artifacts.
2. Identify overlapping conclusions, risks, reviewer checks, and test requirements.
3. Keep the strongest and most precise version of each insight.
4. Preserve rare but important caveats, warnings, and edge cases.
5. If artifacts conflict, keep the conflict visible and explain the tension instead of flattening it away.
6. Upgrade weak or vague guidance into stronger reviewer rules only when the combined evidence supports it.
7. Produce one consolidated artifact in a stable reusable shape.
8. If the merged artifact contains durable reusable rules, recommend a follow-up `knowledge_intake_review.md` pass instead of integrating automatically.

## Output
- consolidated `Engineering Review Artifact`
- merged and strengthened reviewer guidance
- unresolved tensions or open questions
- suggested follow-up destination if the artifact should later influence `skills/`, `knowledge/`, or project memory

When saving a project-scoped merged review artifact:
- use `reviews/review_artifact_metadata.md` for the base metadata block
- use `reviews/review_artifact_naming.md` for the default filename shape
- use `utilities/report_export.md` for the destination map

Preferred section shape:
- `# Consolidated Engineering Review Artifact`
- `## 1. Problem and Scope`
- `## 2. Consolidated Constraints`
- `## 3. Final Decisions and Best Practices`
- `## 4. Dangerous Simplifications`
- `## 5. Critical Risks and Failure Modes`
- `## 6. Reviewer Checklist`
- `## 7. Required Test Coverage`
- `## 8. Consolidated Engineering Principles`
- `## 9. Known Edge Cases`
- `## 10. Open Risks / Unresolved Areas`
- `## 11. Reviewer Handoff`

## Rule
Do not merge by averaging wording.
Prefer stronger, clearer, and more precise conclusions while preserving important limits and caveats.
Never drop an insight unless it is clearly incorrect or strictly redundant.
Do not replace specific reviewer warnings with generic summaries.
This utility consolidates artifacts. It does not decide shared prompt integration by itself.
