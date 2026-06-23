# XUUnity Utility: Knowledge Extraction Triage

## Goal
Process one source artifact through a unified extraction and routing review before any integration happens.

Use this utility when the user wants one command that:
- reads a source artifact, note, cheatsheet, chat, or document
- extracts durable knowledge
- runs a post-extraction retrospective when the source is a development, implementation, or review session
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
2a. If the source is a development chat, implementation session, or review session, run a retrospective pass after the initial extraction.
   - reconstruct the original user-visible request, the non-negotiable outcome, and the constraints that must survive later simplification
   - reconstruct the important implementation turns, reversals, and user corrections
   - preserve simplification prompts, first-principles prompts, or other explicit user reasoning interventions when they materially changed the solution shape
   - identify what the first over-complex solution assumed, what the later simpler solution removed, and which user inputs caused the change
   - after a resume or context compaction, compare the final answer against the earlier request contract instead of extracting only from the compacted/latest patch
   - preserve decision inputs as review evidence, but do not promote session-specific narrative, host-private detail, or project-local context into public-core knowledge
   - identify the top 3 process or code-shape problems that most increased complexity, semantic drift, or avoidable user rework
   - classify whether each problem came from:
     - missing invariant freeze before refactor
     - semantic boundary blur between different domain concepts
     - abstraction or entity multiplication without concrete payoff
     - lost failure attribution across async or orchestration boundaries
     - logging or severity mismatch on a critical flow
     - existing shared guidance not being applied
     - a genuine gap in the current protocol or shared knowledge
   - summarize the feedback themes the user was actually trying to communicate, not just the individual line edits they requested
   - compare the retrospective findings against current public core and internal shared guidance to distinguish:
     - guidance already existed but was under-applied
     - guidance was missing and should be proposed for integration
   - convert the retrospective findings into normal candidate outputs for review artifacts, shared knowledge, or skill updates instead of leaving them as ad hoc chat commentary
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
4a. Apply semantic destination checks before proposing a file target:
   - `codestyle/` only for language- and code-shape guidance such as naming, formatting, member shape, API shape, and reviewable code conventions
   - `knowledge/` for decision heuristics, architectural rules, ownership boundaries, routing doctrine, and other root-level reusable guidance that is not a code-style rule
   - `skills/` for repeatable implementation workflows, task playbooks, or domain-specific engineering practice
   - review artifacts for findings, risks, decision history, and review-specific guardrails
   - project memory for project truth, local constraints, and project-specific overrides
   - never use `codestyle/` as a fallback destination for generic reusable guidance just because it affects code indirectly
5. For each candidate, decide:
   - is it reusable outside the current project
   - is it reusable outside this monorepo
   - is it public-safe
   - does it depend on internal process, private architecture, or confidential rollout context
   - why it does not belong one layer higher or lower
   - why the selected destination is semantically correct and why nearby alternatives such as `codestyle/`, `knowledge/`, or `skills/` were rejected
5a. Hard placement checklist — apply to every candidate before step 6. Each rule blocks placement until satisfied.
   - **A. Specificity → internal.** If the candidate body references monorepo identifiers (class names, packages, namespaces — see project baseline for the list), it goes to `AIModules/XUUnityInternal/`. Public-core variant, if needed, is a separate stripped file.
   - **B. Anti-rule grep.** Grep existing files for BOTH the candidate keyword and the umbrella term the existing doctrine might use (e.g. candidate "editor test bypass" → also grep `seam`). Any hit with same-or-opposite framing → cite + refine in the existing file or reject. No new standalone file in the face of existing position.
   - **C. Domain-cohesion beats abstract type.** Narrow subsystem topic with siblings in `skills/<subsystem>/` → goes there regardless of `knowledge` vs `skills` abstract classification. Generic engineering pattern discovered via UI bug → root `knowledge/`, not `skills/ui/`. Test: would the reader search by subsystem name or by abstract principle?
   - **D. Median ≤ 30 lines, max ≤ 80.** Target is median, not ceiling. If a file lands between 30 and 80 lines, justify per block why each block of prose changes a reader decision. Repeated background prose is water unless the file owns that background canonically.
   - **E. Pointer, not body copy.** Strong reference impl already in repo → link by path. The file owns the rule + anti-pattern + decision criteria; the code owns the body.
   - **F. Honest framing.** If the candidate proposes a pattern NOT present in canonical industry sources (DI containers / `IMemoryCache` / SWR / Cache-Control / well-known design patterns), the file must explicitly cite those alternatives in a "What This Is Not" or "Alternatives" section and frame the candidate as a project-specific or context-specific choice, not a canonical answer. No "this is the decision rule" framing for bespoke patterns.
   - **G. Process proportionality.** Meta / process / infrastructure files (regression baselines, evaluation specs, retrospective frameworks, measurement recipes) need explicit proportionality justification: how often will the process run? Quarterly or less → single-line addition to existing file beats new standalone spec. Daily or weekly → standalone file is justified. State the expected cadence before creating the file.

5b. Sub-router check. If placing this candidate would add the **3rd or later** narrow routing hint to `tasks/start_session.md` within the same zone (UI / async / SDK / tests / native / etc.), propose a sub-router README in the target subfolder instead. Pattern: collapse all narrow hints in that zone into ONE coarse hint at `start_session.md` that points at the sub-router README, and move the narrow keyword triggers into the README. Apply consistently — if you collapsed one zone in this session, check whether the same logic applies to another zone you touched.

6. Compare each candidate against existing public-core + internal-overlay + project outputs for duplication. Step 5a Rule B is the strict version — perform it before this step.
7. Score each candidate for quality, reuse value, merge fitness, and routing confidence.
8. Produce one review package with:
   - extracted durable content
   - retrospective summary when the source was a development or review session
   - top 3 development/process problems from the retrospective
   - user feedback themes and what they were trying to correct
   - existing-skill coverage versus true protocol gaps
   - destination-by-destination recommendations
   - public-safety assessment
   - internal-sensitivity assessment
   - project-dependency assessment
   - conflicts and duplication analysis
   - explicit apply options
8a. Store the review package in the correct report destination, not in a raw-material inbox:
   - host-level shared review package -> `AIOutput/Reports/ReviewArtifacts/`
   - project-bound review package -> `<Project>/Assets/AIOutput/` or `AIOutput/Projects/<Project>/Reports/` based on scope
   - leave `AIOutput/KnowledgeInbox/` for the raw source item only
8b. Pedagogical value gate. For each candidate file in the review package, write ONE sentence describing what a senior reader learns from this file that they could not infer from the title alone. If you cannot write that sentence honestly, the file is scaffolding — merge into the nearest related file or reject. Surface those one-sentence value claims in the review package so the user can challenge thin files.
9. Stop and wait for user approval.

## Approval Rule
This utility never updates shared prompts, skills, review artifacts, or project memory automatically.
It only prepares a multi-destination review package.
Retrospective-derived candidates follow the same approval rule as the primary extracted knowledge.

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
- Retrospective summary when the source is a development or review session
- Top 3 development/process problems from the retrospective
- User feedback themes
- Existing-skill coverage versus missing guidance
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
- Recommended storage location for the review package
