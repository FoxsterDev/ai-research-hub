# XUUnity Utility: Knowledge Integration

## Goal
Apply a previously reviewed extraction or knowledge integration decision after explicit user approval.

## Entry Commands
- `xuunity apply approved extraction`
- `xuunity system apply approved extraction`
- `xuunity apply approved`
- `xuunity integrate approved knowledge`
- `xuunity system integrate approved knowledge`

## Preconditions
Before using this utility, a reviewed extraction package or `knowledge_intake_review` result must exist.
Do not use this utility until the user has approved the integration scope.

## Destination Routing
Apply approved content only to the smallest correct destination:
- public-safe cross-repo reusable skills, shared knowledge, code style, review protocols, and platform guidance -> `AIRoot/Modules/XUUnity/`
- monorepo-internal shared skills, knowledge, review protocols, product guidance, and utilities -> `AIModules/XUUnityInternal/`
- project-only durable guidance -> `<Project>/Assets/AIOutput/ProjectMemory/`
- project-specific skill-like overrides -> `<Project>/Assets/AIOutput/ProjectMemory/SkillOverrides/`
- project-scoped reports, audits, and knowledge drafts -> `<Project>/Assets/AIOutput/`
- external promotion candidates -> optional external repo only after public-safety review

Semantic destination rules:
- `codestyle/` is only for code-style and code-shape guidance such as naming, formatting, member shape, and coding conventions
- `knowledge/` is for architectural doctrine, decision rules, ownership guidance, routing heuristics, and other root-level reusable guidance
- `skills/` is for repeatable workflows, implementation playbooks, and domain practice
- never place a rule into `codestyle/` only because it is short, generic, or likely to affect code review behavior
- if a rule changes how the agent should think about routing, ownership, architecture, or integration, prefer `knowledge/` over `codestyle/`

Never collapse `project-only` content into shared prompts just because the rule is technically useful in one project.
If a rule depends on one project's memory, architecture, vendor workaround, naming bug, or confidential rollout context, keep it project-local unless the reusable part can be cleanly split out first.
Never collapse monorepo-internal shared content into the public core just because it is reused across many projects in this repo.
If a rule depends on host-local workflows, internal review heuristics, private shared runtime structure, or non-public product conventions, keep it in `AIModules/XUUnityInternal/` unless the public-safe part can be cleanly split out first.

## Approval Inputs
Allowed approval forms:
- full approval
- partial approval with specific sections
- destination-specific approval
- public-core-only approval
- internal-shared-only approval
- shared-only approval
- review-artifact-only approval
- skill-only approval
- external-only approval
- public-core-and-project-only approval
- internal-shared-and-report approval
- shared-and-external approval
- project-only approval
- reject

## Process
1. Read the approved review report.
2. Integrate only the approved parts.
3. Route each approved part to its explicit destination:
   - public-safe reusable cross-repo guidance -> `AIRoot/Modules/XUUnity/`
   - reusable monorepo-internal guidance -> `AIModules/XUUnityInternal/`
   - project-only durable guidance -> `<Project>/Assets/AIOutput/ProjectMemory/`
   - project-specific skill overrides -> `<Project>/Assets/AIOutput/ProjectMemory/SkillOverrides/`
   - project reports or drafts -> `<Project>/Assets/AIOutput/`
   - external promotion -> optional external repo only after public-safe narrowing
4. If the approved package includes a review artifact output, create or update that artifact without forcing the same content into `skills/`.
5. Preserve the meaning of the accepted guidance.
6. If the approved outcome requires a new skill family, create the new family instead of forcing the knowledge into an unrelated existing one.
7. Avoid duplication and conflicts with existing files.
7a. Re-check that each approved item still matches the semantic destination chosen during review; do not let `codestyle/` become a catch-all bucket during apply.
8. If approved content contains both public-core and internal-shared parts, split it before writing files instead of choosing one shared destination for everything.
9. If approved content contains both shared and project-specific parts, split it before writing files instead of choosing one destination for everything.
10. Route nothing into `AIRoot/Modules/XUUnity/` unless the approved content is explicitly public-safe.
11. If the approved outcome includes external promotion, prepare or apply the reusable public-safe version for the selected optional external repo.
12. Report exactly what changed.

## Secret Safety Rule
- Do not integrate literal secret values into any destination, including project memory, reports, shared prompts, or external knowledge.
- Redact sensitive config evidence before writing files. Keep only field names, paths, and minimum necessary masked indicators.
- If the approved package still contains confidential project detail that is not reusable or public-safe, keep it project-local and narrow it further before integration.
- If the approved package is reusable across the monorepo but still not public-safe, keep it in `AIModules/XUUnityInternal/` and do not promote it into `AIRoot/Modules/XUUnity/`.

## Output
- Approved scope
- Updated files
- What was intentionally left unchanged
- Residual risks or follow-up work
