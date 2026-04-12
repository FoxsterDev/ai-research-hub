# XUUnity Task: Feature Request Intake

## Goal
Turn a feature request into a scoped, implementation-ready intake package before design or coding begins.

## Use For
- new feature requests
- feature changes with unclear scope
- requests that may touch critical flows
- product-to-engineering handoff before implementation planning

## Inputs
- user request or feature brief
- project router and project memory
- relevant source code when current behavior or dependencies are unclear
- prior project outputs only when they help clarify feature history or behavior drift

## Process
1. Clarify the feature request:
   - requested outcome
   - user-facing goal
   - explicit non-goals if present
   - deadline or rollout pressure if stated
2. Identify the likely scope:
   - screens, flows, systems, SDKs, save data, or backend-facing assumptions involved
   - whether the request is net-new, extension of existing behavior, or a replacement of current behavior
3. Identify the current-state baseline:
   - what already exists in code or project memory
   - what is assumed but not yet verified
   - what is missing and requires clarification
4. Identify critical-flow impact:
   - startup
   - monetization
   - rewards
   - save/load
   - account or identity
   - navigation-heavy UI
   - platform compliance
5. Identify memory and dependency gaps:
   - missing project-memory files
   - missing architecture ownership clarity
   - unclear SDK or native dependencies
   - unclear rollout or validation expectations
6. Classify initial delivery risk:
   - `low`
   - `moderate`
   - `high`
   - `critical`
7. Decide the next protocol step:
   - `feature_design_brief.md` if the request is valid and needs design shaping
   - `project_memory_freshness.md` if stale memory blocks safe interpretation
   - `project_health_audit.md` if the project context is too weak for dependable delivery planning
   - no further delivery planning until missing context is resolved

## Output
- Feature request summary
- User-facing goal
- Scope hypothesis
- Current-state baseline
- Critical flows touched
- Dependencies and unknowns
- Memory/context blockers
- Initial risk class
- Recommended next protocol step

## Rules
- Do not jump directly into implementation shape before the request is scoped.
- Distinguish verified current behavior from assumed behavior.
- If the request depends on stale or missing project memory, surface that explicitly instead of hiding it inside the design phase.
- If the feature touches critical flows, keep that visible in the intake result so later protocols can assemble the right review stack.
