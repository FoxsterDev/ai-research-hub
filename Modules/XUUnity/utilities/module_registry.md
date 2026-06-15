# XUUnity Utility: Module Registry

## Goal
Discover optional host-local modules without committing private paid content into the public `AIRoot` repo or the active product repo.

## Discovery Contract
- Primary discovery root: `<host-root>/AIModules/`.
- A module may be a real directory or a symlink.
- A module is registered only when its resolved root contains `module.json`.
- Unregistered roots are reported but not crawled.
- Registered modules must declare `protocolScopes`; `xuunity` and `universal` are eligible for this protocol.
- Private modules must keep `exportPolicy.mayCommitToHostRepo: false`.

## Commands
Use `Modules/XUUnity/scripts/module_registry_tool.py`.

Common commands:
- `scan`: list visible module roots and registration status.
- `validate`: validate module and pack manifests without loading locked content.
- `resolve`: build a resolved registry of loaded, locked, and invalid packs.
- `doctor --pack-id <id>`: explain why a pack is loaded, locked, invalid, or missing.

Example:
```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py scan --project-root ..
```

## Entitlements
The default entitlement file is `~/.xuunity/entitlements.json`.

Minimum local shape:
```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "mode": "local_personal",
  "features": [
    "xcntp",
    "xcntp.game_qa_paid_skill"
  ]
}
```

Entitlements are user-local. Do not write them into the project repo.

## Resolved Registry
The resolved registry is written to `~/.xuunity/cache/resolved_modules/<project-hash>.json` by default.

Consumers should read:
- `loadedPacks[]` for packs that may be used
- `lockedPacks[]` for packs discovered but unavailable to the current user
- `invalidPacks[]` for packs blocked by manifest or entrypoint validation

Do not infer private module paths outside the resolved registry.
