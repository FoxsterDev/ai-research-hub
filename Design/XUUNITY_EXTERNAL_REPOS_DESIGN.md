# XUUnity External Repos Design

## Goal
Describe an optional extension model where `XUUnity` can compare with or promote to external repositories without making them part of the canonical runtime architecture.

## Current Policy
- public `AIRoot/Modules/XUUnity/` is the canonical reusable core
- `AIModules/XUUnityInternal/` is the monorepo-internal shared overlay when the host repo provides it
- external repos are optional and disabled by default
- `external_repo_test_1` is a placeholder name for future experiments
- no active submodule binding should be required for this design

## Design Rules
- external repos never override the public `XUUnity` core or the internal shared overlay
- project memory still overrides shared prompts
- external integrations must remain opt-in
- transport is an implementation detail, not an architecture contract

## Vocabulary
- `external repo`
- `external source`
- `public core`
- `internal shared`
- `promote to public core only`
- `promote to external only`
- `promote to both public core and external`

## Notes
Keep this capability dormant until there is a concrete need to re-enable it.
