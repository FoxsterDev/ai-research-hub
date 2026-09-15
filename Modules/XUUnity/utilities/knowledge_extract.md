# XUUnity Utility: Knowledge Extract

Compatibility note: this narrow legacy route is retained for callers that need
the five-field output below. New general extraction requests route through
`knowledge_extraction_triage.md`, which owns destination selection, review, and
approval workflow.

## Goal
Turn a validated implementation or review insight into a reusable rule.

This utility may also extract reusable logic from upstream research artifacts.

## Output
- Problem
- Solution
- Rule
- Destination file
- Confidence

## Rule
Do not update shared prompts automatically unless the insight is validated and reusable across projects.
Prefer extracting compact rules, scoring logic, reviewer checks, and decision criteria instead of importing whole upstream documents unchanged.
Never carry literal secret values or project-specific credentials into extracted knowledge. Replace any sensitive config detail with redacted placeholders and keep only the reusable rule.
If the source is a development or review session with visible iteration, reversals, or user corrections, run a short retrospective after the primary extraction.
Turn the retrospective into normal review-artifact or knowledge-triage candidates instead of leaving the lessons only in chat.
