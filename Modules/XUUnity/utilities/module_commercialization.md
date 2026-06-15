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

Commercialization changes only the entitlement source.

## Entitlement Modes
Supported source modes:
- `personal_dev`: local personal grants for development.
- `signed_offline`: a local signed entitlement file issued to a customer.
- `online_sync`: a locally cached entitlement file refreshed from a license service.

The public resolver reads the same `features[]` array for all modes. Signature
verification and online sync are owned by the future license backend or installer
client; the prompt resolver treats the synced entitlement file as input.

## Signed License Shape
Commercial entitlement files should keep the existing
`xuunity.entitlements.v1` schema and add optional `license` metadata:

```json
{
  "schemaVersion": "xuunity.entitlements.v1",
  "subject": "customer-or-seat-id",
  "mode": "signed_offline",
  "features": ["xcntp", "xcntp.game_qa_paid_skill"],
  "source": "signed_license",
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
  "features": ["xcntp", "xcntp.game_qa_paid_skill"],
  "source": "license_server_cache",
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

## Installer Requirements
A customer installer should:
1. install or update the private module folder
2. create or refresh the `AIModules/XCNT-P` symlink or user config path
3. write the customer entitlement cache to `~/.xuunity/entitlements.json`
4. run `xuunity_module_rollsync`
5. show only redacted status output

## Publish Readiness Checklist
- `module.json` validates
- every `pack.json` validates
- entrypoints exist
- `xuunity_module_status` redacts paths and entrypoints
- `xuunity_module_rollsync` reports `ready` for an entitled install
- installer docs do not expose private prompt bodies outside the paid package
