# XUUnity Task: Refactoring

## Goal
Improve structure without changing intended behavior or weakening Unity mobile production safety.

## Invariants
- Do not trade product behavior or public contract stability for structural cleanup.
- Preserve observable product behavior before reducing cognitive load, deleting helpers, or narrowing internals.
- Keep the public interface shape, documented callback semantics, threading contract, and error contract stable unless the task explicitly requires a contract change.

## Focus
- Preserve observable behavior first, especially on startup, resume, save/load, rewards, ads, IAP, and SDK-backed flows.
- Prefer minimal-diff structural cleanup on critical paths unless a larger redesign is required for safety.
- Reduce unsafe lifecycle handling, ownership ambiguity, coupling, duplicated orchestration, or allocation churn.
- Make state ownership, callback ownership, and dependency seams more explicit.
- Keep Unity-facing contracts stable while moving platform, SDK, async, or bridge details behind narrower boundaries.
- On request-shaped native bridges, separate duplicate-in-flight rejection, scheduling failure, and posted-work failure into explicit behavior-preserving paths.
- Prefer operation-specific bridge seams over generic method-name dispatch on critical bridge flows when that improves ownership clarity and testability.
- Remove intermediate methods when they only rename a call without adding a real contract, ownership boundary, or test seam.
- Merge adjacent helpers when splitting them no longer reduces risk and only forces the reader to reconstruct one operation across multiple tiny methods.
- Narrow method signatures to the minimum data and collaborators the callee actually needs so critical-path reading stays local.
- Prefer staged migration, thin adapters, and reversible steps over one-shot rewrites on high-risk flows.
- Do not introduce new waits, blocking work, hidden main-thread stalls, or unhandled exception paths during refactor work.
- Add regression protection where breakage is expensive, especially before deleting the old path.

## Output
- Refactor target
- Behavior-preservation risks
- Ownership and boundary changes
- Migration steps
- Validation plan
