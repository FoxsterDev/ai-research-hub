# Refactoring Routing

## Base Rule
If refactoring-related signals are present, load:
- `behavior_preservation.md`

Prefer refactoring signals when the task is about:
- extracting a service, wrapper, presenter, facade, or explicit seam
- splitting a large class or separating responsibility clusters
- decoupling ownership, state mutation, orchestration, or vendor/platform boundaries
- staged migration with thin adapters or temporary dual-path support
- replacing broad global access with narrower explicit contracts

Prefer `skills/architecture/` instead when the task is primarily about:
- choosing the target subsystem split
- deciding long-term ownership or event-flow design
- comparing architecture options before migration starts
- defining whether a boundary should exist, not how to migrate toward it safely

Then refine:
- `incremental_migration.md` for staged rollouts, monolith splitting, strangler-style migration, or adapter-backed transitions
- `dependency_seams.md` for service extraction, SDK or platform isolation, wrapper design, or test seams
- `presenter_lifetime_split.md` for screen, popup-flow, or scene-root lifetime separation in UI-heavy games
- `progression_snapshot_reconciliation.md` for optimistic progression UI, authoritative snapshot pruning, or quest/state reconciliation cleanup
- `reward_grant_idempotency.md` for rewarded-ad, prize-claim, or duplicate-grant protection work
- `startup_bridge_narrowing.md` for startup consent, permission, or native request ownership cleanup
- `state_stream_simplification.md` for reducer ownership, replay-on-subscribe removal, or monitor-style state service cleanup

## Composition Hints
Refactoring usually composes with:
- `skills/core/critical_flow_protection.md` when startup, save/load, rewards, ads, IAP, or session-sensitive flows are touched
- `skills/architecture/` when the change moves ownership or subsystem boundaries
- `skills/async/` when the refactor changes callback ordering, cancellation ownership, or failure propagation
- `skills/native/` or `skills/sdk/` when the seam is around platform or vendor code
- `skills/tests/` when regression protection is needed before deleting the old path

Do not load refactoring by default for:
- pure bug fixes with a local minimal-diff answer
- generic review work with no structural-change proposal
- pure profiling or allocation tuning with no migration or seam work
- trivial cleanup such as rename, formatting, comments, or file moves

## Mandatory Rule
If the task is routed to refactoring, the implementation or review is incomplete without the refactoring skill layer.
