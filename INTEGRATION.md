# AIRoot Integration Guide

## Purpose
Use this guide when attaching `AIRoot` to a host repository as a reusable module or submodule.
Treat it as an integration contract for AI agents, MCP tools, and automation layers rather than as a manual human checklist.

## Expected Host Responsibilities
The host repo should provide:
- a repo-level router such as `Agents.md`
- any host-local prompt families or private modules
- a repo-level mutable AI state root such as `AIOutput/`
- project routers
- project-local durable memory under `Assets/AIOutput/ProjectMemory/`

## Recommended Host Topology
```text
HostRepo/
  Agents.md
  AIRoot/
    Modules/
      XUUnity/
    Design/
    Operations/
    Templates/
    Visuals/
  AIModules/
    XUUnityInternal/
  AIOutput/
    Registry/
    Reports/
    Operations/
  ProjectA/
    Agents.md
    Assets/
      AIOutput/
        ProjectMemory/
```

## Recommended Routing Contract
- host repo router first
- `AIRoot/Modules/XUUnity/` for the public `xuunity` core
- `AIModules/XUUnityInternal/` as the monorepo-internal shared overlay for `xuunity` when available
- host-local modules outside `AIRoot` when they are private or not public-safe
- project router and project memory after the shared module layer

## Output Contract
- project-local outputs stay under `Assets/AIOutput/`
- host-level mutable state stays under repo-level `AIOutput/`
- `AIRoot` should remain read-mostly and public-safe
- monorepo-internal shared overlays stay under `AIModules/`

## Notes For Tooling
- scripts in `AIRoot/Operations/` may need an explicit host repo root or output directory when run outside an attached host repo
- do not assume a specific host repo name, workstation path, or solution file

## First Repo Bootstrap

When an automation layer attaches `AIRoot` to a host repo for the first time, it should bootstrap the repo-level router first:

Recommended agent-facing entrypoint:

Command phrase:
- `airoot setup`

Treat this as a repo-local setup phrase resolved through `AIRoot/AIROOT_SETUP.md`, not as a required installed command.
The agent should ask for missing setup details, resolve the real host root, preview the topology bootstrap, and apply changes only after explicit confirmation.

Recommended topology-first entrypoint:

```bash
bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --dry-run
```

or, for a monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_topology.sh --profile monorepo_overlay_default --dry-run
```

This path also writes:
- `AIOutput/Registry/host_topology.yaml`
- `AIOutput/Registry/setup_status.yaml`
- extraction evidence slots under `AIOutput/Reports/System/`

For compatibility, the lower-level repo bootstrap remains available:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
```

or, for a monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo --dry-run
```

Then execute the non-preview command only after the governing workflow approves the plan.

Safety rule:
- if the host already has `Agents.md`, the script must not rewrite it silently
- use `--refresh-managed-router` only for an already managed repo router that you intentionally want to rewrite
- use `--adopt-existing-router` only after explicitly deciding to replace an unmanaged repo router

## New Project Bootstrap
When an automation layer attaches `AIRoot` to a host repo that adds a new Unity project, it should bootstrap the project router from the host root with:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode single-project
```

or, for a monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode monorepo
```

Use `--dry-run` first when the agent needs a no-write preview of:
- chosen repo topology
- alias wiring
- router creation or conflict handling

Examples:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode single-project --dry-run
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode monorepo --dry-run
```

This creates or refreshes:
- `Agents.md` for the project
- `Agents.repo.md` as the local repo-router alias
- `Assets/AIOutput/ProjectMemory/` as the project memory root
- baseline project-memory files when they are missing

If the host repo has `AIModules/`, the script also creates:
- `AIModules` as the local host-module alias

If the host repo only attaches `AIRoot` and does not provide `AIModules/`, the script still works and generates a router that uses the public `xuunity` core while marking internal overlays and host-local families as unavailable until they are attached.

Safety rule:
- if the project already has `Agents.md`, the script must not rewrite it silently
- use `--refresh-managed-router` only for an already managed router that you intentionally want to rewrite
- use `--adopt-existing-router` only after explicitly deciding to replace an unmanaged router

For a starting repo-level router, use:
- [REPO_AGENTS_ROUTER_TEMPLATE.md](./Templates/REPO_AGENTS_ROUTER_TEMPLATE.md)

For a starting project-level router, use:
- [PROJECT_AGENTS_ROUTER_TEMPLATE.md](./Templates/PROJECT_AGENTS_ROUTER_TEMPLATE.md)
