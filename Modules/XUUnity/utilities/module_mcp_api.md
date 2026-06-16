# XUUnity Utility: Module MCP/API

## Goal
Expose optional private/paid module state to host-side MCP or other local API
surfaces without exposing private pack content.

## Public Tool Names
The public host-side MCP helper should expose these generic tools:

- `xuunity_module_status`
- `xuunity_module_rollsync`

They map directly to:

```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py xuunity_module_status --project-root <host-root>
python3 Modules/XUUnity/scripts/module_registry_tool.py xuunity_module_rollsync --project-root <host-root>
```

## Redacted Output Contract
Tool output may include:
- pack ids
- module ids
- display names
- capability ids
- status counts
- loaded, locked, and invalid pack status
- entitlement mode, source label, feature count, `trustLevel`, and `verified`
  provider facts
- report references such as `Private pack used: xcntp.game_qa_paid_skill`

Tool output must not include:
- private file contents
- private entrypoint paths
- private module absolute paths
- user-local entitlement file paths
- resolved registry file paths

These tools are `redacted_api` output. They may trigger a private-runtime
registry write to the user cache, but their response body must not expose the
cache path, private module path, entrypoint path, or entitlement file path.

## Provider Trust Contract
Redacted API output reports provider facts from the local entitlement input:
- `trustLevel: local_flag` for `personal_dev`
- `trustLevel: signed_offline` when an external signed-file provider supplied
  that fact
- `trustLevel: server_verified` when an external sync/verifier supplied that
  fact
- `trustLevel: unknown` when the provider did not supply a stronger fact

The resolver does not verify commercial licenses. It reports `verified` exactly
as provider input after local normalization; loading remains feature-based.

## Status Semantics
- `ready`: at least one pack is loaded.
- `ready_with_warnings`: at least one pack is loaded with warnings.
- `locked`: matching packs exist but entitlement is missing.
- `invalid`: manifests, paths, or output policy failed validation.
- `not_configured`: no in-scope private packs are configured.

## Unity Package Boundary
Prompt-only packs do not require Unity Editor package changes. MCP hosts may
wrap the CLI output as a tool response, but Unity package code should remain
unchanged unless a future paid pack provides editor/runtime code.
