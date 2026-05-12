# AIReferenceWatch Reference Selection Doctrine

## Purpose

This document defines the durable selection rules for how `AIReferenceWatch`
chooses, compares, and consumes external references.

Use it to keep reference watching disciplined and useful for public `AIRoot`
module design, especially when multiple references are active and some are
strong only in narrow areas.

## Overall Leader vs Capability Leader

Do not treat these as the same thing.

`overall leader` means a reference is strong across the broad decision surface:

- capability breadth
- maintenance and release activity
- contract quality
- issue signal quality
- documentation clarity
- usefulness as a repeated benchmark

`capability leader` means a reference is strongest for one specific area, even
if it is weaker overall.

Examples of capability areas:

- `ui_primitives`
- `scene_read_write`
- `transport`
- `build_profiles`
- `playmode_control`
- `runtime_analysis`
- `agent_workflow`

Rules:

- use `overall leaders` for recurring benchmark comparison
- use `capability leaders` for feature-specific design review
- never assume an `overall leader` is also the best implementation reference for
  every feature
- when the two disagree, feature design should follow the best
  `capability leader`, while progress reporting may still benchmark against the
  chosen `overall leaders`

## Tiering

ReferenceWatch uses three tiers.

### Tier 1: Core Benchmark Set

Purpose:

- stable benchmark comparison
- recurring issue-watch
- regular progress measurement

Rules:

- keep only `2` references here by default
- these should usually be `overall leaders`
- they should be active enough to provide fresh signal
- they should be relevant enough to influence repeated roadmap decisions

### Tier 2: Active Candidate Set

Purpose:

- track fast-moving or specialized references
- track strong `capability leaders`
- evaluate promotion into Tier 1

Rules:

- keep about `3` references here by default
- they may be broad candidates or narrow specialists
- focused comparison is enough; they do not need full recurring coverage for
  every topic

### Tier 3: Parking Lot

Purpose:

- preserve discoverability
- avoid losing useful references
- keep low-cost access to secondary examples

Rules:

- no heavy recurring normalization cost
- use for occasional manual mining
- promote only when a new capability need or stronger signal appears

## Benchmark Selection Rules

Choose Tier 1 benchmark references using weighted signals, not preference.

Required factors:

- public activity and maintenance freshness
- relevance to the target module or protocol
- breadth of usable capability surface
- contract and schema quality
- issue surface quality
- practical value as a benchmark over time

Avoid choosing Tier 1 references that are:

- mostly inactive
- too narrow to benchmark broad progress
- noisy without clear technical signal
- low-quality in contract clarity

## Capability Leader Selection Rules

Choose a `capability leader` per feature area when:

- the repo clearly exposes stronger capability in that area
- the feature evidence is credible enough to learn from
- the implementation pattern or contract style is relevant to `AIRoot`

Signals that a repo may be a capability leader:

- better command surface in the target area
- stronger evidence or result contract
- clearer failure semantics
- better operator ergonomics
- good workaround patterns for known problem cases

Capability leader status may be:

- `confirmed`
- `provisional`

Use `provisional` when evidence still depends on docs or partial code review.

## Adoption Quality Bar

References are inputs to design, not sources to copy blindly.

Borrow only when:

- the idea closes a real gap or improves a real workflow
- the quality is acceptable for the target area
- the contract style fits `XUUnity` or another target module
- the hidden costs are understood
- the team can explain why this is better than a fresh local design

Quality checks before adopting an idea:

- contract clarity
- evidence quality
- failure semantics
- maintainability
- architecture fit
- safety and runtime cost
- operator usability

Do not adopt in blind form:

- code snippets just because they are convenient
- broad grouped APIs with weak boundaries
- features that increase surface area without clear user value
- implementation patterns that conflict with local safety posture
- issue workarounds that solve another repo's constraints but not ours

## Issue-Watch to Regression-Check Mapping

Issue-watch is useful only if it can trigger local verification or local design
questions.

When a recurring external issue theme is found, classify it into one of these
outcomes:

- `no_local_action`
  - not relevant to our architecture or target use case
- `design_review`
  - check whether current local design has the same weakness
- `test_gap`
  - add or strengthen a regression check
- `ops_gap`
  - add operator guidance or runtime diagnostics
- `feature_gap`
  - local surface is missing a useful capability that would reduce the issue

Recommended mapping examples:

- selector ambiguity
  - local action: `design_review` and possibly `test_gap`
- playmode lifecycle instability
  - local action: `test_gap` and possibly `ops_gap`
- Unity version compatibility break
  - local action: `test_gap`
- setup pain from hidden prerequisites
  - local action: `ops_gap`
- brittle grouped tool semantics
  - local action: `design_review`

Every issue-derived local follow-up should record:

- `sourceId`
- `issueTheme`
- `capabilityArea`
- `localRisk`
- `recommendedAction`
- `owner`

## Selection Workflow

For a new feature area:

1. identify current Tier 1 `overall leaders`
2. identify candidate `capability leaders`
3. compare current module state against both
4. review issue themes from Tier 1 and relevant capability leaders
5. decide `borrow / reject / differentiate`
6. open design or backlog work only after that review

## Stability Rule

This doctrine should change slowly.

If a new project or reference suggests a better short-term idea, update the
host-local watch config first. Update this knowledge doc only when the rule
itself should become durable across future work.
