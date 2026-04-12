# Skill: PlayMode Tests

## Use For
- scene flows
- runtime object interactions
- UI and gameplay integration

## Rules
- Use PlayMode tests for runtime behavior that cannot be trusted in pure unit tests.
- Target critical user flows rather than broad shallow coverage.
- Keep setup cost low enough that tests remain maintainable.
- Validate pause, resume, scene reload, and lifecycle-sensitive behavior where relevant.
