# Skill: Runtime Service Testability

## Use For
- Unity runtime services and singletons
- services that wrap engine callbacks
- services that use `DontDestroyOnLoad`
- time or platform-sensitive runtime behavior

## Rules
- Follow `testing_doctrine.md` as the baseline testing policy.
- Split pure logic from engine-integration behavior where possible.
- Keep policy and state-machine tests in EditMode when they do not need engine object setup.
- Use PlayMode for integration behavior that depends on `DontDestroyOnLoad`, engine message methods, or runtime object lifetime.
- Prefer minimal protected seams plus a test subclass over reflection-heavy tests.
- Prefer protected seams plus a test subclass over explicit `...ForTests` production APIs unless no cleaner seam is sufficient.
- Reflection against private state or private method flow in tests for live production code requires explicit human approval. If the target is legacy or static platform-bound code where a cleaner seam is not proportionate, call that exception out directly instead of normalizing reflection as the default answer.
- Broad test-only delegates, hook fields, and override points in shipping runtime code should be treated as rejected by default unless the seam has clear independent runtime design value outside the test suite.
- If full branch coverage requires invasive test seams that do not improve the runtime design itself, stop short of adding them and prefer narrower direct tests of pure policy, persistence boundaries, and wrapper contracts instead.
- Make time and platform dependencies overridable in tests when they drive behavior.

## Review Focus
- seam size
- runtime API cleanliness
- reflection pressure in tests
- correct EditMode versus PlayMode split
