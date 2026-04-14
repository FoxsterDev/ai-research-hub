# XUUnity Utility: Knowledge Intake Review

## Goal
Process one new knowledge input through a full review pipeline before any integration happens.

Use this utility when the user wants one command that:
- extracts the knowledge
- classifies it
- decides whether some parts should become a review artifact, a skill update, a public-core update, an internal-shared update, or a project-local destination
- compares it with current shared skills and prompts
- evaluates quality and reuse value
- checks whether it should replace, refine, merge, or be rejected
- produces a review report
- waits for explicit user approval before integrating anything

## Approval Rule
This utility never updates shared prompts, skills, or project memory automatically.
It only prepares a review package.
Use `knowledge_intake_review_report_template.md` as the output shape.

Integration may happen only after the user explicitly says one of:
- `yes, integrate`
- `merge only these parts`
- `update public core only`
- `update internal shared only`
- `promote to external only`
- `promote to both public core and external`
- `update project override only`
- `reject`

## Pipeline
1. Ingest the knowledge from chat, link, book, or note source.
2. Extract durable rules and separate them from examples and narrative.
3. Map the knowledge to existing public-core `skills/`, `knowledge/`, `codestyle/`, `platforms/`, internal shared overlay destinations, or project overrides.
   - route by semantic type first, not by convenience:
     - `codestyle/` for naming, formatting, code-shape, and local coding conventions
     - `knowledge/` for architectural doctrine, routing rules, ownership rules, and root-level reusable decision guidance
     - `skills/` for repeatable workflows and implementation practice
   - do not use `codestyle/` as the default bucket for reusable guidance that is not actually style guidance
   - for any new shared knowledge candidate, identify how it becomes reachable in normal use:
     - explicit `start_session` load rule
     - shorthand routing
     - keyword or code-signal trigger
     - direct utility or protocol reference
   - if no realistic load path exists, treat the candidate as incomplete until routing is added or the destination is changed
4. Compare the new knowledge with the current source of truth.
5. Evaluate:
   - technical quality
   - production safety
   - Unity `6000+` relevance
   - mobile relevance
   - zero-crash and zero-ANR alignment
   - performance and microfreeze impact
   - novelty versus duplication
   - risk of semantic loss during merge
   - confidentiality and secret-exposure risk
   - public-safety versus internal-only suitability
6. Decide the recommended outcome:
   - no action
   - create or update a review artifact only
   - merge into an existing public-core skill
   - merge into an existing internal-shared skill
   - split into a new public-core skill topic
   - split into a new internal-shared skill topic
   - create a new public-core skill family
   - create a new internal-shared skill family
   - update public-core knowledge only
   - update internal shared only
   - promote to external only
   - promote to both public core and external
   - update project override only
   - reject as low-value or conflicting
7. Prepare a review report for the user.
8. Stop and wait for user approval.

## Secret Safety Rule
- Review the candidate output for literal secret values or project-confidential detail before presenting or integrating it.
- If the source includes credentials or sensitive config values, redact them and keep only the minimum evidence needed for the decision.
- Reject or narrow any integration proposal that would move non-public project detail into shared or external knowledge.

## Scoring
Score each area from `1` to `5`:
- `technical_quality`
- `production_safety`
- `mobile_relevance`
- `novelty`
- `merge_fitness`
- `expected_usefulness`

Interpretation:
- `24-30`
  - strong candidate for integration
- `18-23`
  - useful but may need narrowing or cleanup
- `12-17`
  - weak or partially redundant
- `<12`
  - likely not worth integrating

## Output
- Source summary
- Candidate output split
- Candidate destination
- Why that destination is semantically correct
- Reachability plan:
  - how this knowledge will actually be loaded
  - which keywords, intents, code signals, or protocol references trigger it
- Public-core candidate
- Internal-shared candidate
- External promotion candidate
- Whether an existing skill family is sufficient
- Whether a new skill family should be created
- Existing files affected
- Duplicate and conflict analysis
- What becomes better if integrated
- What problem it solves, if any
- What would not improve even after integration
- Suggested integration shape
- Score table
- Recommended action
- Approval options for the user
