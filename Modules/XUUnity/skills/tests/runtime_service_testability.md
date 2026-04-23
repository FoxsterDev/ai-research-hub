# Skill: Runtime Service Testability

## Use For
- Unity runtime services and singletons
- services that wrap engine callbacks
- services that use `DontDestroyOnLoad`
- time or platform-sensitive runtime behavior

## Rules
- Split pure logic from engine-integration behavior where possible.
- Keep policy and state-machine tests in EditMode when they do not need engine object setup.
- Use PlayMode for integration behavior that depends on `DontDestroyOnLoad`, engine message methods, or runtime object lifetime.
- Prefer minimal protected seams plus a test subclass over reflection-heavy tests.
- Prefer protected seams plus a test subclass over explicit `...ForTests` production APIs unless no cleaner seam is sufficient.
- If tests need private field mutation or private message invocation through reflection, re-check the service boundary and seams first.
- Make time and platform dependencies overridable in tests when they drive behavior.

## Review Focus
- seam size
- runtime API cleanliness
- reflection pressure in tests
- correct EditMode versus PlayMode split
