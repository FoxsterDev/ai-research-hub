# XUUnity Utility: Module Commercialization

## Goal
Keep the local paid module layout compatible with future commercial delivery.

## Stable Contract
Do not change pack layout for commercialization:

```text
XCNT-P/
  module.json
  packs/
    <pack-id>/
      pack.json
      role/
      skills/
      reviews/
      utilities/
      tests/
```

Commercialization changes only the entitlement provider. The pack layout and
pack ids stay stable.

## Resolver And Verifier Responsibilities
The public entitlement resolver:
- reads a local entitlement input file
- resolves `features[]` against module and pack manifests
- reports provider `trustLevel` and `verified` facts
- writes the full private-runtime registry only to the user cache

The commercial license verifier is a separate future provider:
- verifies signatures or server state before writing entitlement facts
- may set `trustLevel: signed_offline` or `trustLevel: server_verified`
- may set `verified: true` only after that external check succeeds

The resolver does not implement DRM, signature verification, server sync, or a
hosted license backend.

## Entitlement Provider Modes
Supported source modes:
- `personal_dev`: local personal grants for development. Always report
  `trustLevel: local_flag` and `verified: false`.
- `signed_offline`: provider input from a local signed entitlement file issued
  to a customer.
- `online_sync`: provider input from a locally cached entitlement file refreshed
  by a license service.

The public resolver reads the same `features[]` array for all modes. Signature
verification and online sync are owned by the future license backend or
installer client; the prompt resolver treats the synced entitlement file as
input and reports the provider facts without strengthening them.

## Signed License Shape
Commercial entitlement files should keep the existing
`xuunity.entitlements.v1` schema and add optional `license` metadata:

```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "subject": "customer-or-seat-id",
  "mode": "signed_offline",
  "source": "signed_license",
  "provider": {
    "type": "signed_file",
    "mode": "signed_offline",
    "trustLevel": "signed_offline",
    "verified": true,
    "checkedAtUtc": "2026-06-15T00:00:00Z"
  },
  "features": ["xcntp", "xcntp.game_qa_paid_skill"],
  "license": {
    "licenseId": "lic_xcntp_example",
    "issuer": "XCNT-P",
    "subject": "customer-or-seat-id",
    "issuedAtUtc": "2026-06-15T00:00:00Z",
    "expiresAtUtc": "2027-06-15T00:00:00Z",
    "signatureAlgorithm": "ed25519",
    "signature": "<backend-issued-signature>",
    "payloadHash": "<canonical-payload-hash>"
  }
}
```

## Online Sync Shape
Online sync should write a local cache with the same schema:

```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "subject": "customer-or-seat-id",
  "mode": "online_sync",
  "source": "license_server_cache",
  "provider": {
    "type": "server_cache",
    "mode": "online_sync",
    "trustLevel": "server_verified",
    "verified": true,
    "checkedAtUtc": "2026-06-15T00:00:00Z"
  },
  "features": ["xcntp", "xcntp.game_qa_paid_skill"],
  "sync": {
    "mode": "online",
    "server": "https://license.example.invalid",
    "lastSyncAtUtc": "2026-06-15T00:00:00Z",
    "nextSyncAfterUtc": "2026-06-16T00:00:00Z"
  }
}
```

Do not put license-server secrets, customer secrets, or private keys in public
XUUnity files.

## Private Git Or Package Distribution
XCNT-P can be published as:
- a private Git repo mounted through `AIModules/XCNT-P`
- a private package downloaded by an installer into a local module root
- a customer-local folder referenced by `XUUNITY_MODULE_PATHS`

The public support layer should not care which transport installed the module.
After installation, `module_registry_tool.py rollsync` is the compatibility gate.

## Installer Manifest
Commercial distribution may include a machine-readable `installer.json`:

```json
{
  "schemaVersion": "xuunity.installer.v1",
  "moduleId": "xcntp",
  "recommendedMount": "AIModules/XCNT-P",
  "requiredFeatures": ["xcntp", "xcntp.game_qa_paid_skill"],
  "postInstallChecks": ["xuunity_module_status", "xuunity_module_rollsync"]
}
```

Validate installer metadata without reading private pack bodies:

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py validate-installer \
  --installer <path-to-installer.json>
```

## Installer Requirements
A customer installer should:
1. install or update the private module folder
2. create or refresh the `AIModules/XCNT-P` symlink or user config path
3. write the customer entitlement cache to `~/.xuunity/entitlements.json`
4. validate `installer.json` when present
5. run `xuunity_module_rollsync`
6. show only redacted status output

## Pack Review Gate
Before publishing a paid/private pack, run
`Modules/XUUnity/reviews/module_pack_review.md`. The review must reference pack
ids and capability ids only; it must not copy private skill bodies, private
absolute paths, entitlement file paths, or entrypoint lists.

## Publish Readiness Checklist
- `module.json` validates
- every `pack.json` validates
- entrypoints exist
- capability tags are present for public routing
- `module_pack_review.md` has a `ready` verdict or explicit follow-up findings
- installer metadata validates when commercial distribution needs it
- `xuunity_module_status` redacts paths and entrypoints
- `xuunity_module_status` reports provider `trustLevel` without exposing
  entitlement file paths
- `xuunity_module_rollsync` reports `ready` for an entitled install
- installer docs do not expose private prompt bodies outside the paid package
