# AI Setup Index

Use this file as the fastest entrypoint for AI agents and MCP tooling that need to initialize a new host repo or project.

## Start Here

- Main setup guide: `AI_SETUP.md`
- Host/module integration guide: `../INTEGRATION.md`

## Repo-Level Setup

Use this when the host repo itself does not have an AI router yet.

### Preview target

Single-project repo:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
```

Monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo --dry-run
```

### Apply target

Single-project repo:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project
```

Monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo
```

### Script

- `AIRoot/scripts/init_ai_repo.sh`

### Template

- `../Templates/REPO_AGENTS_ROUTER_TEMPLATE.md`

## Project-Level Setup

Use this when the repo already has a root router and the agent is adding a new Unity project.

### Preview target

Single-project host:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode single-project --dry-run
```

Monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode monorepo --dry-run
```

### Apply target

Single-project host:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode single-project
```

Monorepo / multi-project host:

```bash
bash AIRoot/scripts/init_ai_project.sh --project <ProjectName> --repo-mode monorepo
```

### Script

- `AIRoot/scripts/init_ai_project.sh`

### Template

- `../Templates/PROJECT_AGENTS_ROUTER_TEMPLATE.md`

## Existing Router Safety Rules

- Existing repo `Agents.md` is not rewritten silently.
- Existing project `Agents.md` is not rewritten silently.
- Use `--refresh-managed-router` only for a managed router you intentionally want to refresh.
- Use `--adopt-existing-router` only after explicitly deciding to replace an unmanaged router.

## Monorepo Alias Wiring

Use this only for multi-project hosts that already have a prepared repo router and maintain host-specific alias-refresh tooling outside `AIRoot`.
