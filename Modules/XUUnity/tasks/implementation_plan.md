# XUUnity Task: Implementation Plan

## Goal
Turn an accepted feature design into a concrete execution plan before code changes begin.

## Use For
- features that already have a defendable design shape
- work that needs explicit sequencing before implementation
- changes that touch multiple files, systems, or critical flows
- features where validation and rollback checkpoints should be visible before coding

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
6. Identify implementation risks:
   - state ownership regressions
   - duplicated side effects
   - ordering or teardown races
   - migration risk
   - platform-specific breakage
7. Decide the next protocol step:
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
- Main implementation risks
- Open execution questions
- Recommended next protocol step

## Rules
- Do not jump into code if the sequence of changes is still ambiguous.
- Prefer the smallest safe execution shape over broad simultaneous rewrites.
- Keep critical-flow checkpoints visible so validation is not deferred until the end.
- If the plan depends on stale or uncertain memory, say so and fall back to code-backed planning.
