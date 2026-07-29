# XUUnity Utility: System Evaluation Cadence

## Goal
Define when `xuunity` should review installation health, run model-fitness
fixtures, and attempt a bounded improvement.

## When To Run
Run `utilities/system_self_evaluation.md`:
- after any structural change to `AIRoot/Modules/XUUnity/`
- after introducing or restructuring `AIModules/XUUnityInternal/`
- after adding or removing a skill family
- after changing shorthand routing rules
- after moving source-of-truth paths
- after large prompt cleanup or migration
- before team rollout
- before declaring the protocol stable for daily use

Run a full installation review periodically:
- after every 5-10 meaningful protocol edits
- or once per major protocol iteration

Run `utilities/system_health_review.md`:
- when the system starts feeling noisy
- when duplicate guidance appears
- when routing becomes hard to explain
- when different files seem to disagree
- when the public core versus internal overlay boundary is unclear
- after a model, agent surface, adapter, or permission-policy update
- before adopting a new model for regular `xuunity` work
- after a protocol change that claims to improve routing, compliance, or
  delivery reliability

## Quick Versus Full
- Every health invocation should run the deterministic `quick` installation
  audit when the script is available.
- Run the semantic `full` installation review after structural changes or when
  cadence, audit findings, or baseline age requires it.
- Run the exact current model-surface fixture baseline when an approved adapter
  and budget are available.
- Run the full supported model matrix after a protocol reliability change,
  before adding or removing a supported model surface, or when cross-model
  behavior is the question.
- If an adapter, exact identity, representative fixture, or approved budget is
  missing, report `not_run`; do not substitute self-assessment.

## Model Baseline Identity
A baseline is exact only when all fields match:
- model id and version
- reasoning effort
- agent surface
- adapter and adapter version
- tool and permission policy
- protocol fingerprint
- fixture-suite hash
- scorer version

Any changed field invalidates direct comparison. Keep the old run as historical
evidence, but classify it as `stale` for the current identity.

Protocol-improvement A/B is the deliberate exception: treat the baseline and
candidate protocol fingerprints as the single treatment variable, require
every other identity field above to match, and predeclare acceptance and
non-regression thresholds. This comparison does not make the candidate an
exact reusable baseline.

## Improvement Cadence
- Plain `xuunity system health` is review-only.
- `xuunity system health improve` authorizes a bounded candidate loop.
- Evaluate one corrective hypothesis at a time so metric movement remains
  attributable.
- Use the host-declared iteration and cost ceiling. Stop after the first
  accepted candidate unless the user explicitly requests another iteration.
- Stop and report `inconclusive` when repeated runs disagree enough to change
  the decision.
- Never accept a candidate from a mismatched baseline, a critical fixture
  defect, or an invalid run.

Run `utilities/system_output_cleanup.md`:
- after archive-heavy prompt or report migrations
- when archive growth starts outpacing active project memory value
- after repeated weekly protocol or project-output churn
- after the second consecutive cleanup pass that archives more than it deletes

Run archive-retention review specifically:
- every `7` days for volatile or weekly-changing projects
- every `21` days for normal active projects
- after a new canonical system-health or system-progress report changes what should stay hot in `AIOutput/Reports/System/`

## Suggested Short Commands
- `xuunity system evaluate the protocol structure`
- `xuunity system installation review`
- `xuunity system health review`
- `xuunity system health improve`
- `xuunity system cleanup aggressive`
- `xuunity system prune old archives`

## Score Actions
Apply these actions to the installation score only. Keep model fitness separate.

If installation score is `18-20`:
- keep the structure stable
- allow only targeted improvements

If installation score is `14-17`:
- continue using the system
- schedule cleanup for duplicated or weak areas

If installation score is `10-13`:
- do not expand the system until conflicts are reduced
- fix routing ambiguity and duplication first

If installation score is below `10`:
- pause new protocol growth
- perform structural cleanup before relying on the system broadly

## Priority Of Fixes
Fix in this order:
1. conflicting source-of-truth rules
2. broken public-core versus internal-overlay boundaries
3. duplicated routing or duplicated best practices
4. dead files and unreachable layers
5. weak scoring areas in `routing_stability` or `reachability`
6. weak scoring areas in `boundary_integrity` or `execution_efficiency`
7. wording and presentation polish

## Output
- Trigger reason
- Installation review scope and score
- Model baseline status per exact model-surface identity
- Whether cleanup is required now
- Whether a bounded improvement run is authorized
- Whether archive pruning is required now
- Recommended next actions
