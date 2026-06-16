# XUUnity Utility: Module Rollsync

## Goal
Provide a repeatable health gate for optional private/paid modules before a session routes through them.

## Command
```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py rollsync --project-root ..
```

## Status Meanings
- `ready`: at least one private pack is loaded and no warnings were reported.
- `ready_with_warnings`: at least one private pack is loaded, with non-blocking warnings.
- `locked`: packs were discovered but entitlements are missing.
- `invalid`: a module or pack manifest failed validation, an entrypoint is missing, or the requested output path would write resolved private state outside the user cache.
- `not_configured`: no usable private pack was discovered.

## Session Routing
Run Rollsync when:
- the user asks to use private, paid, premium, or local-only modules
- the task text may match a loaded private pack trigger
- the private module symlink, entitlement, or pack manifest changed
- a previous resolved registry is missing or stale

After Rollsync:
- load only `loadedPacks[]`
- do not load `lockedPacks[]` or `invalidPacks[]`
- record matched pack ids in the execution contract as `matched_private_packs`
- keep private paths user-local and avoid quoting private content in final reports
- use `session-plan` when you need a private-runtime loading contract, then copy
  only its `sessionContract.private_pack_report_references` into reports

## Game QA Smoke
For Game QA paid routing, prove the route with:
```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py route-smoke \
  --project-root .. \
  --task-text "validate ui after a fix with PlayMode smoke" \
  --require-capability xuunity.game_qa.runtime_ui_validation \
  --expect-pack xcntp.game_qa_paid_skill
```

Public routing should require capabilities such as
`xuunity.game_qa.runtime_ui_validation`; the local smoke may still assert the
canonical first pack id. The smoke should show entrypoints rooted at the
resolved private module and must not show public `Modules/XUUnity/skills/game_qa`
paths.

## Session Plan
For normal session startup, prefer:
```sh
python3 Modules/XUUnity/scripts/module_registry_tool.py session-plan \
  --project-root .. \
  --task-text "validate ui after a fix with PlayMode smoke" \
  --require-capability xuunity.game_qa.runtime_ui_validation
```

Use `matchedLoadedPacks[]` for prompt stack loading. Use
`sessionContract.private_pack_report_references` for reports.
