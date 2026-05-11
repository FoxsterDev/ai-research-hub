# XUUnity Review Policy Pack: Save/Load Changes

## Goal
Strengthen the review and validation stack for save/load and persistence-sensitive work where serialization, migration, restore, merge, or overwrite mistakes can cause data loss, duplicated state, corrupted progression, silent fallback, or release-visible regressions.

## Trigger When
- the task changes save, load, restore, reset, clear-data, import, export, backup, or persistence lifecycle behavior
- the task changes persisted schema, serialized field shape, DTO shape, default values, versioning, compatibility, or migration code
- the task changes cache, local, remote, server-backed, cloud-save, or offline-state ownership
- the task changes startup restore, resume restore, scene-entry hydration, session recovery, or low-memory/background save behavior
- the task changes partial-update, patch, merge, conflict resolution, stale-write, dirty-state, or last-writer behavior
- the task changes progression, inventory, currency, entitlement, account, settings, or other user-owned state that must survive app restarts

## Primary Risk Signals
- no single owner is responsible for the persistence unit, restore contract, merge boundary, and write timing
- a schema change assumes old persisted data cannot exist without evidence from released builds or migration history
- absent fields, explicit null/default values, and intentionally cleared values are collapsed into the same meaning
- local cache, remote truth, startup defaults, and runtime overrides can overwrite each other without an explicit precedence rule
- save writes can happen during startup restore, backgrounding, low-memory, logout, account switch, scene change, or failed network sync
- destructive reset, clear-data, migration retry, or fallback load can erase valid user state without confirmation or backup semantics
- corruption, partial write, missing file, stale file, version mismatch, or malformed payload paths silently fall back as if they were valid new-user state

## Mandatory Stack Additions
- `knowledge/decision_rules.md`
- `skills/core/critical_flow_protection.md`
- `skills/core/mobile_runtime_safety.md` when mobile pause, resume, low-memory, backgrounding, or interruption can affect persistence
- `skills/mobile/lifecycle_boundaries.md` when save-on-background, restore-on-resume, app lifecycle, or platform-specific persistence timing is relevant
- `skills/mobile/lifecycle_boundary_review.md` when reviewing lifecycle-facing save ownership or runtime service contracts
- `skills/architecture/state_management.md` when mutable state ownership, derived availability, or runtime transition rules are part of the change
- `skills/refactoring/progression_snapshot_reconciliation.md` when save-backed or server-backed progression, inventory, mission, collection, or local cache reconciliation changes
- `skills/async/` when persistence depends on async file IO, remote sync, cancellation, retries, callbacks, or delayed writes
- `skills/tests/smoke_and_release_checks.md` when release confidence depends on startup, restore, resume, offline, interruption, or real-device save/load smoke coverage
- `reviews/feature_code_review.md` for implementation or diff review of changed persistence behavior
- `reviews/release_readiness_review.md` when migration, compatibility, user-owned state, destructive reset, rollout, or ship-readiness is part of the task

## Main Review Questions
- What is the exact persistence unit, and which owner is authoritative for reading, mutating, writing, migrating, restoring, and clearing it?
- What is the compatibility envelope: which released versions, platforms, accounts, or stored payload shapes can realistically exist?
- Where is the serialization boundary, and does the code preserve enough raw information to distinguish absent fields from explicitly set fields when partial-update semantics require it?
- What is the merge boundary between startup defaults, local persisted state, cached state, remote truth, runtime config, and user actions?
- Which write wins after offline edits, remote refresh, startup restore, retry, account switch, logout, backgrounding, or low-memory save signals?
- What happens when data is missing, corrupt, partial, stale, newer-than-supported, older-than-supported, or only partly migrated?
- Can fallback, migration retry, reset, clear-data, or failed load silently erase valid state or hide a production data-loss bug?

## Required Evidence
- the persistence entry points touched, including serializers, deserializers, repositories, storage adapters, lifecycle save triggers, restore callers, migration paths, and reset or clear-data paths
- the current persistence unit, ownership boundary, storage backend, file or key shape, version field, schema or DTO shape, and migration or compatibility history
- explicit evidence for whether older persisted data can exist in released environments before adding or deleting compatibility branches
- field-semantics evidence for omitted fields, explicit defaults, nulls, empty collections, cleared values, and unknown fields
- merge evidence for local/cache/remote/default precedence, dirty-state tracking, conflict handling, stale-write prevention, and runtime override boundaries
- failure evidence for missing data, corrupt data, partial writes, failed writes, failed migrations, unavailable remote state, account/session changes, and destructive reset behavior
- validation evidence for first install, upgrade, downgrade or unsupported-newer data if relevant, corrupt payload, missing payload, stale cache, offline, resume, background save, and clear-data paths proportional to risk

## Validation Focus
- restore loads the correct existing state without replacing it with startup defaults or stale cache
- migration transforms older valid payloads exactly once and preserves user-owned fields
- absent field, explicit default, explicit clear, and unknown-field cases follow the intended merge semantics
- corrupt, partial, missing, or unsupported data fails safely with visible diagnostics or controlled degraded behavior instead of silent destructive fallback
- local and remote merges preserve the authoritative source for each field and do not resurrect deleted state or overwrite fresh state with stale state
- save triggers are idempotent and bounded during pause, focus loss, low-memory, scene change, app quit, logout, and account switch
- destructive reset and clear-data paths are deliberate, scoped, and unable to run accidentally during ordinary restore, migration, retry, or fallback handling
- runtime validation exercises real serialization and restore paths when mocks or in-memory fakes cannot prove persisted compatibility

## Common Failure Modes
- migration code treats every missing field as a new default and overwrites an intentional legacy or remote value
- early deserialization into a concrete object loses the distinction between field absence and explicit field value before the merge boundary
- save-on-startup writes defaults before restore finishes, permanently replacing real user state
- late async save writes an old snapshot after a newer remote refresh, account switch, logout, or scene transition
- fallback load silently starts a new profile after corruption, partial write, missing file, or parse failure without preserving recovery evidence
- compatibility code supports impossible legacy shapes while missing the real released payload shape
- clear-data, reset, or migration retry deletes more storage than the intended persistence unit
- cached progression, inventory, entitlement, or settings state is not pruned or reconciled against the authoritative snapshot
- low-memory or background save runs heavy repeated writes without dirty-state gating or repeated-call suppression

## Release-Risk Framing
- Treat irreversible data loss, currency/progression corruption, entitlement loss, account-state corruption, or destructive reset exposure as release-blocking until disproven.
- Treat silent fallback to default state as high risk when it can hide corruption, migration failure, restore failure, or remote-sync failure from users and diagnostics.
- Treat schema or migration changes as release-sensitive only within the compatibility envelope that can actually exist; do not add broad legacy burden without evidence, but do not delete real compatibility paths without proof.
- Treat mock-only validation as incomplete when correctness depends on real serialization, platform storage, lifecycle save timing, cloud/offline sync, or app restart behavior.
- Treat rollout-guarded persistence changes as production-sensitive because even a small exposed population can suffer irreversible state loss.

## Co-loading Rule
- Prefer this pack as the primary pack when persistence ownership, serialization boundaries, migrations, startup restore, cache/local/remote merge behavior, stale writes, destructive reset, or save/load compatibility is the main breakage surface.
- If the same change is mainly startup, UI-heavy, monetization, SDK, manifest/native, or store behavior, keep the dominant pack primary and load only the save/load additions needed for persistence correctness.
- Do not use this pack for generic state management, generic DTO cleanup, or non-persisted runtime-only refactors unless the changed behavior can affect stored state, restore behavior, compatibility, user-owned data, or destructive reset safety.

## Final Review Must Report
- the persistence surfaces touched and the dominant risk family
- the active policy pack and trigger reasons
- the persistence unit, serialization boundary, storage backend, restore owner, write owner, migration owner, and clear/reset owner
- the compatibility envelope and evidence for which old, new, missing, corrupt, or remote payload shapes can exist
- the merge boundary, partial-update semantics, absent-versus-explicit field behavior, and local/cache/remote/default precedence
- validation performed and validation still missing, especially migration, corrupt data, missing data, startup restore, resume/background save, stale write, offline/remote merge, and destructive reset coverage
- release-risk classification for data loss, data corruption, duplicated state, stale state, silent fallback, compatibility drift, and user-owned state recovery

## Rule
- Compose existing shared reviews, skills, and decision rules. Do not duplicate full architecture, lifecycle, async, testing, or release-readiness protocols here.
