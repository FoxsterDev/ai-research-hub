# XUUnity Utility: Knowledge Ingest From Chat

## Goal
Extract durable engineering guidance from implementation or review chat.

## Retrospective Rule
After extracting the direct technical guidance, run a retrospective pass when the chat contains implementation iteration, user corrections, refactor reversals, or review-driven design changes.
- identify the top 3 process or code-shape problems that created avoidable complexity or extra user correction
- summarize what the user feedback was actually trying to teach or constrain
- compare those findings against current public-core and internal-shared guidance
- separate `existing guidance was not followed` from `guidance is missing`
- package any new reusable retrospective lessons as normal review-artifact or knowledge-triage candidates with explicit integration targets
- do not leave the retrospective only as inline chat commentary

## Output
- Source summary
- Extracted insights
- Retrospective summary when applicable
- Top 3 development/process problems
- User feedback themes
- Existing guidance versus missing-guidance assessment
- Proposed destination
- Required verification
- Recommended report location for the reviewed extraction package
