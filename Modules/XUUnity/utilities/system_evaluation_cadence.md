# XUUnity Utility: System Evaluation Cadence

## Goal
Define when `XUUnity` should run self-evaluation and what to do with the result.

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

Run it periodically:
- after every 5-10 meaningful protocol edits
- or once per major protocol iteration

Run `utilities/system_health_review.md`:
- when the system starts feeling noisy
- when duplicate guidance appears
- when routing becomes hard to explain
- when different files seem to disagree
- when the public core versus internal overlay boundary is unclear

## Suggested Short Commands
- `xuunity system evaluate the protocol structure`
- `xuunity system health review`

## Score Actions
If total score is `18-20`:
- keep the structure stable
- allow only targeted improvements

If total score is `14-17`:
- continue using the system
- schedule cleanup for duplicated or weak areas

If total score is `10-13`:
- do not expand the system until conflicts are reduced
- fix routing ambiguity and duplication first

If total score is below `10`:
- pause new protocol growth
- perform structural cleanup before relying on the system broadly

## Priority Of Fixes
Fix in this order:
1. conflicting source-of-truth rules
2. broken public-core versus internal-overlay boundaries
3. duplicated routing or duplicated best practices
4. dead files and unreachable layers
5. weak scoring areas in `stability`
6. weak scoring areas in `usefulness`
7. wording and presentation polish

## Output
- Trigger reason
- Current score
- Whether cleanup is required now
- Recommended next actions
