# XUUnity Utility: Module Session Routing

## Goal
Turn the resolved private module registry into a safe session prompt stack.

## Command
```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py session-plan --project-root .. --task-text "<task text>"
```

## Rules
- Use only `matchedLoadedPacks[]` as private prompt-stack input.
- Treat `matchedLockedPacks[]` and `matchedInvalidPacks[]` as explanations only.
- If no private pack is loaded, continue with public XUUnity core and project routing.
- Load private packs after public XUUnity core and before project memory.
- Do not guess private pack paths outside the resolved registry.

## Execution Contract
Copy only these public-safe fields into a session execution contract:
- `matched_private_packs`
- `private_pack_report_references`
- `private_content_report_policy`
- `private_paths_user_local_only`
- `continue_without_private_pack`

`private_pack_report_references` is the only text that should be copied into
company or public reports.

## Report Boundary
Allowed:
```text
Private pack used: xcntp.game_qa_paid_skill
```

Not allowed in company/public output:
- private skill bodies
- private review checklist bodies
- private module absolute paths
- private pack entrypoint lists
- user-local entitlement paths
