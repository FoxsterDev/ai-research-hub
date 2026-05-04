# XUUnity Review Artifact Contract

## Goal
Define one canonical persistence contract for concrete `xuunity` reviews.

## Canonical Term
Use `review artifact` as the protocol term.

- `report` may still appear in user-facing prose
- `record` may still appear in explanatory prose
- but the rule term is `review artifact`

## Default Rule
For any concrete project-scoped `xuunity` review that reaches one or more of the following:
- findings
- a verdict
- a score
- a cleanup plan
- a release or rollout recommendation

save a Markdown review artifact by default.

Do not rely on the chat response alone unless the user explicitly asked for a transient or no-file review.

## Destination Rule
Destination mapping belongs to:
- `utilities/report_export.md`

Review protocols should not redefine the destination map unless a narrower project router or task-specific contract explicitly overrides it.

## Pre-Fix Record Rule
If the same session later moves into fixes, refactors, rollout work, or validation:
- keep the original saved review artifact as the pre-change record
- write any follow-up validation or post-fix result as a separate artifact
- do not silently replace the original review artifact

## Full Review Rule
`full_review.md` should save one primary aggregate review artifact by default.

Sub-review artifacts are optional unless:
- the user explicitly asked for them
- a sub-review is being delivered as its own durable output
- a project-local override requires separate artifacts

## Output Metadata Rule
Base metadata belongs to:
- `reviews/review_artifact_metadata.md`

Default filename shape belongs to:
- `reviews/review_artifact_naming.md`

Each review protocol still defines its own:
- review-specific extra metadata
- output shape

This contract governs:
- whether to save
- what counts as the default durable behavior
- where the source of truth for destination mapping lives
