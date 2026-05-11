# XUUnity Task: Implementation Plan

## Goal
Turn an accepted feature design into a concrete execution plan before code changes begin.

## Use For
- features that already have a defendable design shape
- work that needs explicit sequencing before implementation
- changes that touch multiple files, systems, or critical flows
- features where validation and rollback checkpoints should be visible before coding

## Do Not Use For
- choosing the target subsystem split or ownership model from scratch
- comparing architecture options before a preferred design shape exists
- deciding whether a presenter, facade, service, wrapper, or state boundary should exist at all
- cases where the main uncertainty is long-term design direction rather than execution sequencing

## Inputs
- feature design brief
- project router and project memory
- current source code for the affected systems
- relevant prior outputs only when they clarify technical history or prior failed approaches

## Process
1. Restate the approved design shape:
   - target behavior
   - ownership model
   - affected systems
   - critical-flow impact
2. Break the work into implementation steps:
   - preparation or prerequisite work
   - main implementation changes
   - integration updates
   - cleanup or migration work if needed
3. Identify concrete file or subsystem areas likely to change:
   - runtime code
   - wrappers or adapters
   - UI flows
   - native or SDK boundaries
   - config or data definitions
4. Mark execution checkpoints:
   - points where the implementation can be validated before continuing
   - points where risk increases if a previous assumption was wrong
   - points where feature flags or staged rollout support should be considered
5. Define validation expectations before code is written:
   - manual QA scenarios
   - edge cases
   - lifecycle or async checks
   - platform-specific checks
6. Name the validation contract for the implementation slice:
   - primary validation lane
   - any justified secondary lane
   - lane selection reason
   - expected evidence class
   - validation gaps
7. Identify implementation risks:
   - state ownership regressions
   - duplicated side effects
   - ordering or teardown races
   - migration risk
   - platform-specific breakage
8. Decide the next protocol step:
   - `validation_plan.md` if validation coverage should be expanded before coding
   - `delivery_risk_review.md` if delivery risk needs explicit review packaging
   - `feature_development.md` if the implementation path is concrete enough to execute
   - stop and request clarification if the design still leaves critical execution ambiguity

## Output
- Implementation target summary
- Step-by-step execution plan
- Likely file or subsystem areas
- Execution checkpoints
- Validation expectations
- Validation contract:
  - `primary_validation_lane`
  - `secondary_validation_lane`
  - `lane_selection_reason`
  - `expected_evidence_class`
  - `validation_gaps`
- Main implementation risks
- Open execution questions
- Recommended next protocol step

## Rules
- Do not jump into code if the sequence of changes is still ambiguous.
- Do not use this task to hide unresolved architecture decisions behind implementation sequencing.
- Prefer the smallest safe execution shape over broad simultaneous rewrites.
- Keep critical-flow checkpoints visible so validation is not deferred until the end.
- Keep the expected evidence class explicit in the plan instead of collapsing validation into generic QA wording.
- Use the exact validation-contract field names from `knowledge/validation_contract.md`.
- Follow the shared lane and build-sensitive evidence rules from `knowledge/validation_lanes.md` and `knowledge/unity_validation_boundaries.md`.
- If the planned lane cannot provide trustworthy final accounting for the claimed proof surface, keep that as a validation gap in the plan.
- If the plan depends on stale or uncertain memory, say so and fall back to code-backed planning.
- If the target shape is still contested, step back to architecture planning or feature design before producing an execution plan.
