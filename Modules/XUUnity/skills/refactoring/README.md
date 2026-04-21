# XUUnity Refactoring Skills

## Purpose
Use `skills/refactoring/` for behavior-preserving structural changes in Unity mobile code.
Load it when the task is about refactoring, cleanup, extraction, decoupling, legacy untangling, or incremental migration.

## Provenance
This family is a refactoring-focused composition layer built from already established XUUnity rules and distilled from internal review artifacts covering:
- startup consent and native bridge hardening
- presenter lifetime extraction across screens, one-shot flows, and scene roots
- live state-wrapper contract simplification and ownership cleanup

Core dependencies:
- `skills/core/mobile_runtime_safety.md`
- `skills/core/zero_crash_zero_anr.md`
- `skills/core/critical_flow_protection.md`
- `skills/architecture/dependency_boundaries.md`
- `skills/architecture/state_management.md`
- `skills/async/base_async_rules.md`
- `skills/native/bridge_contracts.md`
- `skills/native/ownership.md`
- `skills/sdk/wrapper_design.md`
- `skills/optimization/allocation_control.md`
- `skills/tests/integration_tests.md`

## Routing
Always start with:
- `behavior_preservation.md`

Then add only the needed topic files:
- `incremental_migration.md`
- `dependency_seams.md`
- `presenter_lifetime_split.md`
- `progression_snapshot_reconciliation.md`
- `reward_grant_idempotency.md`
- `startup_bridge_narrowing.md`
- `state_stream_simplification.md`

## Composition
Refactoring often composes with:
- `skills/tests/` for regression protection
- `skills/architecture/` for subsystem boundaries
- `skills/async/` for callback or ownership-sensitive flows
- `skills/optimization/` when the refactor targets allocations, loading, or frame stability
