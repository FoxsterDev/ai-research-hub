# AI Protocol Setup Guide

## Purpose
This guide defines the setup contract for AI agents, MCP tools, and automation layers that initialize a host repo using `AIRoot`.
It is written as reusable setup guidance, not as host-specific mutable state.

For the shortest setup map, see:
- `SETUP_INDEX.md`

For host/module integration details, see:
- `../INTEGRATION.md`

## First Setup Decision

Before making any repo or project changes, the agent must classify the host topology.

### Mode A: Single-project repo
Use this when the repo contains one primary Unity project and you do not need a shared internal AI layer across multiple projects.

Recommended stack:
- repo router: `Agents.md`
- public `xuunity` core: `AIRoot/Modules/XUUnity/`
- project router: `<Project>/Agents.md`
- project memory: `<Project>/Assets/AIOutput/ProjectMemory/`

In this mode:
- `AIModules/XUUnityInternal/` is optional and usually absent
- project `AIModules` aliases are not required just to use `xuunity`
- the simplest valid setup is `public core + project memory`

### Mode B: Monorepo / multi-project repo
Use this when the host contains multiple AI-routed Unity projects and you want reusable internal shared knowledge across them.

Recommended stack:
- repo router: `Agents.md`
- public `xuunity` core: `AIRoot/Modules/XUUnity/`
- internal shared overlay: `AIModules/XUUnityInternal/` when present
- project router: `<Project>/Agents.md`
- project memory: `<Project>/Assets/AIOutput/ProjectMemory/`

In this mode:
- `AIModules/XUUnityInternal/` is the right place for reusable internal knowledge that should not live in public `AIRoot`
- project aliases such as `Agents.repo.md` and `AIModules/` are useful for project-only IDE sessions

## Main Rule

When the agent works inside a Unity project, it should read the project router first, but that router depends on shared repo prompts.

For monorepo hosts, project-level alias wiring is recommended:
- `AIModules` -> host `AIModules`
- `Agents.repo.md` -> host `Agents.md`

For single-project hosts, these aliases are optional. The important requirement is that the project router can still resolve the repo router and the shared public `xuunity` core.

## Load Order
1. Repo router: `Agents.repo.md` or repo root `Agents.md`
2. Public `xuunity` core from `AIRoot/Modules/XUUnity/`
3. Monorepo-internal `xuunity` overlay from `AIModules/XUUnityInternal/` only when the host uses that layer, or other host-local prompt families from `AIModules/` when the selected protocol is host-local
4. Project router: `Agents.md`
5. Project memory: `Assets/AIOutput/ProjectMemory/`
6. Previous AI outputs: `Assets/AIOutput/`

## Prompt Families

### `xuunity`
Default protocol for day-to-day Unity project work:
- bug fixing
- refactoring
- feature development
- code review
- SDK integration and review
- native plugin work and review
- runtime safety
- Android and iOS bridge work
- performance, startup, thermal, compliance

Important:
- `xuunity` loads public core from `AIRoot/Modules/XUUnity/`.
- In multi-project hosts, it may also load the internal shared overlay from `AIModules/XUUnityInternal/` when available.
- In single-project hosts, this overlay is usually absent and should not be invented just to complete the setup.

### Optional host-local protocols
Host repos may attach additional private or host-specific protocol families under `AIModules/`.

Use this rule:
- keep public reusable guidance in `AIRoot`
- keep private or host-specific protocols outside `AIRoot`
- do not document private module names in the public setup contract

## First Repo-Level Setup

When an AI agent initializes a host repo that does not yet have a prepared root router, it should bootstrap the repo layer first.

Execution target for a single-project repo preview:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
```

Execution target for a monorepo / multi-project host preview:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo --dry-run
```

After evaluating the preview output, the agent may execute the non-preview command if the change is approved by the governing workflow:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project
```

or:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo
```

Expected script effect:
- creates the host-level `AIOutput/` scaffold
- creates a managed repo-level `Agents.md` when none exists
- refuses to rewrite an existing repo router unless you pass an explicit approval flag

If the repo already has a managed root router and the automation flow explicitly approves a rewrite:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode <single-project|monorepo> --refresh-managed-router
```

If the repo already has a non-managed root router and the automation flow explicitly approves adoption into the managed setup:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode <single-project|monorepo> --adopt-existing-router
```

The agent must not use these flags blindly. It should read the current root router first and request a merge, replace, or leave-unchanged decision before modifying it.

## New Project Setup

When an AI agent initializes a new project inside an already prepared host repo, it should bootstrap the project router next.

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode single-project --dry-run
```

or:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode monorepo --dry-run
```

After evaluating the preview output, the agent may execute the non-preview command if the change is approved by the governing workflow.

Expected script effect:
- creates `Assets/AIOutput/ProjectMemory/` if missing
- creates `Agents.repo.md` and, when available in the host, the `AIModules` alias
- creates a canonical `Agents.md` router when none exists
- refuses to rewrite an existing project router unless you pass an explicit approval flag

If the project already has a managed router and the automation flow explicitly approves a rewrite:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode <single-project|monorepo> --refresh-managed-router
```

If the project already has a non-managed router and the automation flow explicitly approves adoption into the managed setup:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode <single-project|monorepo> --adopt-existing-router
```

## Existing Router Safety Rules

- Existing repo `Agents.md` is not rewritten silently.
- Existing project `Agents.md` is not rewritten silently.
- Use `--refresh-managed-router` only for a managed router you intentionally want to refresh.
- Use `--adopt-existing-router` only after explicitly deciding to replace an unmanaged router.

## Monorepo Alias Wiring

Use this only when a multi-project host already has a prepared repo router and the host supplies its own alias-refresh tooling outside `AIRoot`.
Public `AIRoot` does not define a canonical host-specific alias-refresh script.
