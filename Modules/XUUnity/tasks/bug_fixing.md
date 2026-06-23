# XUUnity Task: Bug Fixing

## Goal
Resolve a concrete defect with the minimum safe change while preserving production stability.

## Focus
- Narrow the defect to ownership, threading, lifecycle, marshaling, state, or initialization order.
- Prefer low-risk fixes before structural redesign.
- Treat `skills/tests/testing_doctrine.md` as a default constraint for this task, not an optional add-on.
- Do not default to writing tests immediately while the fix shape is still moving.
  - Prefer adding or finalizing tests near the end of the fix once the owned runtime behavior and seams are stable enough to validate cleanly.
  - If tests are optional, ambiguous, or expensive relative to the task, ask the user whether they want tests instead of spending token budget automatically.
  - If regression risk, bug family, or an explicit user request clearly requires tests, say so briefly and proceed.
- If new tests are authored, run a quick self-review against the testing doctrine before closure.
  - Check at minimum:
    - real owned code versus fake-heavy coverage
    - seam cleanliness
    - readability
    - whether any newly added test should be simplified, replaced, or deleted
- Keep the fix task primary, but if investigation or the patch plan shows that the fix changes ownership boundaries, state orchestration, startup sequencing, SDK wrapper responsibilities, queue or flush logic, cache behavior, or cross-layer placement, also load `tasks/refactoring.md` as a behavior-preserving overlay.
- Check project memory before changing platform or SDK behavior.
- For Android manifest, Gradle, resolver, or SDK-startup defects, verify that the inspected generated artifacts come from the same fresh build being diagnosed.
- If `Library/` was deleted, reimport is in progress, or generated Bee/Gradle outputs may predate a clean rebuild, treat those artifacts as potentially stale evidence rather than root-cause proof.
- Before proposing a source-level fix for vendor-managed manifest entries, inspect the same-build `Editor.log` for resolver and postprocess execution.
- Do not convert a vendor-owned build-time declaration into a permanent checked-in source fix unless a clean rebuild reproduces the failure and ownership transfer is explicitly justified.
- If the bug report uses product-facing entry language such as `enter app`, `come back to app`, `return to lobby`, or similar user-visible wording, normalize that contract across the realistic lifecycle entry modes before closure.
- For startup-sensitive or foreground-return-sensitive bugs, explicitly decide whether the intended contract covers:
  - cold start
  - focus restore or resume
  - both
- Do not close a lifecycle-sensitive UX bug after fixing only one technical entry path when the user-visible contract clearly spans the same product surface across multiple entry modes.
- For popup, modal, or one-shot UX flows on a critical path, explicitly separate:
  - entry contract
  - progression contract
  - data required only for later steps
- If the first user-visible screen can be rendered truthfully from already-known local state, do not block entry on a downstream network dependency that is only required for later progression.
- For request recovery bugs where non-2xx responses can include structured error bodies, load `knowledge/request_recovery.md`; do not design recovery until the endpoint-specific error contract, replay safety, and local-state invalidation boundary are known.
- For MCP tooling / install / setup-wizard / CLI-wrapper bugs, path or argument handling, `.sh`/`.cmd`/`.ps1` flavor divergence, spaces-in-paths, or MSYS/Git-Bash/`os.name` behavior, load `knowledge/cross_platform_shell_portability.md`. For any failure that reproduces only in CI or another environment with no interactive access (including a Windows-only failure investigated from a non-Windows host), load `knowledge/remote_only_failure_bisection.md` and spend the first round-trip on bisection instrumentation, not plausible fixes. Route both through the Tooling / Install / Cross-Platform / Remote-Only family in `knowledge/routing_trigger_matrix.md`.
- For recovery bugs that cross shared response parsing and domain-level orchestration, plan coverage at both boundaries: response contract tests and service recovery behavior tests.
- For missing asset, design, config, manifest, or runtime-content warnings, inspect both the immediate log site and the upstream initialization path before deciding the fix shape.
- Required chain for those warnings:
  - symptom
  - immediate caller
  - service or wrapper
  - initialization owner
  - active config/profile
  - content or manifest availability
- If the chain finds a disabled, absent, stale, or mismatched owner config, prefer `configuration_fix` or `sequencing_fix`; do not classify the task as `local_fix` just because the warning is emitted from a local UI or service class.
- Route these warning families through `knowledge/routing_trigger_matrix.md` to select the required owner chain, allowed patch shapes, and validation lane, and validate the derived routing contract with `scripts/routing_gate_check.py` before patching.

## Patch Shape Classification
- Before patching, classify the fix using the narrowest primary patch shape:
  - `local_fix`: narrow source-level repair with no ownership move, no new orchestration layer, and no cross-layer contract change
  - `configuration_fix`: changes an active build/runtime config, enabled flag, profile selection, manifest/content registration, or other owner input without changing source behavior
  - `ownership_fix`: moves field, lifecycle, callback, identity, or state ownership between existing layers
  - `sequencing_fix`: changes startup, consent, readiness, callback ordering, or other delivery timing between existing owners
  - `state_orchestration_fix`: changes or introduces queues, flush paths, retries, cache-backed fallbacks, gating flags, or duplicated trigger removal
  - `cross_layer_fix`: changes public or cross-module call paths, bridge seams, or other boundary contracts across layers
- If more than one shape applies, name one primary shape and treat the rest as trigger reasons, not as separate primary classes.
- If investigation changes the primary shape, update the classification before continuing with the patch plan.
- Derive closure obligations from the selected patch shape:
  - `local_fix` -> keep the change narrow and validate the touched path with the smallest representative proof
  - `configuration_fix` -> validate the active profile/config ownership and the expected runtime/content availability markers; report runtime validation gap explicitly if the active runtime path was not exercised
  - `ownership_fix` -> treat moved ownership as structural, load `tasks/refactoring.md` as an overlay, and validate the affected assembly or narrowest representative build target
  - `sequencing_fix` -> treat timing or readiness changes as structural when they span owners, wrappers, or startup-sensitive paths, and report runtime validation gap explicitly if no representative run happened
  - `state_orchestration_fix` -> load `tasks/refactoring.md` as an overlay, keep simplification mandatory, and report runtime validation gap explicitly if no representative run happened
  - `cross_layer_fix` -> load `tasks/refactoring.md` as an overlay, validate affected build or assembly fallout, and report any remaining contract-risk surface explicitly

## Complexity Budget
- If the planned or implemented fix introduces new flags, queues, flush triggers, cache-backed fallbacks, helper wrappers, delay gates, or duplicate trigger paths, do not treat that as neutral implementation detail.
- Before adding orchestration state, freeze the user-visible request contract in plain terms: what must happen, what must not be skipped, and when the flow may resume. Rebuild the smallest solution from that contract before modeling counters, queues, or deferred paths.
- If the user asks to simplify, apply first-principles reasoning, or challenges the complexity directly, treat that as new source material. Re-check assumptions instead of only polishing the current patch.
- If the task enters repeated redesign loops, stop and restate the minimal product invariants before continuing. At minimum restate:
  - actual source count
  - persistence unit
  - merge boundary
  - partial-update semantics
  - compatibility envelope
  - required platform backends
- For popup or staged UX flows, also restate:
  - first visible screen contract
  - progression gate
  - late-data downgrade behavior
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
- If investigation upgrades a fix from `local_fix` to `configuration_fix`, update the classification and verify the edited profile/config is actually active for the diagnosed project or build lane.
- After the fix works, run one simplification pass:
  - remove redundant wrappers, intermediate helpers, duplicated triggers, or state flags that no longer carry real ownership value
  - prefer the smallest stable state model that still preserves behavior
- After the simplification pass, run one self-review pass focused on:
  - regression risk
  - hidden behavior drift
  - stuck queue or retry paths
  - missing cleanup of temporary workaround logic
  - compile-time fallout from moved fields, signatures, or ownership changes
- For `configuration_fix`, do not claim closure until self-review and the matched validation obligations were completed or explicitly reported as gaps.
- For `ownership_fix`, `sequencing_fix`, `state_orchestration_fix`, and `cross_layer_fix`, do not claim closure until simplification, self-review, and the matched validation obligations were completed or explicitly reported as gaps.
- When the fix moved code across layers or changed public or cross-module call paths, validate the affected assembly or the narrowest representative build target before claiming completion.
- If representative runtime validation is not available, state that gap explicitly instead of treating code inspection as runtime proof.

## Verification Policy
- Derive validation obligations from both the primary patch shape and the bug family. Do not leave `Validation result` at generic wording such as `reviewed code` or `checked flow`.
- Minimum mapping by primary patch shape:
  - `local_fix` -> validate the narrowest touched path with the smallest representative proof; if ownership or signature fallout appears, reclassify instead of keeping the weaker validation rule
  - `configuration_fix` -> verify the active config/profile, owner field, and content or manifest availability expected by the runtime path; if no representative runtime run happened, report the remaining runtime gap explicitly
  - `ownership_fix` -> compile the affected assembly or narrowest representative build target; if no representative runtime run happened, report the remaining runtime gap explicitly
  - `sequencing_fix` -> state the expected observable runtime markers and report the remaining runtime gap explicitly if no representative run happened; compile the affected target if signatures or owners moved
  - `state_orchestration_fix` -> compile the affected target, state the expected runtime markers for ordering, queue drain, or callback delivery, and report the remaining runtime gap explicitly if no representative run happened
  - `cross_layer_fix` -> validate affected assembly or representative build fallout and name any unresolved contract-risk surface explicitly if the runtime path was not exercised
- Minimum bug-family overlays:
  - startup, consent, SDK initialization, attribution identity, or ad-revenue work -> list the expected logs, callbacks, readiness markers, or observable state transitions that would prove the fix at runtime
  - missing asset, design, config, manifest, or runtime-content warning -> list the checked chain from symptom through immediate caller, service/wrapper, initialization owner, active config/profile, and content/manifest availability; state why the chosen patch shape is not a local warning-site fix
  - analytics or reporting work -> list the event names, required fields, ordering assumptions, or observable markers that would prove the fix
  - request recovery work -> validate structured non-2xx error-body parsing, cache invalidation before retry, recovery failure behavior, safe replay boundaries, and correlated trigger/recovery/retry diagnostics
  - editor-only work -> verify the editor path explicitly rather than treating generic compile success as full proof
  - manifest, resolver, native, or vendor-managed build-time work -> validate same-build generated artifacts and same-build `Editor.log` evidence before treating the root cause as proven
- If available evidence is weaker than the derived validation obligation, report that as a validation gap instead of silently weakening the requirement.

## Output
- Root cause
- Root-cause chain checked
- Patch shape and trigger reasons
- Why not local fix, when the symptom originates at a log site but ownership is upstream
- Fix strategy
- Complexity budget result
- Simplification outcome
- Self-review outcome
- Regression risk
- Validation result
- Remaining runtime validation gap
