# XUUnity Utility: Paid Skill Authoring

## Goal
Create a new paid/private XUUnity skill pack in a repeatable way, without
copying private content into public `AIRoot` or a company project repo.

Use this when adding a new paid skill such as:
- a Game QA pack
- a review discipline pack
- a project automation planning pack
- a premium knowledge/utility pack

## Mental Model
There are three layers:

1. Public support layer
   - lives in `AIRoot/Modules/XUUnity`
   - contains schemas, registry tooling, Rollsync, session routing, redacted API
   - never contains paid skill bodies

2. Private module repo
   - example: `XCNT-P`
   - contains `module.json`
   - contains one or more paid packs under `packs/<pack_slug>/`

3. User-local activation
   - mount private module through `AIModules/<ModuleName>` or `XUUNITY_MODULE_PATHS`
   - grant features in `~/.xuunity/entitlements.json`
   - run Rollsync and session-plan

## Folder Shape

Recommended private module shape:

```text
XCNT-P/
  module.json
  README.md
  INSTALL.md
  packs/
    my_paid_skill/
      pack.json
      README.md
      role/
        my_paid_brain.md
      skills/
        my_paid_skill/
          routing.md
          main_skill.md
      reviews/
        my_paid_review_gate.md
      utilities/
        my_paid_usage.md
      tests/
        manifest_validation_cases.json
```

## Creation Steps

1. Pick stable ids.

Use lowercase ids:
- module id: `xcntp`
- pack id: `xcntp.my_paid_skill`
- license feature: `xcntp.my_paid_skill`

Do not rename ids casually after the pack is used. Display names can change;
ids should remain stable.

2. Create or reuse a private module root.

For local development:

```sh
mkdir -p ../_HostLocal/XCNT-P
ln -s ../_HostLocal/XCNT-P ../AIModules/XCNT-P
```

The host repo should ignore both `_HostLocal/` and the personal symlink unless
the host intentionally tracks the private module reference.

3. Copy templates.

Use:

```text
Modules/XUUnity/scripts/templates/paid_module_skill/
```

Replace template tokens:

```text
{{MODULE_ID}}
{{MODULE_DISPLAY_NAME}}
{{MODULE_MOUNT_NAME}}
{{MODULE_VERSION}}
{{PACK_ID}}
{{PACK_DISPLAY_NAME}}
{{PACK_SLUG}}
{{LICENSE_FEATURE}}
{{CAPABILITY_ID}}
{{TRIGGER_TEXT}}
{{ROLE_FILE}}
{{SKILL_FOLDER}}
{{PRIMARY_SKILL_FILE}}
{{REVIEW_FILE}}
{{UTILITY_FILE}}
```

4. Add installer metadata when the pack may be distributed.

Use `installer.json.template` and validate it before sharing installer docs:

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py validate-installer \
  --installer <private-module-root>/installer.json
```

5. Add private entrypoint files.

The loader does not crawl directories. Every file that should be loaded by a
session must be declared in `pack.json` under `entrypoints`.

6. Add routing triggers and capabilities.

Use triggers for human task text and capabilities for stable public routing.

Example capability:

```text
xuunity.game_qa.runtime_ui_validation
```

7. Grant local entitlement.

Edit `~/.xuunity/entitlements.json`:

```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "subject": "local-seat",
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
    "xcntp.my_paid_skill"
  ]
}
```

8. Validate and sync.

From `AIRoot`:

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py validate --project-root ..
python3 Modules/XUUnity/scripts/module_registry_tool.py rollsync --project-root ..
python3 Modules/XUUnity/scripts/module_registry_tool.py xuunity_module_status --project-root ..
```

9. Prove session routing.

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py session-plan \
  --project-root .. \
  --task-text "{{TRIGGER_TEXT}}" \
  --require-capability "{{CAPABILITY_ID}}"
```

Expected:
- `status: private_pack_loaded`
- `matched_private_packs` includes the new pack id
- `private_pack_report_references` contains only `Private pack used: <pack id>`

10. Add a route smoke for the first trigger.

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py route-smoke \
  --project-root .. \
  --task-text "{{TRIGGER_TEXT}}" \
  --require-capability "{{CAPABILITY_ID}}" \
  --expect-pack "{{PACK_ID}}"
```

11. Run the pack review gate before publishing.

Use `Modules/XUUnity/reviews/module_pack_review.md`. The review output must
reference pack ids and capability ids only; do not paste private bodies,
absolute paths, entitlement paths, or entrypoint lists.

12. Keep reports redacted.

Company/public reports may say:

```text
Private pack used: {{PACK_ID}}
```

They must not include:
- private skill bodies
- private review checklist bodies
- private absolute paths
- private entrypoint lists
- local entitlement paths

## How It Works At Session Time

1. `start_session.md` loads public XUUnity.
2. The session checks the resolved registry or runs Rollsync when paid/private
   modules are requested.
3. The registry discovers module roots under `AIModules/` and explicit module
   paths.
4. The registry validates `module.json` and declared `pack.json` files.
5. Entitlements decide whether a pack is `loaded`, `locked`, or `invalid`.
6. `session-plan` matches the task text against loaded pack routing triggers.
7. Only matched `loadedPacks[]` entrypoints are eligible for prompt loading.
8. Project memory remains the final project-specific truth.
9. Reports copy only redacted pack references.

## Done Criteria For A New Paid Skill

- `module.json` exists and validates
- `pack.json` exists and validates
- every declared entrypoint exists
- local entitlement grants module and pack features
- `rollsync` reports `ready`
- `xuunity_module_status` reports the pack without private paths
- `session-plan` reports `private_pack_loaded` for a representative task and
  required capability
- `route-smoke` passes for the first trigger and canonical pack id
- `module_pack_review.md` reaches a publishable verdict before distribution
- `validate-installer` passes when an installer manifest is present
- company/public output contains only pack id references

## Common Mistakes

- Putting private skill files under public `AIRoot/Modules/XUUnity/skills/`.
- Relying on folder crawling instead of declaring entrypoints.
- Forgetting to add both module-level and pack-level feature ids.
- Copying private checklist text into a company report.
- Treating `personal_dev` as a commercial license.
- Renaming pack ids after they have appeared in entitlements.
