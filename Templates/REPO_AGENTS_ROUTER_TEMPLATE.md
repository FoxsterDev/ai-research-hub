# Repo Agents Router Template

Use this template when wiring AI routing in a new host repo.

This is a starting point, not an instruction to overwrite an existing repo router without review.
If the host already has an `Agents.md`, compare first, then ask the user whether to:
- keep the existing router as-is
- merge only the missing routing contract
- replace it with a managed version

## Core rules

- Keep the repo router minimal.
- The repo router should decide shared prompt families, load order, and storage rules.
- Project-specific truth must stay in project routers and `Assets/AIOutput/ProjectMemory/`.
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
1. This repo-level `Agents.md`
2. Shared protocol modules from `AIRoot/Modules/`
3. Project-level `Agents.md`
4. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
5. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant

## Routing Table
- Use `xuunity` as the default protocol for Unity implementation, review, refactoring, product-facing implementation explanation, SDK work, native work, runtime safety, startup, performance, and compliance.
- Optional host-local protocols may exist outside `AIRoot`, but they should be declared by the host repo, not by this public template.

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
1. This repo-level `Agents.md`
2. Shared protocol modules from `AIRoot/Modules/`, with `xuunity` loading public core from `AIRoot/Modules/XUUnity/`
3. Optional monorepo-internal overlay from `AIModules/XUUnityInternal/` when the host uses it
4. Other host-local prompt families from `AIModules/` when the selected protocol is host-local
5. Project-level `Agents.md`
6. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
7. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant

## Routing Table
- Use `xuunity` as the default protocol for Unity implementation, review, refactoring, product-facing implementation explanation, SDK work, native work, runtime safety, startup, performance, and compliance.
- Optional host-local protocols may exist outside `AIRoot`, but they should be declared by the host repo, not by this public template.

## Prompt Family Map
- `xuunity` -> public core `AIRoot/Modules/XUUnity/` plus internal overlay `AIModules/XUUnityInternal/` when the host uses it
- host-local private protocols -> `AIModules/`

## Storage Rule
- Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`.
- Project reports and drafts belong in `<Project>/Assets/AIOutput/`.
- Host-level setup and reports belong in `AIOutput/`.
- Public reusable `xuunity` guidance belongs in `AIRoot/Modules/XUUnity/`.
- Monorepo-internal shared `xuunity` guidance belongs in `AIModules/XUUnityInternal/`.
```

## Existing router policy

If the repo already has an `Agents.md`:

1. Read it first.
2. Compare it against the target topology.
3. Identify only the missing contract pieces.
4. Ask the user whether to merge, replace, or leave it unchanged.

Do not assume a rewrite is safe.
