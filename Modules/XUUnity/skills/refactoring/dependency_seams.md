# Skill: Dependency Seams

## Use For
- service extraction
- SDK and platform isolation
- testability improvements
- coupling reduction

## Rules
- For testing-oriented seam work, follow `skills/tests/testing_doctrine.md` as the baseline policy.
- Cut seams at volatile or high-risk dependencies first.
- Prefer composition and narrow contracts over inheritance-heavy refactors.
- Keep orchestration ownership separate from platform ownership when extracting services or presenters around native or SDK code.
- Do not introduce abstraction without a concrete replacement, isolation, ownership, or testability reason.
- Do not multiply resolver, decision, result, or helper layers unless each new layer removes a concrete ownership ambiguity, testability barrier, or failure-isolation risk.
- Treat constructor bags of `Func<>` or delegate hooks in owned orchestration as a seam-smell by default. Re-check seam placement unless each delegate maps to a real external boundary, deterministic policy input, or stable runtime-owned callback contract.
- The re-check concludes against the delegate when every construction site — production and test alike — passes the same expression, and more so when the receiving method already reads a sibling member of that same source directly. Such a delegate is not a policy input; it is an unused seam that hides the coupling it appears to break. Delete it and read the source directly.
- If an extraction would blur semantic boundaries between distinct domain concepts, keep those concepts in separate seams even if the resulting code is slightly more repetitive.
- That rule presumes the concepts are actually independent. Before invoking it, check whether either type's derived state or teardown reads the other's. A property defined as *my own state OR the sibling's state* is proof they are one concept with two report kinds, not two concepts — merge them and discriminate per record. A class comment asserting the concepts are deliberately separate is an assumption to verify, not a decision that discharges this check.
- When a Unity runtime service is hard to test because of engine callbacks or time/platform dependencies, prefer a minimal protected seam plus a test subclass before adding explicit test-only production APIs.
- For live production code, do not normalize reflection over private lifecycle methods or private fields as a routine testing technique. Require an explicit human decision for that path and re-check whether a smaller seam can make the runtime boundary testable without polluting the public contract.
