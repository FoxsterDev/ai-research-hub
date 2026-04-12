# AIRoot

## Purpose
`AIRoot` is the public reusable AI module layer for the monorepo.
Use it for reusable design docs, roadmaps, visual maps, templates, and generic operations guidance.

Do not treat `AIRoot` as the source of truth for protocol behavior.

## Source Of Truth
The canonical instruction and project-context layers stay outside `AIRoot`.
In an attached host repo, these typically include:
- a repo router such as `Agents.md`
- host-local prompt families or private modules when needed
- project routers
- project-local durable memory under `Assets/AIOutput/ProjectMemory/`
- project-local AI outputs under `Assets/AIOutput/`
- host-local mutable AI state under a repo-level `AIOutput/`

`AIRoot` exists to organize the reusable operating layer on top of the runtime sources.

`AIRoot` is intentionally routerless:
- do not add `AIRoot/Agents.md` as a parallel prompt source
- do not create `AIRoot/Assets/AIOutput/ProjectMemory/` as a fake project-memory layer
- keep system-level overrides in shared prompts or in explicit AIRoot operational docs

## Structure
- `Design/`
  System design docs, protocol architecture notes, external extension design notes, and long-form conceptual documents.
- `Roadmaps/`
  Strategic roadmap, execution plan, milestone reviews, and next milestone planning.
- `Visuals/`
  Visual protocol maps, maturity maps, and portfolio diagrams.
- `Operations/`
  Generic operational docs, reusable handbook-style navigation, and protocol change logs.
- `Templates/`
  Reusable templates for repo routers, project routers, portfolio reviews, milestone reviews, and operational reporting.
Public reusable bootstrap scripts now live in `AIRoot/scripts/`:
- `AIRoot/scripts/init_ai_repo.sh` for first repo-level setup
- `AIRoot/scripts/init_ai_project.sh` for project-level setup

These scripts are intended primarily for AI agents, MCP tooling, and automation layers.
Host repos may still keep additional host-specific tooling outside `AIRoot`.

## Layer Map
- `AIRoot/`
  Public reusable layer. Safe to prepare as a standalone repo or submodule.
- `AIRoot/Modules/XUUnity/`
  Public-safe reusable execution protocol layer for shared AI work:
  roles, tasks, reviews, utilities, skills, platforms, and knowledge.
- host-local modules such as `AIModules/`
  Private or host-specific protocol families that should not live in public `AIRoot`.
  This includes `AIModules/XUUnityInternal/` as the monorepo-internal shared overlay for `xuunity`.
- host-local mutable state such as `AIOutput/`
  Setup, handoff, registry, reports, and other live host artifacts.
- project-local state under `<Project>/Assets/AIOutput/`
  Project memory, project outputs, and project-specific durable truth.

Practical rule:
- reusable public-safe protocol behavior -> `AIRoot/Modules/XUUnity/`
- monorepo-internal shared `xuunity` behavior -> `AIModules/XUUnityInternal/`
- private or host-local protocol families -> host repo `AIModules/`
- setup, handoff, registry, and generated reports -> host repo `AIOutput/`
- project memory and project outputs -> `<Project>/Assets/AIOutput/`

## Current Documents
- design:
  - [XUUNITY_SKILLS_SYSTEM_DESIGN.md](./Design/XUUNITY_SKILLS_SYSTEM_DESIGN.md)
  - [XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md](./Design/XUUNITY_PRODUCT_PROTOCOLS_DESIGN.md)
  - [XUUNITY_UPSTREAM_SUBMODULE_DESIGN.md](./Design/XUUNITY_UPSTREAM_SUBMODULE_DESIGN.md)
  - [XUUNITY_EXTERNAL_REPOS_DESIGN.md](./Design/XUUNITY_EXTERNAL_REPOS_DESIGN.md)
- roadmap: [AI_AUTOMATION_ROADMAP.md](./Roadmaps/AI_AUTOMATION_ROADMAP.md)
- execution plan: [AI_AUTOMATION_EXECUTION_PLAN.md](./Roadmaps/AI_AUTOMATION_EXECUTION_PLAN.md)
- protocol visuals: [AI_PROTOCOL_VISUAL_MAP.md](./Visuals/AI_PROTOCOL_VISUAL_MAP.md)
- protocol handbook: [AI_PROTOCOL_HANDBOOK.md](./Operations/AI_PROTOCOL_HANDBOOK.md)
- setup guide: [AI_SETUP.md](./Operations/AI_SETUP.md)
- setup index: [SETUP_INDEX.md](./Operations/SETUP_INDEX.md)
- product-owner setup: [AI_PRODUCT_OWNER_SETUP.md](./Operations/AI_PRODUCT_OWNER_SETUP.md)
- product-owner quickstart: [AI_PRODUCT_OWNER_QUICKSTART.md](./Operations/AI_PRODUCT_OWNER_QUICKSTART.md)
- external repo path migration runbook: [AI_EXTERNAL_REPO_PATH_MIGRATION_RUNBOOK.md](./Operations/AI_EXTERNAL_REPO_PATH_MIGRATION_RUNBOOK.md)
- extraction evaluation: [XUUNITY_KNOWLEDGE_EXTRACTION_EVALUATION.md](./Operations/XUUNITY_KNOWLEDGE_EXTRACTION_EVALUATION.md)
- module integration guide: [INTEGRATION.md](./INTEGRATION.md)
- modules index: [README.md](./Modules/README.md)

## Working Rules
- Put reusable public-safe design, roadmap, visual, template, and generic operations documents in `AIRoot`.
- Put design and strategy documents in `AIRoot/Design/` unless they directly define active prompt behavior.
- Keep public-safe prompt behavior and reusable protocol logic in `AIRoot/Modules/`.
- Keep monorepo-internal overlays and host-local protocol logic in explicit host-local modules outside `AIRoot`.
- Keep project-specific truth in project `Assets/AIOutput/ProjectMemory/`.
- Keep host-local setup, handoff, registry, and generated reports outside `AIRoot`.
- If a document changes protocol behavior, it belongs in the repo root prompt system, not only in `AIRoot`.

## Fast Start
Use the host repo root as the primary runtime AI entrypoint after this module is attached.

Recommended default:
- let the host repo router decide how `AIRoot` is mounted
- use `AIRoot/` as the reusable module subtree
- keep host-local mutable AI state outside `AIRoot`
- treat `AIRoot/Operations/AI_SETUP.md` and `AIRoot/Operations/SETUP_INDEX.md` as the public setup source of truth

Do not use `AIRoot/` as a fake project root or as a replacement for the host repo router.
For host wiring details, use [INTEGRATION.md](./INTEGRATION.md).

## Placement Rule
- If a file explains how the AI system should be designed, extended, or evolved, put it in `AIRoot/Design/`.
- If a file tracks what should happen next, put it in `AIRoot/Roadmaps/`.
- If a file is a reusable generic operations doc, put it in `AIRoot/Operations/`.
- If a file is host-local setup, handoff, registry, or generated state, keep it outside `AIRoot`.
- If a file is part of active routing, prompt loading, or project truth, do not move it into `AIRoot`.

## Suggested Next Files
- `Roadmaps/milestone_reviews.md`
- `Operations/weekly_review.md`
- `Operations/next_milestone.md`
- `Operations/research_watch_log.md`
