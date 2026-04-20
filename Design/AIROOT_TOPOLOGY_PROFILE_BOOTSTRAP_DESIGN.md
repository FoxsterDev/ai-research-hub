# AIRoot Topology Profile Bootstrap Design

Date: 2026-04-16
Status: draft
Scope: refactor the AIRoot onboarding model so the host can choose topology explicitly at startup

## Goal
Make onboarding topology an explicit first-class choice instead of an implicit side effect of bootstrap scripts.

The system should support:
- standard project-local topology
- root-only host topology
- monorepo overlay topology
- symlinked project topology

without requiring manual router surgery after bootstrap.

## Problem Statement
The current public AIRoot bootstrap path assumes one dominant shape:
- repo router at repo root
- project router inside the Unity project
- durable project memory under `<Project>/Assets/AIOutput/ProjectMemory/`
- reports under `<Project>/Assets/AIOutput/`

That works for the default case, but it breaks down when the host wants:
- all AI state at repo root
- no AI files inside the Unity project folder
- a symlinked external Unity project mounted into a host workspace
- a host-specific solution shell that mirrors an external Unity solution

The result is predictable:
- bootstrap scripts generate the wrong shape
- public docs and shared utilities point at dead or unwanted paths
- onboarding requires manual override logic
- system health must treat the host as a special exception instead of a supported profile

## Design Principles
- choose topology first
- store topology as durable host metadata
- generate routers from profile data, not from one hardcoded path layout
- keep public AIRoot generic and public-safe
- make default profile easy, but make custom profiles explicit and supported
- separate public defaults from host-local overrides cleanly
- treat symlinked project shape as a normal supported case, not as an edge hack

## Public-Safety Rules
This document is part of public `AIRoot` and must remain public-safe.

Never include:
- private project names
- private repo names
- company-internal module names
- internal registry URLs
- private workspace paths
- product-specific architecture details that are not reusable

Always use generic placeholders in examples:
- `<HostRepo>`
- `<ProjectName>`
- `<ProfileId>`
- `<RepoMode>`

If a concrete example is useful but not public-safe, rewrite it as a generic pattern instead of naming the real host or project.

## Core Recommendation
Refactor onboarding around a `topology profile` selected before any router or memory files are generated.

The profile should drive:
- router generation
- storage paths
- alias generation
- project-local file policy
- registry shape
- system health expectations
- optional solution mirroring

## Topology Model

### 1. Profile Axes
Do not model topology as only `single-project` vs `monorepo`.

Use a small structured model:
- `repo_mode`
  - `single-project`
  - `monorepo`
- `storage_profile`
  - `project-local`
  - `root-only`
- `router_mode`
  - `repo-and-project`
  - `repo-only`
- `project_link_mode`
  - `direct`
  - `symlinked`
  - `external-linked`
- `solution_mode`
  - `none`
  - `host-only`
  - `mirror-project-solution`

This allows the system to describe real hosts without inventing one-off logic.

### 2. Supported Named Profiles
Expose a small set of named profiles for common onboarding flows.

#### Profile A: `single_project_default`
- `repo_mode: single-project`
- `storage_profile: project-local`
- `router_mode: repo-and-project`
- `project_link_mode: direct`
- `solution_mode: none`

Use this for the current public default.

#### Profile B: `single_project_root_only`
- `repo_mode: single-project`
- `storage_profile: root-only`
- `router_mode: repo-only`
- `project_link_mode: direct`
- `solution_mode: host-only`

Use this when the host wants all AI state under repo root and no AI files inside the Unity project.

#### Profile C: `single_project_root_only_symlinked`
- `repo_mode: single-project`
- `storage_profile: root-only`
- `router_mode: repo-only`
- `project_link_mode: symlinked`
- `solution_mode: mirror-project-solution`

Use this when the host workspace mounts the Unity project via symlink or external link.

#### Profile D: `monorepo_overlay_default`
- `repo_mode: monorepo`
- `storage_profile: project-local`
- `router_mode: repo-and-project`
- `project_link_mode: direct`
- `solution_mode: none`

Use this for multi-project hosts with `AIModules/XUUnityInternal/`.

## Storage Abstraction
Public AIRoot should stop speaking only in literal storage paths.

Introduce these canonical concepts:
- `active repo router`
- `active project memory root`
- `active project reports root`
- `active project skill overrides root`
- `active routed project root`

The host router resolves these concepts into real paths.

### Example Mapping

#### `project-local`
- project memory -> `<Project>/Assets/AIOutput/ProjectMemory/`
- project reports -> `<Project>/Assets/AIOutput/`
- skill overrides -> `<Project>/Assets/AIOutput/ProjectMemory/SkillOverrides/`

#### `root-only`
- project memory -> `AIOutput/ProjectMemory/`
- project reports -> `AIOutput/Reports/`
- skill overrides -> `AIOutput/ProjectMemory/SkillOverrides/`

## Router Model

### Repo Router
The repo router should always exist.

It should define:
- topology profile
- active storage roots
- project routing policy
- legacy path translation rules if the host overrides public defaults

### Project Router
Project routers should become profile-dependent, not mandatory.

Rules:
- `repo-and-project` mode generates project routers
- `repo-only` mode does not generate project routers
- in `repo-only` mode, all project-specific routing lives in the repo router

### Legacy Path Translation
When the host uses a non-default storage profile, the repo router should define canonical path translation:
- legacy project-local paths
- current host-specific paths
- router ownership rules

This makes host override an explicit contract rather than an undocumented workaround.

## Bootstrap Refactor

### Current Limitation
Current scripts:
- `scripts/init_ai_repo.sh`
- `scripts/init_ai_project.sh`

decide too much from fixed assumptions.

### Proposed Refactor
Split bootstrap into phases:

1. `topology resolution`
2. `plan rendering`
3. `router generation`
4. `storage scaffold generation`
5. `optional solution actions`
6. `post-bootstrap health validation`

### CLI Shape
Two safe options are acceptable.

#### Option 1: extend existing scripts
Examples:

```bash
bash AIRoot/scripts/init_ai_repo.sh \
  --repo-mode single-project \
  --storage-profile root-only \
  --router-mode repo-only \
  --project-link-mode symlinked \
  --solution-mode mirror-project-solution \
  --dry-run
```

and:

```bash
bash AIRoot/scripts/init_ai_project.sh \
  --project <ProjectName> \
  --storage-profile root-only \
  --router-mode repo-only \
  --project-link-mode symlinked \
  --dry-run
```

#### Option 2: introduce a topology-first entrypoint
Examples:

```bash
bash AIRoot/scripts/init_ai_topology.sh --profile single_project_root_only_symlinked --project <ProjectName> --dry-run
```

Recommendation:
- keep `init_ai_repo.sh` and `init_ai_project.sh` for compatibility
- add a shared topology resolver module internally
- optionally add `init_ai_topology.sh` as the new canonical public entrypoint

## Durable Host Metadata
Persist the selected profile in a machine-readable file:

```text
AIOutput/Registry/host_topology.yaml
```

Suggested fields:
- `profile_id`
- `repo_mode`
- `storage_profile`
- `router_mode`
- `project_link_mode`
- `solution_mode`
- `routed_projects`
- `active_repo_router`
- `active_project_memory_root`
- `active_project_reports_root`
- `active_project_skill_overrides_root`

This gives system-health and registry tools a stable source of truth.

## Registry Refactor
`AIOutput/Registry/project_registry.yaml` should stop assuming project-local router ownership.

Add fields such as:
- `router_owner`
  - `repo`
  - `project`
- `storage_profile`
- `project_link_mode`
- `solution_mode`
- `project_memory_root`
- `reports_root`
- `skill_overrides_root`

This is a low-risk metadata expansion and should not change runtime behavior.

## System Health Refactor
`system_health_review.md` should validate against the active host topology, not only against legacy project-local expectations.

New checks:
- selected profile exists and is readable
- repo router matches `host_topology.yaml`
- project router presence matches `router_mode`
- actual storage roots match `storage_profile`
- symlinked project paths resolve correctly from real filesystem location
- solution mirror status matches `solution_mode`
- legacy path translation is defined when host profile overrides public default topology

Severity guidance:
- missing topology metadata for a profile-aware host -> `high`
- wrong storage root generated for active profile -> `high`
- legacy docs still mention default topology while repo router overrides it -> `low` or `medium`
- symlink path mismatch that causes dead router paths -> `high`

## Solution Mirroring
For hosts that manage Unity work from a shell workspace, solution behavior should be an explicit supported capability.

### Public-Safe Capability
AIRoot may include an optional utility such as:

```text
scripts/mirror_solution.sh
```

Purpose:
- copy or regenerate a host-level `.sln`
- rewrite project paths through a mounted project folder
- validate the result with `dotnet sln list`

This is public-safe because it is generic and does not depend on private repo names.

## Public AIRoot Additions
These additions are good public-core candidates.

### Knowledge
- `Modules/XUUnity/knowledge/storage_profiles.md`
- `Modules/XUUnity/knowledge/router_override_rules.md`

### Templates
- `Templates/REPO_AGENTS_ROUTER_ROOT_ONLY_TEMPLATE.md`
- `Templates/REPO_AGENTS_ROUTER_SYMLINKED_PROJECT_TEMPLATE.md`
- `Templates/PROJECT_MEMORY_BASELINE_TEMPLATE.md`

### Scripts
- topology resolver shared module
- optional `scripts/init_ai_topology.sh`
- optional `scripts/mirror_solution.sh`

### Utilities
- update `utilities/system_health_review.md`
- update `utilities/system_project_registry_audit.md`
- update `utilities/system_registry_refresh.md`

## What Must Stay Out Of Public AIRoot
Do not put these into public AIRoot:
- host-specific repo names
- private module names
- internal business workflows
- private registry endpoints
- product-specific architecture notes
- one-project-only runtime workarounds

## Migration Strategy

### Phase 1
Add profile-aware metadata and templates without breaking default flow.

### Phase 2
Refactor bootstrap scripts to resolve topology before generating files.

### Phase 3
Make health utilities and registry tools profile-aware.

### Phase 4
Add optional solution mirroring support.

### Phase 5
Deprecate hardcoded wording that treats project-local storage as the only valid topology.

## Acceptance Criteria
The refactor is successful when:
- onboarding begins with an explicit topology choice
- the chosen topology is stored durably in host metadata
- bootstrap output matches the selected profile without manual patching
- `repo-only` mode generates no project router
- `root-only` mode generates no project-local AI storage
- symlinked project mode resolves real filesystem paths correctly
- system health validates profile correctness instead of flagging supported shapes as anomalies
- public docs still present a simple default onboarding path

## Recommended First Implementation Slice
Start with the minimum useful slice:

1. add `host_topology.yaml`
2. extend repo router template to declare active storage roots
3. add `root-only` and `repo-only` support to bootstrap rendering
4. update system health to read active topology
5. add root-only router template and project memory baseline template

This gives immediate practical value without forcing a full bootstrap rewrite in one pass.
