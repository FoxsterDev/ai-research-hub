# Skill: Progression Snapshot Reconciliation

## Derived From
- reviewed optimistic progression-state reconciliation artifact

## Use For
- progression or quest-state refactors
- mission, collection, or home-surface reconciliation cleanup
- save-backed or server-backed local cache cleanup

## Rules
- When UI moves optimistically ahead of authoritative progression state, guard follow-up actions until fresh truth arrives or an explicit fallback expires.
- Match temporary blocking scope to reconciliation scope; item-scoped updates should not become full-screen lockouts by default.
- Full snapshot reconciliation must prune locally cached entities that are missing from the fresh authoritative snapshot.
- Derive section visibility and re-interaction from current filtered visible state, not stale constructor defaults or cached availability flags.
- Keep fallback timers and cancellation ownership in orchestration code, while item or collection models own local action-state mutation rules.
