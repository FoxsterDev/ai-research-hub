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
- Do not mix relative and absolute application of the same value. When the response carries the absolute post-grant total, applying a relative delta first and assigning the authoritative total afterwards double-counts whenever the balance already reflected the grant — the player watches the counter overshoot and then drain back, which reads as the reward being taken away. Reconcile the authoritative value first and animate from `authoritative - delta` toward it, or let the animation be purely visual and never mutate the balance.
