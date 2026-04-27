# XUUnity Task: Bug Fixing

## Goal
Resolve a concrete defect with the minimum safe change while preserving production stability.

## Focus
- Narrow the defect to ownership, threading, lifecycle, marshaling, state, or initialization order.
- Prefer low-risk fixes before structural redesign.
- Keep the fix task primary, but if investigation or the patch plan shows that the fix changes ownership boundaries, state orchestration, startup sequencing, SDK wrapper responsibilities, queue or flush logic, cache behavior, or cross-layer placement, also load `tasks/refactoring.md` as a behavior-preserving overlay.
- Check project memory before changing platform or SDK behavior.
- For Android manifest, Gradle, resolver, or SDK-startup defects, verify that the inspected generated artifacts come from the same fresh build being diagnosed.
- If `Library/` was deleted, reimport is in progress, or generated Bee/Gradle outputs may predate a clean rebuild, treat those artifacts as potentially stale evidence rather than root-cause proof.
- Before proposing a source-level fix for vendor-managed manifest entries, inspect the same-build `Editor.log` for resolver and postprocess execution.
- Do not convert a vendor-owned build-time declaration into a permanent checked-in source fix unless a clean rebuild reproduces the failure and ownership transfer is explicitly justified.

## Patch Shape Classification
- Before patching, classify the fix using the narrowest primary patch shape:
  - `local_fix`: narrow source-level repair with no ownership move, no new orchestration layer, and no cross-layer contract change
  - `ownership_fix`: moves field, lifecycle, callback, identity, or state ownership between existing layers
  - `sequencing_fix`: changes startup, consent, readiness, callback ordering, or other delivery timing between existing owners
  - `state_orchestration_fix`: changes or introduces queues, flush paths, retries, cache-backed fallbacks, gating flags, or duplicated trigger removal
  - `cross_layer_fix`: changes public or cross-module call paths, bridge seams, or other boundary contracts across layers
- If more than one shape applies, name one primary shape and treat the rest as trigger reasons, not as separate primary classes.
- If investigation changes the primary shape, update the classification before continuing with the patch plan.
- Derive closure obligations from the selected patch shape:
  - `local_fix` -> keep the change narrow and validate the touched path with the smallest representative proof
  - `ownership_fix` -> treat moved ownership as structural, load `tasks/refactoring.md` as an overlay, and validate the affected assembly or narrowest representative build target
  - `sequencing_fix` -> treat timing or readiness changes as structural when they span owners, wrappers, or startup-sensitive paths, and report runtime validation gap explicitly if no representative run happened
  - `state_orchestration_fix` -> load `tasks/refactoring.md` as an overlay, keep simplification mandatory, and report runtime validation gap explicitly if no representative run happened
  - `cross_layer_fix` -> load `tasks/refactoring.md` as an overlay, validate affected build or assembly fallout, and report any remaining contract-risk surface explicitly

## Complexity Budget
- If the planned or implemented fix introduces new flags, queues, flush triggers, cache-backed fallbacks, helper wrappers, delay gates, or duplicate trigger paths, do not treat that as neutral implementation detail.
- If the task enters repeated redesign loops, stop and restate the minimal product invariants before continuing. At minimum restate:
  - actual source count
  - persistence unit
  - merge boundary
  - partial-update semantics
  - compatibility envelope
  - required platform backends
- Before claiming closure on such a fix, state:
  - why the added complexity is necessary
  - which simpler alternatives were rejected
  - what temporary logic was removed, merged, or flattened after the fix worked
- If you cannot justify the remaining orchestration in one or two concrete sentences, reconsider the patch shape and simplify before closure.
- For `state_orchestration_fix` and `cross_layer_fix`, default expectation is net simplification after the bug is solved, not permanent accumulation of new orchestration layers.

## Closure Discipline
- Before patching, derive closure obligations from the selected patch shape instead of from general severity alone.
- Do not stop at the first working patch when the bug fix introduced new flags, helper wrappers, delayed queues, flush triggers, cache fallbacks, or duplicated orchestration.
- If investigation upgrades a fix from `local_fix` to `ownership_fix`, `sequencing_fix`, `state_orchestration_fix`, or `cross_layer_fix`, update the classification and treat the remaining work as structural.
- After the fix works, run one simplification pass:
  - remove redundant wrappers, intermediate helpers, duplicated triggers, or state flags that no longer carry real ownership value
  - prefer the smallest stable state model that still preserves behavior
- After the simplification pass, run one self-review pass focused on:
  - regression risk
  - hidden behavior drift
  - stuck queue or retry paths
  - missing cleanup of temporary workaround logic
  - compile-time fallout from moved fields, signatures, or ownership changes
- For `ownership_fix`, `sequencing_fix`, `state_orchestration_fix`, and `cross_layer_fix`, do not claim closure until simplification, self-review, and the matched validation obligations were completed or explicitly reported as gaps.
- When the fix moved code across layers or changed public or cross-module call paths, validate the affected assembly or the narrowest representative build target before claiming completion.
- If representative runtime validation is not available, state that gap explicitly instead of treating code inspection as runtime proof.

## Verification Policy
- Derive validation obligations from both the primary patch shape and the bug family. Do not leave `Validation result` at generic wording such as `reviewed code` or `checked flow`.
- Minimum mapping by primary patch shape:
  - `local_fix` -> validate the narrowest touched path with the smallest representative proof; if ownership or signature fallout appears, reclassify instead of keeping the weaker validation rule
  - `ownership_fix` -> compile the affected assembly or narrowest representative build target; if no representative runtime run happened, report the remaining runtime gap explicitly
  - `sequencing_fix` -> state the expected observable runtime markers and report the remaining runtime gap explicitly if no representative run happened; compile the affected target if signatures or owners moved
  - `state_orchestration_fix` -> compile the affected target, state the expected runtime markers for ordering, queue drain, or callback delivery, and report the remaining runtime gap explicitly if no representative run happened
  - `cross_layer_fix` -> validate affected assembly or representative build fallout and name any unresolved contract-risk surface explicitly if the runtime path was not exercised
- Minimum bug-family overlays:
  - startup, consent, SDK initialization, attribution identity, or ad-revenue work -> list the expected logs, callbacks, readiness markers, or observable state transitions that would prove the fix at runtime
  - analytics or reporting work -> list the event names, required fields, ordering assumptions, or observable markers that would prove the fix
  - editor-only work -> verify the editor path explicitly rather than treating generic compile success as full proof
  - manifest, resolver, native, or vendor-managed build-time work -> validate same-build generated artifacts and same-build `Editor.log` evidence before treating the root cause as proven
- If available evidence is weaker than the derived validation obligation, report that as a validation gap instead of silently weakening the requirement.

## Output
- Root cause
- Patch shape and trigger reasons
- Fix strategy
- Complexity budget result
- Simplification outcome
- Self-review outcome
- Regression risk
- Validation result
- Remaining runtime validation gap
