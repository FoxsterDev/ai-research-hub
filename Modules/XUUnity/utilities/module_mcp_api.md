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
- status counts
- loaded, locked, and invalid pack status
- entitlement mode, source label, and feature count
- report references such as `Private pack used: xcntp.game_qa_paid_skill`

Tool output must not include:
- private file contents
- private entrypoint paths
- private module absolute paths
- user-local entitlement file paths
- resolved registry file paths

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
