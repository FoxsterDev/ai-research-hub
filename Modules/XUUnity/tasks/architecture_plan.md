# XUUnity Task: Architecture Plan

## Goal
Choose a defensible subsystem shape before refactoring, implementation sequencing, or direct coding begins.

## Use For
- target subsystem split or ownership decisions
- architecture options that need comparison before migration starts
- cases where the main uncertainty is boundary design, not execution sequencing
- changes where event flow, state ownership, or wrapper layering are still unsettled

## Do Not Use For
- execution sequencing after the design shape is already accepted
- local refactors where the target shape is already known and the main question is safe transition
- feature requests that still need user-facing scope shaping before architecture work
- cases where the user-facing feature shape is not settled yet

## Inputs
- current source code for the affected systems
- project router and project memory
- relevant prior outputs only when they clarify boundary history, prior failed designs, or architecture drift

## Process
1. Restate the architecture question:
   - target behavior or capability
   - contested ownership or boundary area
   - explicit non-goals
2. Map the current shape:
   - existing owners
   - current flow entry points
   - dependencies and shared boundaries
   - current pain points or structural risks
3. Compare viable target shapes:
   - ownership model
   - subsystem boundaries
   - event and state flow
   - integration seams
4. Select the preferred target shape:
   - why it is safer
   - what tradeoffs it accepts
   - what complexity it avoids
5. Identify migration readiness:
   - whether the shape is concrete enough for refactoring
   - whether feature design questions are still unresolved
   - whether validation or rollout constraints change the architecture choice
6. Decide the next protocol step:
   - `tasks/refactoring.md` if the target shape is chosen and safe migration is next
   - `tasks/implementation_plan.md` if the target shape is chosen and execution sequencing is next
   - `tasks/feature_design_brief.md` if feature scope or user-facing flow is still ambiguous
   - stop and request clarification if the architecture choice is still underspecified

## Output
- Architecture question summary
- Current shape summary
- Candidate target shapes
- Preferred boundary and ownership decisions
- Tradeoffs and rejected options
- Migration readiness
- Open questions
- Recommended next protocol step

## Rules
- Optimize for clear ownership and stable boundaries, not only immediate delivery.
- Keep architecture planning separate from implementation sequencing.
- Do not use this task when user-facing feature shape, scope, or flow is still unsettled.
- Do not produce a step-by-step execution plan until the target shape is defendable.
- If the decision depends on stale or uncertain memory, say so and fall back to code-backed planning.
