# Architecture Routing

## Base Rule
If the task is primarily about target-shape design, load the relevant files from `skills/architecture/`.

Prefer architecture when the main question is:
- what the target subsystem split should be
- where ownership should live long-term
- how state and event flow should be modeled
- whether a presenter, facade, service, wrapper, or model boundary should exist at all

Prefer `tasks/feature_design_brief.md` instead when:
- the user-facing feature shape is still unsettled
- the main ambiguity is scope, flow, or product behavior rather than structure

Prefer `skills/refactoring/` instead when:
- the target shape is mostly known
- the main question is safe migration, seam cutting, or old-path deletion

## Composition Hints
Architecture often composes with:
- `state_management.md` for ownership and transition design
- `dependency_boundaries.md` for stable subsystem layering
- `event_driven_design.md` when event topology is part of the decision
