# XUUnity Review: Delivery Risk

## Goal
Review planned feature delivery risk before coding or rollout decisions so breakage exposure, blockers, and mandatory checks are explicit.

## Use For
- features that already have a design brief and implementation plan
- validation plans that expose material uncertainty or rollout sensitivity
- changes that touch critical flows, shared state, monetization, startup, save/load, SDK boundaries, or lifecycle behavior
- work that looks implementable but may still be unsafe to land without extra controls

## Inputs
- feature design brief
- implementation plan
- validation plan
- project memory and project-specific constraints
- source code when ownership, dependency, or current-flow assumptions need verification
- `knowledge/review_quality_scoring.md`

## Process
1. Restate the delivery target:
   - target behavior
   - systems and files likely to change
   - critical flows touched
   - assumptions that are still unverified
2. Classify delivery risk:
   - `low`
   - `moderate`
   - `high`
   - `critical`
3. Identify why the change can break:
   - shared ownership or unclear boundaries
   - lifecycle or async complexity
   - state restoration or duplicate-action risk
   - SDK, native, manifest, or platform-specific sensitivity
   - weak observability or validation coverage
4. Separate blockers from mitigations:
   - blockers that must be resolved before implementation or rollout confidence is credible
   - mitigations that reduce risk but do not remove the need for review or validation
5. Define mandatory controls:
   - required validation gates
   - required code review depth
   - rollout or staged-release constraints
   - dependency or build-artifact checks when relevant
6. Decide the next protocol step:
   - `tasks/feature_development.md` if risk is understood and controlled
   - `reviews/release_readiness_review.md` if the main question is ship readiness
   - stop and request clarification if ownership, validation, or dependency assumptions are still too weak

## Output
When the review is output or saved as a report, include review metadata at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`

- Delivery target summary
- Delivery risk class
- Critical flows at risk
- Main breakage modes
- Blockers
- Mandatory controls and validation gates
- Recommended next protocol step
- Quality score section using `knowledge/review_quality_scoring.md`

## Rules
- Do not flatten uncertain or mixed evidence into `low` risk.
- Distinguish code-verified concerns from project-memory assumptions.
- Call out critical-flow exposure explicitly even if implementation scope looks small.
- If rollout safety depends on merged artifacts, device behavior, or vendor constraints, say so directly.
- Do not treat "can probably be validated later" as an acceptable substitute for a current risk decision.
