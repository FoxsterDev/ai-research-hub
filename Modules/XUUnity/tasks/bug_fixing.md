# XUUnity Task: Bug Fixing

## Goal
Resolve a concrete defect with the minimum safe change while preserving production stability.

## Focus
- Narrow the defect to ownership, threading, lifecycle, marshaling, state, or initialization order.
- Prefer low-risk fixes before structural redesign.
- Keep the fix task primary, but if the fix changes ownership boundaries, state orchestration, startup sequencing, SDK wrapper responsibilities, queue or flush logic, cache behavior, or cross-layer placement, also load `tasks/refactoring.md` as a behavior-preserving overlay.
- Check project memory before changing platform or SDK behavior.
- For Android manifest, Gradle, resolver, or SDK-startup defects, verify that the inspected generated artifacts come from the same fresh build being diagnosed.
- If `Library/` was deleted, reimport is in progress, or generated Bee/Gradle outputs may predate a clean rebuild, treat those artifacts as potentially stale evidence rather than root-cause proof.
- Before proposing a source-level fix for vendor-managed manifest entries, inspect the same-build `Editor.log` for resolver and postprocess execution.
- Do not convert a vendor-owned build-time declaration into a permanent checked-in source fix unless a clean rebuild reproduces the failure and ownership transfer is explicitly justified.

## Closure Discipline
- Do not stop at the first working patch when the bug fix introduced new flags, helper wrappers, delayed queues, flush triggers, cache fallbacks, or duplicated orchestration.
- After the fix works, run one simplification pass:
  - remove redundant wrappers, intermediate helpers, duplicated triggers, or state flags that no longer carry real ownership value
  - prefer the smallest stable state model that still preserves behavior
- After the simplification pass, run one self-review pass focused on:
  - regression risk
  - hidden behavior drift
  - stuck queue or retry paths
  - missing cleanup of temporary workaround logic
  - compile-time fallout from moved fields, signatures, or ownership changes
- When the fix moved code across layers or changed public or cross-module call paths, validate the affected assembly or the narrowest representative build target before claiming completion.
- If representative runtime validation is not available, state that gap explicitly instead of treating code inspection as runtime proof.

## Output
- Root cause
- Fix strategy
- Regression risk
- Validation steps
