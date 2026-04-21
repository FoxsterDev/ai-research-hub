# Skill: Dependency Seams

## Use For
- service extraction
- SDK and platform isolation
- testability improvements
- coupling reduction

## Rules
- Cut seams at volatile or high-risk dependencies first.
- Prefer composition and narrow contracts over inheritance-heavy refactors.
- Keep orchestration ownership separate from platform ownership when extracting services or presenters around native or SDK code.
- Do not introduce abstraction without a concrete replacement, isolation, ownership, or testability reason.
