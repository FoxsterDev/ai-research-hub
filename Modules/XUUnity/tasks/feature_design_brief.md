# XUUnity Task: Feature Design Brief

## Goal
Convert an accepted feature request into the safest implementation shape before writing an implementation plan or code.

## Use For
- feature requests that passed intake and need design shaping
- changes that touch multiple systems or critical flows
- requests where implementation direction is not obvious yet
- cases where dependencies, ownership boundaries, or failure modes need to be made explicit

## Do Not Use For
- choosing a long-term subsystem split from scratch
- comparing architecture options whose main difference is ownership or boundary design
- cases where the central question is structural architecture rather than feature shape
- cases where the main uncertainty is ownership or boundary design rather than feature behavior

## Inputs
- feature intake result
- project router and project memory
- source code for the current implementation baseline
- relevant prior outputs only when they clarify architecture history or behavior drift

## Process
1. Restate the design target:
   - requested behavior
   - user-facing outcome
   - scope constraints
   - explicit non-goals
2. Map the current implementation baseline:
   - systems that already own adjacent behavior
   - current flow entry points
   - shared versus project-local boundaries
   - assumptions that are still unverified
3. Define the safest implementation shape:
   - preferred ownership model
   - affected systems and boundaries
   - required wrappers, adapters, or state transitions
   - whether the change should be additive, replacing, or behind a feature flag
4. Identify critical-flow impact:
   - startup
   - monetization
   - rewards
   - save/load
   - account or identity
   - navigation-heavy UI
   - compliance-sensitive flows
5. Identify dependencies and prerequisites:
   - memory gaps
   - SDK or native dependencies
   - missing architecture clarity
   - rollout or validation prerequisites
6. Identify failure modes and regressions to prevent:
   - state ownership mistakes
   - async or callback races
   - duplicated rewards or duplicated side effects
   - navigation regressions
   - platform-specific breakage
7. Decide the next planning step:
   - `implementation_plan.md` if the design shape is defendable
   - `project_memory_freshness.md` if stale memory blocks safe design decisions
   - `project_health_audit.md` if project context is too weak for dependable planning
   - stop and request clarification if the feature goal is still underspecified

## Output
- Design target summary
- Current implementation baseline
- Proposed implementation shape
- Ownership boundaries
- Critical flows touched
- Dependencies and prerequisites
- Main failure modes to guard against
- Open questions
- Recommended next protocol step

## Rules
- Do not jump from feature request directly to code-level task breakdown if implementation shape is still ambiguous.
- Do not use this task to hide unresolved architecture questions behind feature wording.
- Do not use this task when the main unresolved question is ownership or boundary design.
- Keep shared versus project-local boundaries explicit.
- If code and memory disagree about current ownership, trust code for current behavior and note the memory drift.
- If the change touches critical flows, make the risk visible now instead of deferring it to implementation.
- If the main uncertainty is long-term boundary or ownership design, step back to architecture planning.
