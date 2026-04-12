# AIRoot Public Module Architecture Design

Date: 2026-04-12
Status: active
Scope: public-safe architecture for shipping `AIRoot` as a reusable repo or submodule

## Purpose
This design defines the public structure of `AIRoot` and its boundary with host-local layers.

It is intentionally limited to:
- the public `xuunity` core
- generic optional host-local protocol families
- project-local memory and outputs

It does not name or document private host-only protocol families.

## Core Model

`AIRoot` is the public reusable AI layer.

It should contain:
- reusable protocol modules
- reusable setup and integration docs
- reusable templates
- reusable bootstrap scripts
- generic design and visual references

It should not contain:
- host-local mutable state
- project-specific memory
- project-specific reports
- private protocol families by name
- host-specific operational scripts

## Target Repo Shape

```text
airroot/
  README.md
  INTEGRATION.md
  MISSION.md
  Modules/
    XUUnity/
  Operations/
  Templates/
  scripts/
  Design/
  Visuals/
```

When attached to a host repo as a submodule, it should mount at:

```text
HostRepo/
  AIRoot/              <- submodule
  AIModules/           <- optional host-local overlays
  AIOutput/            <- host-local mutable state
  <Project>/
  Agents.md
```

## Layer Boundaries

### 1. Public core
Public reusable protocol logic belongs in:

```text
AIRoot/Modules/XUUnity/
```

This layer must be:
- reusable across repos
- public-safe
- free of project-local assumptions

### 2. Host-local overlays
Optional host-local protocol families belong in:

```text
AIModules/
```

This layer is for:
- monorepo-internal overlays
- private protocol families
- host-specific routing helpers
- internal workflow rules that should not ship publicly

Public `AIRoot` should refer to this layer only generically as optional host-local protocols.

### 3. Project-local truth
Project-specific knowledge belongs in:

```text
<Project>/Assets/AIOutput/ProjectMemory/
<Project>/Assets/AIOutput/
```

This layer remains the source of local truth for:
- project constraints
- verified implementation notes
- project-specific overrides
- project-specific reports and audits

## Repo Modes

### Single-project repo
Use:
- repo router
- public `xuunity` core
- project router
- project memory

No host-local overlay is required.

### Monorepo / multi-project repo
Use:
- repo router
- public `xuunity` core
- optional host-local overlay from `AIModules/`
- project router
- project memory

Host-local overlays are optional, not baseline requirements.

## Load Order

The public model is:

1. repo router
2. public `xuunity` core from `AIRoot/Modules/XUUnity/`
3. optional host-local protocol families from `AIModules/` when the host attaches them
4. project router
5. project memory
6. relevant prior project outputs

## Routing Contract

Public `AIRoot` guarantees only this named protocol family:

- `xuunity`

Host repos may add more protocol families locally, but those should be documented in host-local routing, not in public `AIRoot`.

## Storage Contract

Public reusable material:
- `AIRoot/Modules/`
- `AIRoot/Operations/`
- `AIRoot/Templates/`
- `AIRoot/scripts/`
- `AIRoot/Design/`
- `AIRoot/Visuals/`

Host-local mutable material:
- `AIOutput/Registry/`
- `AIOutput/Reports/`
- `AIOutput/Operations/`

Project-local material:
- `<Project>/Assets/AIOutput/ProjectMemory/`
- `<Project>/Assets/AIOutput/`

## Publication Rules

Before publishing a file inside `AIRoot`, verify:

1. It is reusable across multiple repos.
2. It is public-safe.
3. It does not depend on a private protocol family by name.
4. It does not require host-local mutable state to make sense.
5. It does not contain project-specific data or secrets.

If any answer is `no`, the file belongs outside `AIRoot`.

## Bootstrap Rules

Public bootstrap scripts may:
- initialize repo-level and project-level router scaffolding
- create generic host-local folders like `AIOutput/`
- describe optional `AIModules/` usage generically

Public bootstrap scripts must not:
- assume named private protocol families
- assume host-specific alias-refresh tooling
- generate routers that hardcode private module names

## Design Implications

This architecture means:
- `AIRoot` can be published as a standalone repo
- `AIRoot` can be mounted as `AIRoot/` via git submodule
- host repos can stay simple in single-project mode
- monorepos can add private overlays without contaminating public docs

## Acceptance Criteria

The public architecture is healthy when:
- `AIRoot` can stand alone as its own repo root
- mounting it as `AIRoot/` preserves all public paths
- public docs mention only `xuunity` and generic host-local overlays
- no public bootstrap path depends on host-only scripts outside `AIRoot`
- no project-specific data or private protocol names leak into the public surface
