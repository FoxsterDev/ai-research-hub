# XUUnity Review: Module Pack Review

## Goal
Review an optional private/paid XUUnity pack before publication or customer
distribution without copying private pack bodies into public XUUnity, company
repos, or review artifacts.

## Inputs
- `module.json` manifest metadata
- `pack.json` manifest metadata
- redacted `xuunity_module_status` or `xuunity_module_rollsync` output
- optional `validate-installer` output when an installer manifest exists
- pack id and capability ids supplied by the package owner

Do not request or paste private skill bodies, private review checklist text,
private absolute paths, local entitlement file paths, or entrypoint lists into
the review output.

## Checks
- Manifest validity: `module_registry_tool.py validate` passes for the mounted
  private module.
- Path safety: pack paths and entrypoints stay inside the pack root, and
  resolved registries are written only to the user cache.
- Private/public boundary: public docs contain only generic examples,
  capability ids, pack ids, and report references.
- Report redaction: company/public artifacts cite only
  `Private pack used: <pack id>`.
- Entitlement feature stability: module feature and pack `licenseFeature` are
  stable, lowercase ids and are not renamed for marketing.
- Capability tags: `pack.json` exposes stable capabilities for public routing,
  and public policy can route by capability rather than by product pack id.
- Customer install readiness: installer metadata exists when distribution needs
  machine-readable setup, and `validate-installer` passes.
- MCP/API boundary: `xuunity_module_status` and `xuunity_module_rollsync`
  expose trust level and status without private paths or entrypoints.

## Output
Use this shape:

```md
**Module Pack Review**
- `pack_id`: `<pack id>`
- `display_name`: `<display name>`
- `capabilities`: `<capability id list or none>`
- `manifest_status`: `passed` | `failed` | `not_run`
- `path_safety`: `passed` | `failed` | `not_run`
- `redaction_status`: `passed` | `failed` | `not_run`
- `entitlement_status`: `passed` | `failed` | `not_run`
- `installer_status`: `passed` | `failed` | `not_applicable` | `not_run`
- `publishing_verdict`: `ready` | `blocked` | `needs_followup`
- `report_references`:
  - `Private pack used: <pack id>`
- `findings`:
  - `<finding or none>`
```

## Boundary
Review output is `company_report` safe only when it contains pack ids,
capability ids, counts, statuses, and report references. If a finding requires
private file evidence, describe the manifest field or check name, not the
private content or absolute path.
