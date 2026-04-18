# XUUnity Review Policy Pack: Startup Changes

## Goal
Strengthen the stack for startup-sensitive work where small mistakes can create ANR, crash, consent, ordering, or first-interaction regressions.

## Trigger When
- the task changes bootstrapping, initialization sequencing, first interactive flow, startup-blocking consent, resume-sensitive init, or startup dependency ownership
- the task changes whether a feature or SDK is blocking, deferred, timed out, or single-flight during startup
- the task touches first-frame, first-scene, or startup observability behavior

## Primary Risk Signals
- startup stall or ANR exposure
- double initialization or ordering races
- first interactive flow blocked by optional work
- startup-bound consent or permission sequencing
- hidden dependency on app-active or resume state

## Mandatory Stack Additions
- `skills/mobile/startup.md`
- `skills/core/critical_flow_protection.md`
- `skills/core/zero_crash_zero_anr.md`
- `skills/optimization/loading_and_microfreeze_prevention.md`
- `skills/sdk/initialization.md` when SDK init is part of the startup path
- `skills/async/` when startup ownership, cancellation, timeout, or callback coordination is relevant
- `reviews/release_readiness_review.md` when rollout confidence or ship-readiness is part of the task
- host-local startup consent knowledge only when the overlay routing trigger actually matches

## Validation Focus
- first interactive time and blocked-loading risk
- timeout and recovery behavior when optional services are slow or hung
- duplicate startup entry protection
- app-active timing for permission or consent prompts
- scene-entry, resume, ad-return, and reward-return regressions on startup-adjacent flows

## Co-loading Rule
- Prefer this pack as the primary pack when startup sequencing or startup critical-flow behavior is the main exposure.
- If the same task also changes SDK or native boundaries, load only the extra layers required for those boundaries instead of turning startup review into a full unrelated stack dump.

## Rule
- Treat startup as a critical-flow surface. Do not weaken the stack only because the code diff is small.
