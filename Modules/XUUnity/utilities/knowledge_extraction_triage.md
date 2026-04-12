# XUUnity Utility: Knowledge Extraction Triage

## Goal
Process one source artifact through a unified extraction and routing review before any integration happens.

Use this utility when the user wants one command that:
- reads a source artifact, note, cheatsheet, chat, or document
- extracts durable knowledge
- identifies whether some parts should become a review artifact
- identifies whether some parts should become public-core skills or knowledge
- identifies whether some parts belong in monorepo-internal shared skills or knowledge
- prepares one approval package
- stops for explicit user review before any apply step

## Entry Commands
- `xuunity extract ...`
- `xuunity extract knowledge`
- `xuunity extract this source`
- `xuunity system extract ...`

Prefer this utility when the source may produce more than one destination.
Use narrower utilities only when the user already knows the exact target:
- `review_artifact_extract.md`
- `skill_extract.md`
- `knowledge_intake_review.md`

## Pipeline
1. Identify the source type and topic.
2. Separate durable rules from examples, narrative, incidents, and project-local detail.
3. Detect whether the source contains:
   - reviewer guardrails and decision history
   - reusable implementation rules that are public-safe across repos
   - reusable implementation rules that are shared only inside this monorepo
   - non-skill public-core knowledge
   - non-skill internal shared knowledge
   - project-only override details
   - project-scoped report or draft material
4. Build candidate outputs by destination:
   - `Engineering Review Artifact`
   - public-core skill update in an existing family
   - internal-shared skill update in an existing family
   - new public-core skill topic or family
   - new internal-shared skill topic or family
   - public-core knowledge or code style update
   - internal-shared knowledge, review, product, or utility update
   - project override only
   - project report or draft only
   - external promotion candidate
   - no action
5. For each candidate, decide:
   - is it reusable outside the current project
   - is it reusable outside this monorepo
   - is it public-safe
   - does it depend on internal process, private architecture, or confidential rollout context
   - why it does not belong one layer higher or lower
6. Compare each candidate with current public core, internal overlay, and known outputs to avoid duplication.
7. Score each candidate for quality, reuse value, merge fitness, and routing confidence.
8. Produce one review package with:
   - extracted durable content
   - destination-by-destination recommendations
   - public-safety assessment
   - internal-sensitivity assessment
   - project-dependency assessment
   - conflicts and duplication analysis
   - explicit apply options
9. Stop and wait for user approval.

## Approval Rule
This utility never updates shared prompts, skills, review artifacts, or project memory automatically.
It only prepares a multi-destination review package.

Allowed approval styles include:
- `apply all approved items`
- `apply public-core items only`
- `apply internal-shared items only`
- `apply skill items only`
- `apply review artifact only`
- `apply public-core and project-only items`
- `apply internal-shared and report items`
- `apply shared knowledge only`
- `apply only items 1 and 3`
- `reject`

## Output
- Source summary
- Extracted durable rules
- Candidate review artifact output
- Candidate public-core outputs
- Candidate internal-shared outputs
- Candidate project-only outputs
- Candidate project report or draft outputs
- Candidate external promotion outputs
- Public-safety assessment
- Internal-sensitivity assessment
- Project-dependency assessment
- Duplicate and conflict analysis
- Recommended apply scope
- Approval options for the user
