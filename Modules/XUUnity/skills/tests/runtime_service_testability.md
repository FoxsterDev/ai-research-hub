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
- Non-public test access order for repo-owned code:
  1. real public contract
  2. narrow `internal` seam with `InternalsVisibleTo`
  3. protected seam plus test subclass only when inheritance already fits the runtime design
  4. reflection only with explicit approval for closed or legacy boundaries
- Do not add explicit `...ForTests` APIs when `internal` access or an existing runtime seam is enough.
- Do not add broad test-only delegates, hook fields, or override points unless they have runtime design value outside the test suite.
- If full branch coverage requires invasive seams that do not improve runtime design, stop. Test pure policy, persistence boundaries, and wrapper contracts instead.
- Make time and platform dependencies overridable in tests when they drive behavior.
- For singleton PlayMode isolation, reset only mutable test state and scene objects. Do not dispose or recreate lifetime infrastructure that production cannot safely re-establish, such as a long-lived cancellation source; keep cleanup test-owned or behind a narrow production-valid seam.

## Review Focus
- seam size
- runtime API cleanliness
- reflection pressure in tests
- correct EditMode versus PlayMode split
