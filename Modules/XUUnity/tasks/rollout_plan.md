# XUUnity Task: Rollout Plan

## Goal
Define the safest rollout shape for a planned or implementation-ready feature before release so staged exposure, monitoring, and rollback expectations are explicit.

## Use For
- features that already have a design brief, implementation plan, or validation plan
- changes that touch critical flows, SDKs, startup, monetization, save/load, or release-sensitive declarations
- work that may be technically implementable but still unsafe to ship without staged rollout controls
- features where rollback shape, observability, or feature-flag posture should be decided before release time

## Inputs
- implementation plan
- validation plan
- delivery risk review when available
- matched risk-sensitive review outputs when rollout shape depends on SDK, startup, manifest, native, monetization, or save/load risk
- project memory and project-specific constraints
- source code or merged build-artifact evidence when rollout safety depends on current implementation or generated declarations

## Process
1. Restate the rollout target:
   - target behavior
   - systems and flows affected
   - user-facing impact
   - critical flows touched
2. Classify the dominant rollout risk surface:
   - SDK, startup, manifest/native, monetization, save/load, or other critical-flow-sensitive work
   - whether the current rollout question depends on a matched policy pack or narrower release-risk evidence
   - whether the current risk is mostly breakage risk, exposure risk, or observability risk
3. Identify rollout prerequisites:
   - implementation dependencies that must land first
   - validation gates that must pass before exposure
   - SDK, manifest, plist, entitlement, or privacy evidence required before rollout confidence is credible
4. Decide the rollout shape:
   - immediate release
   - staged rollout
   - feature flag or remote config gate
   - platform-specific rollout split
   - internal-only or limited-audience release first
5. Define exposure checkpoints:
   - pre-release gate
   - first exposure gate
   - broader rollout gate
   - full-release gate
6. Define monitoring and rollback expectations:
   - signals to watch
   - failure thresholds
   - disable, rollback, or fallback path
   - who or what can stop rollout if signals degrade
7. Identify rollout blockers:
   - missing observability
   - unclear rollback path
   - no safe feature flag or staged gate
   - unresolved compliance or build-artifact uncertainty
8. Decide the next protocol step:
   - `reviews/release_readiness_review.md` if the main question is go or no-go
   - `tasks/feature_development.md` if rollout support needs implementation work first
   - `product/protocols/rollout_readiness.md` if a product-facing readiness summary is needed after the plan exists
   - stop and request clarification if the rollout surface is still too uncertain

## Output
- Rollout target summary
- Dominant rollout risk surface
- Proposed rollout shape
- Exposure checkpoints
- Monitoring signals and rollback triggers
- Rollout blockers
- Required evidence before release
- Recommended next protocol step

## Rules
- Do not assume an immediate full release is the default safe shape for critical-flow-sensitive work.
- Keep policy-pack-specific concerns visible in rollout gates when the dominant breakage surface is SDK, startup, or manifest/native work.
- If rollout safety depends on generated build artifacts, merged manifests, plist entries, entitlements, privacy manifests, or SDK version truth, require that evidence explicitly.
- If no credible rollback, disable, or containment path exists, call that out as a blocker instead of pretending staged rollout is available.
- Keep rollout planning distinct from product-facing rollout readiness: this task defines the execution plan, while `product/protocols/rollout_readiness.md` explains ship readiness.
