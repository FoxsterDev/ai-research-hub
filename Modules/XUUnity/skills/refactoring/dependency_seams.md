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
- Do not multiply resolver, decision, result, or helper layers unless each new layer removes a concrete ownership ambiguity, testability barrier, or failure-isolation risk.
- If an extraction would blur semantic boundaries between distinct domain concepts, keep those concepts in separate seams even if the resulting code is slightly more repetitive.
- When a Unity runtime service is hard to test because of engine callbacks or time/platform dependencies, prefer a minimal protected seam plus a test subclass before adding explicit test-only production APIs.
- If tests need reflection over private lifecycle methods or private fields, re-check whether a smaller seam can make the runtime boundary testable without polluting the public contract.
