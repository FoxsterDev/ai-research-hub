# Skill: Incremental Migration

## Use For
- staged subsystem replacement
- splitting large classes
- replacing global access patterns
- adapter-backed transitions

## Rules
- Create a seam first, then move one responsibility at a time.
- Keep old entrypoints as thin adapters until callers are fully migrated.
- Make state ownership and transitions explicit instead of spreading migration state across helpers, flags, and callbacks.
- Delete dead paths only after the new path is the sole owner of behavior.
- Prefer reversible steps over one-shot rewrites on critical flows.
- Validate each migration step against startup, resume, save/load, and monetization-sensitive paths when they are touched.
