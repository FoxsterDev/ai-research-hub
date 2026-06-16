# XUUnity Paid Module First-Principles Fix Plan

Date: 2026-06-15
Status: implemented and validated
Source: first-principles review of `XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md`

## Goal

Turn the current paid-module overlay from a working local architecture into a
commercially safer architecture by fixing the few places where assumptions can
become product debt.

The current implementation is valid for personal use. This plan targets the
next hardening pass.

## First-Principles Baseline

The paid-module architecture should be built only on these truths:

1. Paid value is private content, not the repository, symlink, package manager,
   or license transport.
2. Public XUUnity may know how to discover, validate, and route modules, but it
   must not contain private paid bodies.
3. Company repos must not become dependent on personal paid content.
4. A pack can be loaded only after a resolved registry marks it as loaded.
5. A commercial license is not the same thing as a local entitlement file.
6. Every report/output boundary is a possible leak boundary.
7. Prompt-only packs should not require Unity Editor package changes.
8. Future commercialization should change entitlement provider/source, not pack
   layout.

## Top Fixes

### P0. Add Entitlement Provider Contract

Problem:
The current resolver reads `features[]` and `mode`, but it does not distinguish
between a local development flag and a commercially verified license.

Fix:
Add an explicit entitlement-provider layer to the public contract.

Proposed fields:

```json
{
  "provider": {
    "type": "local_file",
    "mode": "personal_dev",
    "trustLevel": "local_flag",
    "verified": false,
    "checkedAtUtc": "2026-06-15T00:00:00Z"
  }
}
```

Allowed `trustLevel` values:
- `local_flag`
- `signed_offline`
- `server_verified`
- `unknown`

Implementation targets:
- `Modules/XUUnity/schemas/xuunity.entitlements.schema.json`
- `Modules/XUUnity/scripts/module_registry_tool.py`
- `Modules/XUUnity/utilities/module_commercialization.md`
- `Modules/XUUnity/utilities/module_mcp_api.md`

Acceptance:
- personal grants resolve with `trustLevel: local_flag`
- signed/online grants have a place to report stronger trust later
- `xuunity_module_status` exposes trust level in redacted form
- loading behavior remains feature-based for now

### P0. Split Entitlement Resolution From License Verification

Problem:
The resolver currently risks becoming both a prompt loader and a license system.
That would make future commercial licensing hard to change.

Fix:
Define two separate responsibilities:

- `entitlement resolver`: reads local entitlement input and resolves feature ids
- `license verifier`: future external provider that proves entitlement source

The public resolver should not implement DRM. It should consume verified or
unverified entitlement facts and report their trust level.

Implementation targets:
- `module_commercialization.md`
- `module_registry_tool.py` internal naming
- design doc terminology update

Acceptance:
- code and docs do not imply `personal_dev` is a commercial license
- `signed_offline` and `online_sync` remain provider inputs, not loader logic
- future backend can replace only the provider, not the pack layout

### P0. Harden Redaction As A Formal Output Boundary

Problem:
Redaction exists, but it is currently distributed across docs and command
behavior. The architecture needs one explicit rule: every non-user-cache output
must be redacted.

Fix:
Classify outputs:

- `private_runtime`: may include absolute private paths and entrypoints
- `redacted_api`: pack ids, capability ids, counts, status, report references,
  and entitlement provider trust facts only
- `company_report`: pack id references only
- `public_doc`: generic examples only

Implementation targets:
- `module_registry_tool.py`
- `module_mcp_api.md`
- `module_session_routing.md`
- `report_export.md`
- `system_health_review.md`

Acceptance:
- `resolve` may write private paths only to user cache
- `xuunity_module_status` and `xuunity_module_rollsync` never output private
  paths, entrypoints, or entitlement file paths
- `session-plan` clearly marks entrypoint output as session-private, not report
  safe
- tests assert no private path fragments in redacted API output

### P1. Replace Hardcoded Product Pack Names In Public Routing With Capability Tags

Problem:
Public files currently mention `xcntp.game_qa_paid_skill` in some routing and
policy contexts. That is acceptable for the first local pack, but it couples
public XUUnity to one private product name.

Fix:
Add capability tags to `pack.json` routing and match capabilities in public
rules.

Example:

```json
{
  "capabilities": [
    "xuunity.game_qa.runtime_ui_validation",
    "xuunity.game_qa.playmode_smoke_planning"
  ]
}
```

Public docs should prefer capabilities; local smoke tests may still assert the
actual pack id.

Implementation targets:
- `xuunity.pack.schema.json`
- private `XCNT-P/packs/game_qa_paid_skill/pack.json`
- `module_registry_tool.py`
- `start_session.md`
- `ui_heavy_changes.md`

Acceptance:
- public routing can say "load a pack with capability X"
- local tests still prove `xcntp.game_qa_paid_skill` satisfies capability X
- adding a second paid Game QA pack does not require rewriting public policy
  files

### P1. Normalize Naming: Game QA Paid Skill And Marketing Alias

Problem:
The design previously mixed an older Game QA Pro technical id with
`xcntp.game_qa_paid_skill`. Mixed technical ids create product and migration
confusion.

Fix:
Choose one current canonical pack id and one market-facing display name.

Recommended:
- pack id: `xcntp.game_qa_paid_skill`
- display name: `Game QA Paid Skill`
- future marketing alias: `Game QA Pro`

Implementation targets:
- `XUUNITY_PERSONAL_PAID_MODULE_OVERLAY_DESIGN.md`
- `module_commercialization.md`
- private `XCNT-P/README.md`
- private `XCNT-P/INSTALL.md`

Acceptance:
- ids are stable and technical
- display names can evolve without changing entitlements
- all examples use the current pack id consistently

### P1. Add Pack Review Gate Before Publishing

Problem:
The loader validates shape, but it does not review whether a pack is safe to
publish or whether it accidentally contains public/company-sensitive material.

Fix:
Add a public pack review checklist.

Review dimensions:
- manifest validity
- path safety
- private/public boundary
- report redaction
- entitlement feature stability
- capability tags
- customer install readiness

Implementation targets:
- `Modules/XUUnity/reviews/module_pack_review.md`
- `Modules/XUUnity/utilities/module_commercialization.md`
- private `XCNT-P/docs/PUBLISHING.md`

Acceptance:
- every new paid pack has a review route before publication
- review output references pack ids only
- review can run without private pack bodies in public repo

### P2. Add Installer Manifest For Commercial Distribution

Problem:
Installer docs describe what to do, but there is no machine-readable install
manifest for future clients.

Fix:
Add an optional installer manifest.

Example:

```json
{
  "schemaVersion": "xuunity.installer.v1",
  "moduleId": "xcntp",
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

Implementation targets:
- new schema `xuunity.installer.schema.json`
- private `XCNT-P/installer.json`
- `INSTALL.md`

Acceptance:
- future installer can mount and verify the pack without hardcoded assumptions
- public XUUnity can validate installer metadata without private bodies

## Recommended Implementation Order

1. P0 entitlement provider contract. ✓ done
2. P0 entitlement/license responsibility split. ✓ done
3. P0 formal output boundary and redaction test expansion. ✓ done
4. P1 naming normalization. ✓ done
5. P1 capability tags. ✓ done
6. P1 pack review gate. ✓ done
7. P2 installer manifest. ✓ done

## Implementation Status

Completed on 2026-06-15:

- P0 entitlement provider contract with `trustLevel`, `verified`, and
  `checkedAtUtc`.
- P0 resolver/verifier split: the resolver remains feature-based and does not
  implement DRM, hosted licensing, signature verification, or online sync.
- P0 output-boundary hardening: private paths are limited to private-runtime
  and user-cache outputs; MCP/API status output is redacted.
- P1 naming normalization in public design examples:
  `xcntp.game_qa_paid_skill` / `Game QA Paid Skill`.
- P1 capability tags in pack schema, resolver payloads, redacted API output,
  `session-plan`, `route-smoke`, public routing docs, and templates.
- P1 public module pack review gate:
  `Modules/XUUnity/reviews/module_pack_review.md`.
- P2 installer manifest schema and metadata-only validator:
  `xuunity.installer.v1` and `module_registry_tool.py validate-installer`.

Validation evidence:

- `python3 -m unittest Modules.XUUnity.scripts.tests.test_module_registry_tool` — 25 tests, all passing (verified 2026-06-16)
- `python3 -m py_compile Modules/XUUnity/scripts/module_registry_tool.py Modules/XUUnity/scripts/tests/test_module_registry_tool.py`
- JSON parse checks for schema files and paid-module-skill JSON templates.
- Generated paid-module-skill template smoke via the unit suite.

## Historical P0 Implementation Prompt

```text
Implement P0 from Design/XUUNITY_PAID_MODULE_FIRST_PRINCIPLES_FIX_PLAN.md.

Scope:
- add entitlement provider contract with trustLevel and verified fields
- keep personal_dev as trustLevel local_flag
- keep commercial verification outside the resolver
- expose trustLevel through redacted xuunity_module_status and xuunity_module_rollsync
- strengthen output-boundary docs/tests so only user-cache/private-runtime outputs may include private paths

Do not change pack ids.
Do not add a hosted license backend.
Do not touch Unity Editor package code.
Do not commit private paid bodies into AIRoot.
```
