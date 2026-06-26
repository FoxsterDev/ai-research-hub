# XUUnity Personal Paid Module Overlay Design

Date: 2026-06-15
Status: Phase 1-5 implemented locally and verified
Scope: public `XUUnity` support for optional local paid/private module packs, with the first local pack implemented as `xcntp.game_qa_paid_skill`

## Goal

Add support for paid/private XUUnity module packs without committing private content
to the public `AIRoot` repo or to a company project repo.

The immediate target is personal local development:

- public `AIRoot/Modules/XUUnity/` contains only the reusable open/core support
- paid modules live under the existing host-local `AIModules/` root, usually as
  local folders or symlinks to local folders that can become Git repos later
- only the current user's XUUnity sessions can load the paid packs
- other developers do not see, install, or depend on the paid packs
- generated state stays in user-level cache unless explicitly requested

The future target is commercial distribution:

- the same module contract can be published as a private Git repo, private package,
  or paid distribution later
- public XUUnity already knows how to discover, validate, resolve, and health-check
  paid packs when they are present
- paid content remains outside public XUUnity

## Non-Goals

- Do not implement full DRM in the first pass.
- Do not require a hosted licensing server in the first pass.
- Do not commit `XCNT-P` to public `AIRoot`.
- Do not commit real `XCNT-P` paid content to company project repos.
- Do not require a committed `XCNT-P` symlink in company project repos for
  personal development.
- Do not make company projects depend on personal paid modules.
- Do not auto-scan arbitrary folders for private modules.
- Do not put paid content in public docs, reports, or generated artifacts.

## Terms

- `XUUnity core`: public reusable protocol in `AIRoot/Modules/XUUnity/`.
- `AIModules root`: the host-local/private module root already supported by the
  repo router.
- `paid module root`: a local folder that contains `module.json`.
- `pack`: one feature bundle inside a module root, described by `pack.json`.
- `entitlement loader`: public XUUnity code that reads local grants and decides
  which installed packs are allowed.
- `module registry`: the resolved list of available, loaded, locked, invalid, and
  ignored packs for the current user/session.
- `Rollsync`: the planned resolve-and-sync gate that refreshes module registry
  state, validates private-module boundaries, and reports whether the active
  XUUnity session may load paid packs.

`Rollsync` is implemented by `Modules/XUUnity/scripts/module_registry_tool.py`
as the validate-resolve-cache health gate for optional private packs.

## Recommended Local Topology

Preferred personal layout:

```text
Workspace/
  CompanyProject/
    AIRoot/
      Modules/
        XUUnity/
    AIModules/
      XUUnityInternal/
      Nexus -> <private-module-root>/Nexus
      ExploreTheGame/
      XCNT-P -> <private-module-root>/XCNT-P
    <UnityProject>/

  <private-module-root>/XCNT-P/
    module.json
    packs/
      game_qa_paid_skill/
        pack.json
        skills/
        reviews/
        utilities/
        tests/
```

The preferred discovery surface is `AIModules/` because the host router already
uses it for private/local modules such as `XUUnityInternal`, `Nexus`, and
non-Unity modules such as `ExploreTheGame`.

For personal paid modules, the `AIModules/XCNT-P` entry may be a symlink to a
folder outside the company project checkout. That keeps development convenient
while avoiding a committed copy of the paid content.

User-level config:

```text
~/.xuunity/config.json
~/.xuunity/entitlements.json
~/.xuunity/cache/
```

Example `~/.xuunity/config.json`:

```json
{
  "schemaVersion": "xuunity.user-config.v1",
  "additionalModuleSearchPaths": [
    "<private-module-root>/XCNT-P"
  ],
  "moduleCacheRoot": "<user-cache-root>/.xuunity/cache",
  "allowAIModulesDiscovery": true
}
```

Default behavior should prefer the host-declared `AIModules/` root when present.
User-level paths are additive for development outside a host checkout.

No broad parent-folder search should be used.

## Public Core Additions

Public XUUnity should add only the support system, not paid content:

```text
AIRoot/
  Modules/
    XUUnity/
      schemas/
        xuunity.module.schema.json
        xuunity.pack.schema.json
        xuunity.entitlements.schema.json
        xuunity.resolved-modules.schema.json
        xuunity.installer.schema.json
      scripts/
        module_registry_tool.py
      utilities/
        module_registry.md
        module_rollsync.md
        module_commercialization.md
```

Optional future integration points:

```text
AIRoot/
  Modules/
    XUUnity/
      tasks/
        module_development.md
      reviews/
        module_pack_review.md
```

The public support layer may mention generic local/private modules, but must not
name private customer-only pack internals as part of the public baseline.

## Private Module Root Contract

Every paid module root must contain:

```text
XCNT-P/
  module.json
```

Example:

```json
{
  "schemaVersion": "xuunity.module.v1",
  "id": "xcntp",
  "displayName": "XCNT-P",
  "kind": "personal_private_overlay",
  "visibility": "personal_private",
  "version": "0.1.0",
  "protocolScopes": [
    "xuunity"
  ],
  "discovery": {
    "preferredRoot": "AIModules",
    "symlinkAllowed": true
  },
  "xuunityCore": {
    "compatibleRange": ">=0.1.0"
  },
  "license": {
    "feature": "xcntp",
    "defaultState": "locked"
  },
  "packs": [
    "packs/game_qa_paid_skill/pack.json"
  ],
  "exportPolicy": {
    "mayCommitToHostRepo": false,
    "mayWriteResolvedRegistryToProject": false,
    "mayQuotePrivateContentInReports": false
  }
}
```

Required fields:

- `schemaVersion`
- `id`
- `displayName`
- `kind`
- `visibility`
- `version`
- `protocolScopes`
- `packs`
- `exportPolicy`

Path rules:

- pack paths must be relative to the module root
- pack paths must not escape the module root with `..`
- symlink module roots under `AIModules/` are allowed when the symlink itself is
  inside `AIModules/` and the resolved target contains a valid `module.json`
- paths declared inside a symlinked module must still stay inside the resolved
  module target
- module ids must be stable lowercase identifiers
- modules whose `protocolScopes` do not include `xuunity` or `universal` must be
  visible in scans but ignored by XUUnity resolution

## Pack Contract

Every pack must contain:

```text
XCNT-P/
  packs/
    game_qa_paid_skill/
      pack.json
```

Example first pack:

```json
{
  "schemaVersion": "xuunity.pack.v1",
  "id": "xcntp.game_qa_paid_skill",
  "displayName": "Game QA Paid Skill",
  "tier": "personal_pro",
  "licenseFeature": "xcntp.game_qa_paid_skill",
  "dependsOn": [
    "xuunity.core"
  ],
  "capabilities": [
    "xuunity.game_qa.runtime_ui_validation",
    "xuunity.game_qa.playmode_smoke_planning"
  ],
  "entrypoints": {
    "skills": [
      "skills/routing.md",
      "skills/playmode_smoke_pro.md",
      "skills/project_capability_inventory_pro.md"
    ],
    "reviews": [
      "reviews/game_qa_release_review.md"
    ],
    "utilities": [
      "utilities/usage.md"
    ],
    "knowledge": []
  },
  "mcp": {
    "requiredCapabilities": [],
    "providedCapabilities": [
      "xuunity.game_qa.playmode_smoke_planning"
    ],
    "tools": []
  },
  "routing": {
    "triggers": ["game qa", "playmode smoke"],
    "capabilities": ["xuunity.game_qa.runtime_ui_validation"]
  },
  "exportPolicy": {
    "mayQuotePrivateContentInReports": false,
    "reportReferenceMode": "pack_id_only"
  }
}
```

Required fields:

- `schemaVersion`
- `id`
- `displayName`
- `licenseFeature`
- `dependsOn`
- `entrypoints`
- `exportPolicy`

The `entrypoints` section should be declarative only. The loader builds a list
of loadable files; it does not infer files by crawling the pack directory.

## Entitlement Contract

Initial personal mode uses a local grant file:

```text
~/.xuunity/entitlements.json
```

Example:

```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "subject": "siarhei-local",
  "mode": "personal_dev",
  "source": "local_user_grant",
  "provider": {
    "type": "local_file",
    "mode": "personal_dev",
    "trustLevel": "local_flag",
    "verified": false,
    "checkedAtUtc": "2026-06-15T00:00:00Z"
  },
  "features": [
    "xcntp",
    "xcntp.game_qa_paid_skill"
  ],
  "expiresAtUtc": ""
}
```

Personal mode rules:

- `mode: personal_dev` is accepted only from user-level config paths.
- It must never be read from a company project repo by default.
- It enables local development and private personal use.
- It is not a commercial license verification mechanism.
- It always reports `trustLevel: local_flag` and `verified: false`.

Future commercial modes can reuse the same feature model:

- `signed_offline`
- `online_sync`

The resolver should expose the provider mode and trust level in diagnostics so
paid-pack behavior is auditable. Commercial signature checks and server
verification belong to a future entitlement provider, not to the prompt
resolver.

## Installer Manifest Contract

Commercial package distribution may include an installer manifest. The manifest
is metadata only; it must not contain private prompt bodies or absolute private
paths.

Example:

```json
{
  "schemaVersion": "xuunity.installer.v1",
  "moduleId": "xcntp",
  "displayName": "XCNT-P",
  "recommendedMount": "AIModules/XCNT-P",
  "requiredFeatures": [
    "xcntp",
    "xcntp.game_qa_paid_skill"
  ],
  "postInstallChecks": [
    "xuunity_module_status",
    "xuunity_module_rollsync"
  ]
}
```

Validate without reading private pack bodies:

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py validate-installer \
  --installer <path-to-installer.json>
```

## Entitlement Loader Behavior

The loader is implemented in public XUUnity support code.

Inputs:

- public core path
- host root path
- host `AIModules/` path when present
- user config path
- environment override `XUUNITY_MODULE_PATHS`
- user entitlements path
- optional command arguments
- current host/project path for context only

Resolution order:

1. Always include `xuunity.core`.
2. Discover module roots directly under host `AIModules/` when that root exists.
3. Read explicit module roots from CLI args.
4. Read `XUUNITY_MODULE_PATHS` if present.
5. Read `additionalModuleSearchPaths` from `~/.xuunity/config.json`.
6. Validate every discovered module root with `module.json`.
7. Classify module roots without `module.json` as `unregistered_module_root`
   instead of crawling them.
8. Filter XUUnity resolution by `protocolScopes`.
9. Validate every declared pack for in-scope modules.
10. Read user-level entitlements.
11. Mark each pack as `loaded`, `locked`, `invalid`, or `ignored`.
12. Write resolved output only to user cache.

Discovery must not guess arbitrary sibling folder names. The only implicit
host-local discovery root is the router-owned `AIModules/` directory.

## Resolved Registry Output

Default path:

```text
~/.xuunity/cache/resolved_modules/<project-hash>.json
```

Example:

```json
{
  "schemaVersion": "xuunity.resolved-modules.v1",
  "resolvedAtUtc": "2026-06-15T00:00:00Z",
  "projectRoot": "/path/to/CompanyProject",
  "writeScope": "user_cache",
  "outputBoundary": "private_runtime",
  "discoveryRoots": [
    {
      "kind": "host_aimodules",
      "path": "/path/to/CompanyProject/AIModules"
    }
  ],
  "scannedModules": [
    {
      "id": "xcntp",
      "root": "/path/to/CompanyProject/AIModules/XCNT-P",
      "resolvedRoot": "<private-module-root>/XCNT-P",
      "protocolScopes": ["xuunity"],
      "resolution": "in_scope"
    },
    {
      "id": "explore_the_game",
      "root": "/path/to/CompanyProject/AIModules/ExploreTheGame",
      "protocolScopes": ["explore_the_game"],
      "resolution": "ignored_protocol_scope"
    }
  ],
  "loadedModules": [
    {
      "id": "xuunity.core",
      "source": "public_core",
      "root": "/path/to/CompanyProject/AIRoot/Modules/XUUnity"
    }
  ],
  "loadedPacks": [
    {
      "id": "xcntp.game_qa_paid_skill",
      "moduleId": "xcntp",
      "source": "personal_private_overlay",
      "root": "/path/to/XCNT-P/packs/game_qa_paid_skill",
      "licenseFeature": "xcntp.game_qa_paid_skill",
      "capabilities": [
        "xuunity.game_qa.runtime_ui_validation",
        "xuunity.game_qa.playmode_smoke_planning"
      ],
      "entitlementMode": "personal_dev",
      "entitlementTrustLevel": "local_flag",
      "entitlementVerified": false,
      "entrypoints": {
        "skills": [
          "/path/to/XCNT-P/packs/game_qa_paid_skill/skills/routing.md"
        ],
        "reviews": [],
        "utilities": [],
        "knowledge": []
      }
    }
  ],
  "lockedPacks": [],
  "invalidPacks": [],
  "warnings": []
}
```

Private content protection:

- resolved registry may include private file paths in user cache
- resolved registry must not be written outside the user cache
- reports intended for company/public repos should reference private packs only
  by pack id and version, never by copied content
- modules in `AIModules/` that are not in XUUnity scope must remain visible in
  scan diagnostics but absent from `loadedPacks`

## CLI/API Surface

Implement a public script:

```text
Modules/XUUnity/scripts/module_registry_tool.py
```

Required commands:

```bash
python3 Modules/XUUnity/scripts/module_registry_tool.py scan
python3 Modules/XUUnity/scripts/module_registry_tool.py validate
python3 Modules/XUUnity/scripts/module_registry_tool.py resolve --project-root <path>
python3 Modules/XUUnity/scripts/module_registry_tool.py rollsync --project-root <path>
python3 Modules/XUUnity/scripts/module_registry_tool.py doctor --project-root <path>
```

Command semantics:

- `scan`: list configured module roots and whether `module.json` exists.
- `validate`: validate module and pack manifests without loading content.
- `resolve`: produce the resolved registry.
- `rollsync`: validate + resolve + health gate + cache write.
- `doctor`: explain why a pack is not available.

Exit codes:

- `0`: success
- `1`: validation failed
- `2`: entitlement missing or locked
- `3`: unsafe path/export policy violation
- `4`: incompatible schema/version
- `5`: unexpected runtime error

Suggested wrapper names:

```bash
xuunity module scan
xuunity module validate
xuunity module resolve
xuunity module rollsync
xuunity module doctor
```

The wrapper can be added later. The Python script is the first stable API.

## Rollsync Contract

`rollsync` is the operational command that makes paid modules reliable before a
session uses them.

It must check:

- host `AIModules/` root is discoverable when present
- user config is readable
- configured module roots exist
- symlink module roots resolve to readable local targets
- module manifests pass schema validation
- `AIModules/` entries without `module.json` are reported but not crawled
- out-of-scope modules are ignored without becoming errors
- pack manifests pass schema validation
- entrypoint files exist
- paths do not escape module roots
- entitlements are readable
- loaded packs are explicitly entitled
- locked packs are reported clearly
- private pack content is not copied into project output
- resolved registry is written to user cache
- current public core version is compatible

`rollsync` output:

```json
{
  "action": "xuunity.module.rollsync",
  "status": "ready",
  "loaded_pack_count": 1,
  "locked_pack_count": 0,
  "invalid_pack_count": 0,
  "cache_path": "<user-cache-root>/.xuunity/cache/resolved_modules/hash.json",
  "next_actions": []
}
```

Allowed statuses:

- `ready`
- `ready_with_warnings`
- `locked`
- `invalid`
- `unsafe`
- `not_configured`

## XUUnity Session Integration

`tasks/start_session.md` should eventually learn this optional step:

1. Load public XUUnity core.
2. If module registry support exists, read the latest resolved registry from
   user cache.
3. If no resolved registry exists, do not auto-load private modules.
4. If the user requests paid/private modules, run or request `rollsync`.
5. Load only `loadedPacks` from the resolved registry.
6. Treat `AIModules/` packs, symlinked `AIModules/` packs, and user-config
   packs the same after resolution.
7. Place private packs after public core and before project memory.
8. Keep project memory as the final project-specific truth.

Load order with private packs:

```text
1. repo router
2. public XUUnity core
3. loaded personal/private paid packs
4. project router
5. project memory
6. relevant prior outputs
```

This mirrors the existing optional overlay model while keeping personal paid
packs outside the host repo.

## System Health Integration

Update `Modules/XUUnity/utilities/system_health_review.md` to include a private
module overlay subsection when module registry support is present.

Health checks:

- module registry schema exists
- module registry tool exists
- host `AIModules/` root is detected when present
- `AIModules/` entries with `module.json` are scanned
- `AIModules/` entries without `module.json` are reported as unregistered
  rather than silently crawled
- symlink module roots resolve to readable targets
- out-of-scope modules such as non-XUUnity private modules are ignored by
  XUUnity resolution
- latest rollsync artifact exists or is explicitly not configured
- private packs are not inside public `AIRoot`
- private packs are not inside company project root unless explicitly allowed
- no public docs copy private pack bodies
- no project output contains private entrypoint content
- system can distinguish `not_configured`, `locked`, `invalid`, and `ready`

Output subsection shape:

```md
**Private Module Overlay Status**
- `module_support`: `present` | `absent`
- `rollsync_status`: `ready` | `ready_with_warnings` | `locked` | `invalid` | `unsafe` | `not_configured` | `not_run`
- `resolved_registry`: `<user-cache path or none>`
- `aimodules_root`: `<path or none>`
- `scanned_aimodules`: `<count>`
- `out_of_scope_modules`: `<count>`
- `loaded_private_packs`: `<count>`
- `locked_private_packs`: `<count>`
- `project_repo_contamination`: `none` | `detected` | `not_checked`
- `gaps`:
  - `<gap or none>`
```

## Public/Private Boundary Rules

Public XUUnity may contain:

- schemas
- loader/resolver code
- generic docs
- empty examples with fake ids
- validation tests

Public XUUnity must not contain:

- real `XCNT-P` paid pack files
- real private module entrypoint text
- local personal grants
- customer-specific pack ids if those ids are not intentionally public
- generated resolved registries that reveal private paths

Company project repos must not contain:

- real `XCNT-P` paid module content
- a committed `XCNT-P` symlink unless the host owner intentionally wants that
  private module reference in the repo
- `~/.xuunity` equivalent config
- personal entitlements
- resolved registry cache
- copied paid prompt bodies

Personal local work may have:

- an untracked or ignored `AIModules/XCNT-P` symlink to a local paid module repo
- tracked host-local modules such as `XUUnityInternal` when the host already
  owns that convention
- unrelated private modules such as `Nexus` or `ExploreTheGame`, as long as
  their manifests declare the correct `protocolScopes`

Reports written into company repos may say:

```text
Private pack used: xcntp.game_qa_paid_skill@0.1.0
```

Reports must not include:

- private skill file contents
- private review checklist bodies
- private module absolute paths unless the report is user-local

## First Pack: Game QA Paid Skill

Initial local private pack:

```text
XCNT-P/
  packs/
    game_qa_paid_skill/
      pack.json
      skills/
        routing.md
        playmode_smoke_pro.md
        project_capability_inventory_pro.md
        popup_environment_handling_pro.md
      reviews/
        game_qa_release_review.md
      utilities/
        usage.md
      tests/
        manifest_validation_cases.json
```

First useful behavior:

- richer PlayMode smoke routing
- stronger project-defined hook inventory
- UI state polling doctrine
- popup/environment stabilization
- evidence summary discipline

The first pack should not require Unity-side paid code.
Keep it as prompt/protocol content first. Add MCP/Unity operations only after
the prompt pack proves useful.

## Feature Branch Migration: `feature/game-qa-paid-skill`

The branch `feature/game-qa-paid-skill` contains the first Game QA paid skill
content, but it placed the paid files under public XUUnity paths:

```text
Modules/XUUnity/role/game_qa_brain.md
Modules/XUUnity/skills/game_qa/
Modules/XUUnity/skills/registry.md
Modules/XUUnity/tasks/start_session.md
Modules/XUUnity/reviews/policy_packs/ui_heavy_changes.md
```

Do not merge that branch raw into public `master`.

Reason:

- a normal merge would publish paid skill bodies into public XUUnity
- even a follow-up delete would leave paid content in public Git history
- public `master` should receive only generic private-module support and
  public-safe routing contracts

Prepared private destination:

```text
<HostRepo>/_HostLocal/XCNT-P/
<HostRepo>/AIModules/XCNT-P -> ../_HostLocal/XCNT-P
```

Prepared private pack id:

```text
xcntp.game_qa_paid_skill
```

The content from the feature branch should live in:

```text
_HostLocal/XCNT-P/packs/game_qa_paid_skill/
```

Public `master` integration should be a clean branch from `master` that adds:

- module registry schemas
- `module_registry_tool.py`
- Rollsync support
- system health private-module checks
- generic docs for `AIModules` private paid packs

Public `master` integration should not add:

- `Modules/XUUnity/skills/game_qa/`
- `Modules/XUUnity/role/game_qa_brain.md`
- direct `skills/registry.md` entries for private Game QA files
- direct `tasks/start_session.md` references to private Game QA files
- paid checklist bodies in public policy packs

Public-safe candidates from the feature branch may be re-authored only if they
are generic support rules, for example a short note that
`project_defined_hook_poll_until` is a preferred MCP primitive for async
project-defined UI flows. Such notes must not depend on private pack paths.

Current verification status:

- private `AIModules/XCNT-P` symlink resolves locally
- `module.json` and `pack.json` parse successfully
- all declared `xcntp.game_qa_paid_skill` entrypoints exist
- local personal entitlement includes `xcntp` and `xcntp.game_qa_paid_skill`
- content copied from `feature/game-qa-paid-skill` matches the local paid pack
  for `role/game_qa_brain.md` and all `skills/game_qa/*` files
- `module_registry_tool.py validate --project-root ..` reports `status: valid`
- `module_registry_tool.py rollsync --project-root ..` reports `status: ready`
  with loaded pack `xcntp.game_qa_paid_skill`
- `module_registry_tool.py route-smoke --project-root .. --task-text
  "validate ui after a fix with PlayMode smoke" --expect-pack
  xcntp.game_qa_paid_skill` reports `status: passed`
- route smoke loads entrypoints through `AIModules/XCNT-P` and reports
  `publicPathLeakDetected: false`

Implemented public support before claiming end-to-end routing:

- implement `module_registry_tool.py`
- implement `rollsync`
- write resolved registry to user cache
- update `tasks/start_session.md` to read `loadedPacks`
- add a routing smoke proving that a Game QA task resolves
  `xcntp.game_qa_paid_skill` through `AIModules/XCNT-P`, not through public
  `Modules/XUUnity/skills/game_qa`

## Implementation Plan

### Phase 1: Public support skeleton

1. Add manifest schemas under `Modules/XUUnity/schemas/`.
2. Add `module_registry_tool.py` with `scan`, `validate`, `resolve`, `rollsync`,
   and `doctor`.
3. Add unit tests using temporary local module roots.
4. Add utility docs for module registry and rollsync.
5. Update system health review with the private module overlay subsection.

Acceptance:

- no private content is required for tests
- fake local module fixtures validate and resolve
- resolved registry writes to user cache by default
- unsafe project writes are rejected

### Phase 2: Personal local XCNT-P root

Status: completed locally on 2026-06-15.

Actual local folder:

```text
<HostRepo>/_HostLocal/XCNT-P/
```

Actual local link:

```text
<HostRepo>/AIModules/XCNT-P -> ../_HostLocal/XCNT-P
```

Implemented:

1. Created local private folder under `_HostLocal/XCNT-P`.
2. Linked it into host-local `AIModules/XCNT-P`.
3. Kept both `_HostLocal/` and `AIModules/XCNT-P` ignored/untracked for host repo personal development.
4. Added `module.json`.
5. Added `packs/game_qa_paid_skill/pack.json`.
6. Added first Game QA paid entrypoint docs and content.
7. Added local `~/.xuunity/entitlements.json` with `xcntp` and
   `xcntp.game_qa_paid_skill`.
8. Ran `rollsync`.

Acceptance:

- public repo remains clean
- company repo remains clean
- `AIModules/XCNT-P` symlink resolves locally
- `rollsync` reports one loaded private pack
- locked/invalid states are testable by editing local grants

Phase 2 verification:

- `AIModules/XCNT-P` resolves to `../_HostLocal/XCNT-P`
- `module_registry_tool.py validate --project-root ..` reports `status: valid`
- `module_registry_tool.py rollsync --project-root ..` reports `status: ready`
  with loaded pack `xcntp.game_qa_paid_skill`
- `module_registry_tool.py doctor --project-root .. --pack-id
  xcntp.game_qa_paid_skill` reports `status: loaded`
- route smoke for `validate ui after a fix with PlayMode smoke` reports
  `status: passed` and `publicPathLeakDetected: false`

### Phase 3: Session routing

Status: completed locally on 2026-06-15.

Implemented:

1. Defined how the active AI session reads the resolved registry.
2. Added start-session guidance that private packs are optional and user-local.
3. Ensured private pack paths are loaded only from `loadedPacks`.
4. Added report redaction rules for private pack usage.
5. Added `module_registry_tool.py session-plan` as the session-routing proof.
6. Added `utilities/module_session_routing.md`.
7. Added report export rules for `private_pack_report_references`.

Acceptance:

- sessions can use Game QA Paid Skill when enabled
- sessions continue normally when private modules are absent
- private pack content is not copied into company repo output

Phase 3 verification:

- `session-plan` with entitled `xcntp.game_qa_paid_skill` reports
  `status: private_pack_loaded`
- `session-plan` with a locked matching pack reports
  `status: private_pack_unavailable` and `fallback: continue_with_public_core`
- `session-plan` with no private module reports `status: public_core_only`
- session report references use pack id only, for example
  `Private pack used: xcntp.game_qa_paid_skill`
- unit tests cover enabled, locked, absent, and redacted report-reference paths

### Phase 4: MCP/API extension

Status: completed locally on 2026-06-15.

Implemented:

1. Added host-side MCP/API-safe helper commands:
   - `xuunity_module_status`
   - `xuunity_module_rollsync`
2. Kept these tools generic and public.
3. Redacted private content from MCP/API output.
4. Documented the tool contract in
   `Modules/XUUnity/utilities/module_mcp_api.md`.

Acceptance:

- MCP can report loaded/locked/invalid packs
- MCP output redacts private file contents
- no Unity Editor package changes are required for prompt-only packs

Phase 4 verification:

- `xuunity_module_status --project-root ..` reports loaded, locked, and invalid
  pack sections in a redacted shape
- `xuunity_module_rollsync --project-root ..` writes the user-cache registry and
  returns a redacted status response
- redacted API output omits private module paths, private entrypoint paths, and
  private file contents
- the implementation lives in public `module_registry_tool.py`; no
  `Operations/XUUnityLightUnityMcp` or Unity package changes are required

### Phase 5: Future commercialization

Status: completed as a commercialization-ready local contract on 2026-06-15.

Implemented:

1. Kept the same manifest and feature resolution model.
2. Extended `xuunity.entitlements.v1` with a provider contract
   (`trustLevel`, `verified`) plus optional `license` and `sync` metadata for
   signed offline licenses and online entitlement sync caches.
3. Kept `XCNT-P` as a private Git-ready local repo under `_HostLocal/XCNT-P`.
4. Added installer and publishing docs for paying clients:
   - `_HostLocal/XCNT-P/INSTALL.md`
   - `_HostLocal/XCNT-P/docs/PUBLISHING.md`
5. Documented public commercialization rules in
   `Modules/XUUnity/utilities/module_commercialization.md`.

Acceptance:

- existing local pack structure remains valid
- commercial license backend changes entitlement provider, not pack layout
- installer docs describe private Git/package installation without exposing
  private content through public XUUnity

Phase 5 verification:

- local private repo commit contains the paid pack and installer docs
- `xuunity.entitlements.v1` still accepts `features[]` as the resolver contract
- commercial modes use `signed_offline` or `online_sync` provider inputs
- no hosted license backend or private Git remote is required for the public
  support layer to remain valid

## Validation Plan

Required automated tests:

- valid module root resolves
- missing `module.json` is reported
- invalid schema version fails
- pack path escaping root fails
- missing entitlement locks pack
- personal entitlement loads pack
- resolved registry writes to user cache
- project-root write is rejected by default
- report reference mode hides private content
- `rollsync` statuses are stable
- `session-plan` loads enabled packs from `loadedPacks`
- `session-plan` continues with public core when a matching private pack is absent
- `session-plan` continues with public core when a matching private pack is locked
- session report references contain pack ids only, not private paths or bodies
- `xuunity_module_status` redacts private paths and entrypoints
- `xuunity_module_rollsync` redacts private paths and entrypoints

Required manual checks:

- run `module_registry_tool.py rollsync` with no config
- run with configured local `XCNT-P`
- run with missing entitlement
- run with one invalid pack path
- run `module_registry_tool.py session-plan` with configured local `XCNT-P`
- run `module_registry_tool.py xuunity_module_status` with configured local
  `XCNT-P`
- run `module_registry_tool.py xuunity_module_rollsync` with configured local
  `XCNT-P`
- run system health review and confirm private module overlay status is included

Completed automated verification:

- unit tests cover all required automated tests above
- test count on completion: `14`

Completed manual verification:

- no-config Rollsync returns `not_configured`
- configured local `XCNT-P` Rollsync returns `ready`
- missing entitlement returns `locked`
- invalid pack path returns `invalid`
- configured local `XCNT-P` session-plan returns `private_pack_loaded`
- `xuunity_module_status` returns redacted loaded/locked/invalid sections
- `xuunity_module_rollsync` returns redacted loaded/locked/invalid sections
- system health review contains the `Private Module Overlay Status` template

## Risks

- Accidental project contamination if resolved registry writes to project output.
  Mitigation: user-cache default and explicit export policy.
- Hidden dependency on private pack behavior in company work.
  Mitigation: reports cite pack id only; project memory should not copy private
  rules unless intentionally public-safe and rewritten.
- Loader complexity grows into a package manager.
  Mitigation: first pass supports explicit local paths only.
- Commercial licensing assumptions leak into personal workflow.
  Mitigation: keep `personal_dev` simple and isolated.

## Next Chat Implementation Prompt

Use this prompt to start implementation:

```text
Implement Phase 1 from Design/XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md.

Scope:
- add public schemas under Modules/XUUnity/schemas/
- add Modules/XUUnity/scripts/module_registry_tool.py
- discover registered module roots under host AIModules/
- allow symlinked AIModules module roots when they contain module.json
- filter modules by protocolScopes so non-XUUnity modules remain visible but ignored
- support scan, validate, resolve, rollsync, doctor
- default resolved registry output to ~/.xuunity/cache/resolved_modules/
- add focused tests with temporary fake module roots
- update Modules/XUUnity/utilities/system_health_review.md with Private Module Overlay Status

Do not create or commit real XCNT-P paid content.
Do not write resolved private-module state into the project repo by default.
Keep all examples fake/public-safe.
```
