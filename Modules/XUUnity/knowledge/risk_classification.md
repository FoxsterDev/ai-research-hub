# XUUnity Knowledge: Risk Classification

## Goal
Define a reusable shared risk model for `xuunity` task assembly so risky work can trigger stronger review and validation stacks consistently across task types.

## Risk Classes

### `low`
- bounded local change
- no direct critical-flow exposure
- no SDK, native, startup, persistence, or compliance-sensitive boundary
- no meaningful validation-path uncertainty

### `moderate`
- touches shared state, async coordination, UI flow, or validation-sensitive behavior
- still bounded enough that failure is unlikely to become a release blocker by default
- no direct startup, native, manifest, or high-exposure SDK sensitivity unless other evidence escalates it

### `high`
- touches startup, monetization, save/load, SDK initialization, native bridges, manifests, plist, entitlements, privacy declarations, or other high-exposure critical flows
- can create visible breakage, crash/ANR exposure, or store/compliance risk if implemented incorrectly
- depends on merged build artifacts, native/plugin behavior, or validation-path constraints for confidence

### `critical`
- likely release blocker
- meaningful crash, ANR, privacy, compliance, or irreversible state-corruption exposure
- broad breakage surface across startup, core monetization, account/identity, or save/load flows
- unresolved uncertainty is already too large for a normal implementation stack to be credible

## Escalation Rules
- Escalate by one class when more than one independent high-risk signal is present, such as `startup + SDK`, `native + manifest`, or `save/load + migration`.
- Escalate when critical-flow exposure is direct and user-visible even if the code diff looks small.
- Escalate when validation depends on merged build artifacts, store declarations, or native/plugin runtime behavior that cannot be trusted from source inspection alone.
- Escalate when the task changes ownership at a sensitive boundary instead of making a bounded local fix.
- Do not flatten mixed evidence into `low` only because the implementation scope appears small.

## De-escalation Rules
- Do not classify a task as `high` or `critical` only because it mentions a broad subsystem name.
- If the risky surface is adjacent but not actually being changed, keep the lower class and explain the boundary.
- If a task is review-only or planning-only, classify by the breakage surface being evaluated, not by the fact that no code is being written yet.

## Routing Use
- Use this file when `xuunity` must infer risk class or decide whether policy-pack routing is required.
- Policy packs define change-family-specific mandatory layers.
- This file defines the cross-task doctrine for when those packs should be considered and how strongly the task should be escalated.

## Rules
- Risk classification is not a substitute for project memory. Project-local critical-flow facts still come from project memory and source code.
- Prefer explicit trigger reasons such as `startup path`, `SDK upgrade`, or `manifest-sensitive native change` over vague statements like `this seems risky`.
- If validation-path uncertainty is material, keep the risk class elevated until the uncertainty is resolved.
