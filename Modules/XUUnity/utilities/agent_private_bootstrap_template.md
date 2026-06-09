# XUUnity Agent-Private Working Discipline Template

Use this template only inside an agent-private memory, entrypoint, or tool-local config store.
Replace bracketed placeholders with the agent's actual paths and capabilities.
Do not copy this template into project memory.

```markdown
---
name: xuunity-working-discipline
description: Routing only - shared xuunity discipline lives in the public core, host overlay, and project memory. Load and apply those files before implementation; do not duplicate their rule bodies here.
---

This private entry is a router and capability map for [agent/tool name].
The source of truth for reusable Unity work is shared `xuunity`, not this private memory.

## Canonical Sources To Load
- `[repo]/AIRoot/Modules/XUUnity/tasks/start_session.md`
- `[repo]/AIRoot/Modules/XUUnity/knowledge/agent_source_of_truth.md`
- `[repo]/AIRoot/Modules/XUUnity/role/base_role.md`
- `[repo]/AIRoot/Modules/XUUnity/codestyle/`
- `[repo]/AIRoot/Modules/XUUnity/skills/core/`
- task-matched files from `[repo]/AIRoot/Modules/XUUnity/tasks/`, `skills/`, `knowledge/`, `reviews/`, and `platforms/`
- host-local shared overlay when the repo router declares one
- resolved project router and durable project memory before previous outputs

## Working Discipline
- Start `xuunity` work by resolving the project and assembling the minimum stack from `tasks/start_session.md`.
- Load project memory before relying on historical reports or previous AI outputs.
- Decide the safest implementation shape before editing code.
- Prefer the simplest shape that satisfies the requirement; new objects, allocations, thread hops, guards, abstractions, and state machinery need an explicit reason.
- Treat compile/test success as execution evidence, not design validation. State residual design, threading, lifecycle, and correctness risk separately.
- If reusable guidance is learned, promote it into the smallest correct shared layer instead of storing a private copy here.

## Capability Map For This Agent
- Load prompt files: [how this agent reads repo files]
- Search: [preferred search tools]
- Edit: [safe edit mechanism]
- Unity validation: [representative validation route for this host/project, or unsupported]
- Memory update: [how this agent creates/updates this private memory, or unsupported]
- Durable outputs: [where this agent writes reports or task records when asked]

## Calibration
- User-facing style: [short user-specific preferences, if any]
- Local cautions: [agent-specific pitfalls, if any]

## Non-Goals
- Do not duplicate `xuunity` rules here.
- Do not store project architecture truth here.
- Do not store secrets here.
- Do not treat this private entry as stronger than shared `xuunity` or project memory.
```
