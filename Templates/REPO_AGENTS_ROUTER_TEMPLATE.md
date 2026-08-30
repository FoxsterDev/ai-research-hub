# Repo Agents Router Template

Use this template when wiring AI routing in a new host repo.

This is a starting point, not an instruction to overwrite an existing repo router without review.
If the host already has an `AGENTS.md`, compare first, then ask the user whether to:
- keep the existing router as-is
- merge only the missing routing contract
- replace it with a managed version

## Core rules

- Keep the repo router minimal.
- The repo router should decide shared prompt families, load order, and storage rules.
- Project-specific truth must stay in project routers and `Assets/AIOutput/ProjectMemory/`.
- Public operation/tooling repos mounted under `AIRoot/Operations/` may have their own standalone router; root routers should point to the exact child-owned filename instead of treating them as host Unity consumer projects.
- Do not silently rewrite an existing router owned by a project or another team.

## Topology choice

Choose one of these before writing the router:

### A. Single-project host
Use this when the repo has one routed Unity project and no need for a reusable internal shared overlay.

### B. Monorepo / multi-project host
Use this when the repo has multiple routed Unity projects and wants reusable internal shared knowledge across them.

## Single-project repo router skeleton

```md
# Repo Agent Router

## Purpose
This file is the repo-level routing layer.
Keep it minimal.
Use it to select shared prompt families, define load order, and route project-local overrides.

## Load Order
1. This repo-level `AGENTS.md`
2. Optional compact host kernel at `AIOutput/Harness/KERNEL.md` when the host owns it
3. Shared protocol modules from `AIRoot/Modules/`
4. Project-level `AGENTS.md`
5. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
6. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant

## Routing Table
- Use `xuunity` as the default protocol for Unity implementation, review, refactoring, product-facing implementation explanation, SDK work, native work, runtime safety, startup, performance, and compliance.
- Optional host-local protocols may exist outside `AIRoot`, but they should be declared by the host repo, not by this public template.
- If `AIRoot/Operations/XUUnityLightUnityMcp/` is mounted, route MCP repo tasks to its exact child-owned `AIRoot/Operations/XUUnityLightUnityMcp/AGENTS.md`. The tooling satellite remains standalone-capable and owns its router generator; the host must not create a dangling path or overwrite that independent checkout.

## Fast Shortcuts
- `xuunity fix this bug`
- `xuunity refactor this code`
- `xuunity review the git change`
- `xuunity sdk review this integration`
- `xuunity native review this bridge`
- `xuunity feature plan this flow`
- `xuunity product explain this feature`
- `xuunity product health this project`
- `xuunity project memory freshness this project`

## Prompt Family Map
- `xuunity` -> `AIRoot/Modules/XUUnity/`
- host-local private protocols -> `AIModules/` when attached

## Storage Rule
- Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`.
- Project reports and drafts belong in `<Project>/Assets/AIOutput/`.
- Host-level setup and reports belong in `AIOutput/`.
- Public reusable `xuunity` guidance belongs in `AIRoot/Modules/XUUnity/`.
```

## Monorepo repo router skeleton

```md
# Monorepo Agent Router

## Purpose
This file is the repo-level routing layer for the host.
Keep it minimal.
Use it to select shared prompt families, define load order, and route project-local overrides.

## Load Order
1. This repo-level `AGENTS.md`
2. Optional compact host kernel at `AIOutput/Harness/KERNEL.md` when the host owns it
3. Shared protocol modules from `AIRoot/Modules/`, with `xuunity` loading public core from `AIRoot/Modules/XUUnity/`
4. Optional monorepo-internal overlay from `AIModules/XUUnityInternal/` when the host uses it
5. Other host-local prompt families from `AIModules/` when the selected protocol is host-local
6. Project-level `AGENTS.md`
7. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
8. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant

## Routing Table
- Use `xuunity` as the default protocol for Unity implementation, review, refactoring, product-facing implementation explanation, SDK work, native work, runtime safety, startup, performance, and compliance.
- Optional host-local protocols may exist outside `AIRoot`, but they should be declared by the host repo, not by this public template.

## Fast Shortcuts
- `xuunity fix this bug`
- `xuunity refactor this code`
- `xuunity review the git change`
- `xuunity sdk review this integration`
- `xuunity native review this bridge`
- `xuunity feature plan this flow`
- `xuunity product explain this feature`
- `xuunity product health this project`
- `xuunity project memory freshness this project`

## Prompt Family Map
- `xuunity` -> public core `AIRoot/Modules/XUUnity/` plus internal overlay `AIModules/XUUnityInternal/` when the host uses it
- `xuunity-light-unity-mcp` -> public tooling project `AIRoot/Operations/XUUnityLightUnityMcp/` when mounted
- host-local private protocols -> `AIModules/`

## Storage Rule
- Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`.
- Project reports and drafts belong in `<Project>/Assets/AIOutput/`.
- Host-level setup and reports belong in `AIOutput/`.
- Public reusable `xuunity` guidance belongs in `AIRoot/Modules/XUUnity/`.
- Monorepo-internal shared `xuunity` guidance belongs in `AIModules/XUUnityInternal/`.
```

## Existing router policy

If the repo already has an `AGENTS.md`:

1. Read it first.
2. Compare it against the target topology.
3. Identify only the missing contract pieces.
4. Ask the user whether to merge, replace, or leave it unchanged.

Do not assume a rewrite is safe.
