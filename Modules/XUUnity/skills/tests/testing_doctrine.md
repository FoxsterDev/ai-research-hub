# Skill: Testing Doctrine

## Purpose
Use this file as the canonical testing doctrine for `xuunity`.

Tests should maximize confidence in real production behavior without polluting public API shape, degrading component design, or normalizing fake-heavy coverage of owned runtime code.

One of the primary missions of tests is to help find production UX bugs early by closing rare but critical logical branches in real runtime code before users discover them in live flows.

Another mission of tests is to avoid increasing the cognitive complexity of the project. Tests should remain elegant, readable, and understandable to humans rather than becoming a second hard-to-reason system around the product code.

## Definitions

- `live production code`
  - code that currently participates in the shipped or actively maintained runtime behavior of the product
- `owned code`
  - runtime logic, orchestration, policies, and state handling that the project team controls and can redesign directly
- `closed boundary`
  - an external or effectively external surface that the project does not fully control, such as Unity-owned engine APIs, vendor SDKs, native bridge calls, filesystem or keychain shells, transport shells, and environment-provided inputs
- `legacy exception`
  - a case where the target code is static, legacy, platform-bound, or otherwise expensive to reshape cleanly, and a narrower seam would be disproportionate to the current maintenance value
- `real-path coverage`
  - a test path that executes the actual owned production logic under test rather than a mirrored or substitute implementation of that logic
- `exception approval`
  - an explicit human decision that a doctrine exception is proportionate for the current case and is not being normalized into the default testing shape

## Doctrine

### 1. Real Production Code First
- Tests should exercise as much real production runtime code as practical.
- Prefer real production behavior over tests that mostly validate mocks, mirrored fakes, or duplicated test logic.
- Do not fake confidence by proving only scaffolding, trivial forwarding wrappers, or test-only control surfaces.

### 2. Boundary-Only Mocking
- Mocks, fakes, and test doubles are acceptable at true external boundaries:
  - Unity-owned closed surfaces
  - vendor SDK calls
  - native bridge calls
  - filesystem, keychain, network, and process shells
  - time, randomness, and environment inputs that the project does not own
- Do not fake code that the project owns just because it is inconvenient to test directly.

### 3. Owned Code Must Stay Real
- Keep real production logic in tests for:
  - state transitions
  - retry and fallback policy
  - cache behavior and invalidation
  - sequencing and ordering guarantees
  - request and header construction
  - startup and recovery orchestration
  - lifecycle interpretation
  - wrapper orchestration above vendor or native boundaries
  - error translation and recovery decisions
- Prioritize rare but UX-critical logical branches in owned runtime code even when they are inconvenient to reach. These branches are often the ones that escape into production and break user trust.
- Prefer low-frequency, high-impact, user-visible branch coverage before broadening redundant happy-path coverage.

### 4. No Public API Pollution For Tests
- Do not expand public API solely for tests.
- Public `...ForTests` methods, public test flags, and public state exposure are rejected by default.
- If a seam is needed, prefer the narrowest production-valid seam:
  - existing real contract
  - `internal`
  - `protected`
  - `protected virtual`
  - narrow wrapper boundary around an external dependency

### 4a. Anti-Mockability-Over-Design Rule
- Do not reshape production architecture primarily to satisfy mockability.
- Testability must follow runtime ownership and design quality, not replace them.
- Do not introduce extra interfaces, facades, adapters, forwarding wrappers, or indirection layers unless they improve the runtime design independently of tests.
- If a proposed abstraction exists mainly to make internal owned code easier to mock, reject it by default and prefer a narrower seam or a real-path test strategy instead.

### 5. Test-Assembly Extension Pattern
- Prefer a test-assembly subclass or wrapper that drives real production behavior over modifying production components with broad test hooks.
- Test helpers may reveal, trigger, or observe production behavior.
- Test helpers must not reimplement production decision logic.

### 5a. Test Support Simplicity Rule
- Test support code must stay simpler than the production behavior it validates.
- Do not build a second orchestration layer, fake state machine, or mini-framework in the test suite when a narrower seam or more direct assertion would do.
- Prefer test setups and helpers that a human can understand quickly from local context.
- Reject test shapes that preserve runtime purity at the cost of making the tests themselves obscure, over-abstract, or difficult to debug.

### 6. Anti-Mirror Rule
- A test subclass, wrapper, fake, or helper is invalid by design if it duplicates production branching, fallback selection, cache policy, sequencing, or recovery logic.
- If the helper mirrors the owned runtime logic instead of exposing it, the test is measuring the helper, not the product code.

### 6a. Stale Confidence Rule
- Reject tests that can keep passing after a meaningful runtime contract regression.
- Prefer assertions on observable contract outcomes, externally visible behavior, and owned-state effects rather than indirect surrogate signals alone.
- If a test mostly proves that the scaffolding still behaves the same while the real runtime contract could have changed underneath it, the test is stale by design.

### 6b. Observability Rule
- Rare, recovery-critical, or UX-critical runtime branches should have an observable outcome that can be validated outside the test harness.
- Prefer at least one of:
  - externally visible behavior
  - explicit result state
  - stable diagnostic marker
  - contract-level side effect
- Do not rely on hidden internal branching alone for confidence in recovery or production-critical paths.

### 7. Reflection Restriction
- Reflection against private state or private method flow in tests for live production code requires explicit human approval.
- Exception:
  - legacy or static platform-bound code where a cleaner seam is disproportionate
- Even for exceptions, call the reason out explicitly. Do not normalize reflection as the default testing answer.

### 7a. Exception Protocol
- Doctrine exceptions require explicit human approval.
- Every approved exception must record:
  - what rule is being overridden
  - why a narrower seam or cleaner test shape was not sufficient
  - whether the exception is a `legacy exception` or a temporary live-code exception
  - what cleanup or removal condition would retire the exception later
- Do not silently inherit one approved exception into neighboring tests, files, or components.
- Treat exceptions as local and time-bounded unless a new explicit decision widens them.

### 8. Anti-Hook Rule
- Broad test-only delegates, hook fields, fake branches, and override matrices in shipping production code are rejected by default.
- Allow them only when the seam has clear independent runtime design value outside the test suite or when release-gating device validation makes that seam a justified production investment.

### 8a. Anti-Flake And Determinism Rule
- Flaky tests are broken validation, not weak evidence.
- Do not use blind sleeps, magic delays, race-dependent timing, or repeated reruns as the primary proof of correctness.
- When time, retries, cooldowns, or scheduling are owned by the project code, prefer deterministic control of that behavior through real seams rather than nondeterministic waiting.
- Use explicit completion markers, bounded waits, and observable contract outcomes.
- If a test passes only intermittently or only under favorable local timing, treat it as invalid until stabilized.

### 9. Editor And Runtime Parity
- For Unity runtime and platform helpers, keep editor on the same main orchestration path as production where practical.
- Represent editor behavior as a narrow policy delta such as scope selection or cache invalidation, not a separate retrieval pipeline.
- Remember that `UNITY_EDITOR` can coexist with active build-target symbols such as `UNITY_ANDROID` or `UNITY_IOS`. When the editor contract must win, order preprocessor branches explicitly.

### 10. Wrapper Contract Testing
- Test wrappers against their real default contract, not a nearby custom-configured dependency shape.
- If a wrapper binds implicitly to `Application.identifier`, engine state, or runtime-owned configuration, align the test to that default contract unless the test is explicitly about custom construction.

### 11. Persisted-State Regression Testing
- When runtime behavior depends on previously saved or cached state, cover the state transitions that actually happen in production:
  - fresh install or clean state
  - existing persisted state
  - stale or conflicting persisted state
  - recovery, reset, or migration path where applicable
- Do not treat fresh-state coverage as sufficient for persisted-state-sensitive runtime code.

## Mobile Validation Ladder

This ladder is mandatory for mobile-sensitive production changes.

### Layer 1. Pure Logic Validation
- Use EditMode or unit tests for deterministic policy, state transforms, parsing, and value-object behavior.

### Layer 2. Real Unity Orchestration Validation
- Use PlayMode or integration tests for owned runtime orchestration:
  - lifecycle handling
  - startup sequencing
  - persistence coordination
  - retry and fallback paths
  - cache invalidation
  - callback routing

### Layer 3. Native Boundary Contract Validation
- Native components may be mocked in Unity EditMode or PlayMode tests.
- These tests validate Unity-side contract and orchestration only.
- They are not proof of real Android or iOS bridge correctness.

### Layer 4. Real Native Or Device Validation
- Use device validation, smoke validation, or manual protocol for:
  - Android or iOS bridge correctness
  - native callback delivery
  - platform-owned storage behavior
  - platform lifecycle ordering
  - build-flag or stripping-sensitive flows

### Layer 5. Release-Critical Mobile Flow Validation
- Changes that affect any of the following require at least one representative runtime validation beyond fake-backed tests:
  - startup
  - pause, resume, or background behavior
  - identity and persistence
  - network recovery
  - native callback delivery
  - platform-specific compile branches

## Risk-To-Validation Mapping For Mobile-Sensitive Changes

- `pure logic or value-object change`
  - minimum bar:
    - deterministic EditMode or unit coverage
  - not enough:
    - manual reasoning only

- `owned runtime orchestration change`
  - examples:
    - retries
    - fallback selection
    - cache invalidation
    - callback routing
    - request construction
  - minimum bar:
    - real-path unit or integration coverage over the owned logic
    - PlayMode when Unity runtime behavior materially participates
  - not enough:
    - fake-heavy tests that mirror the orchestration

- `lifecycle, pause/resume, background, or startup ordering change`
  - minimum bar:
    - EditMode coverage for pure policy
    - PlayMode or integration coverage for runtime orchestration
    - at least one representative runtime validation
  - not enough:
    - EditMode-only proof

- `identity, persistence, storage, or recovery change`
  - minimum bar:
    - direct coverage of policy branches
    - integration coverage of orchestration and state reuse
    - representative runtime validation when behavior depends on persisted state, scope, installer path, or platform-owned storage behavior
  - not enough:
    - coverage of happy path only

- `native bridge, SDK wrapper, JNI, Objective-C, or Swift boundary change`
  - minimum bar:
    - fake-backed contract validation at the Unity-side boundary
    - validation of owned orchestration above the boundary
    - representative device, smoke, or manual validation for the real bridge path
  - not enough:
    - fake-backed tests alone

- `compile-flag, platform-branch, or editor-versus-runtime branch change`
  - minimum bar:
    - direct validation of the affected branch logic
    - at least one representative validation for the target branch when the behavior is mobile-sensitive
  - not enough:
    - assuming editor behavior proves non-editor branch correctness

## Closure Rule

- If a change falls into a mobile-sensitive validation bucket and the required ladder level was not executed, closure must explicitly report that validation gap.
- Do not present fake-backed success, compile success, or partial branch proof as evidence of full runtime correctness when higher validation levels are still outstanding.
- A task is not fully validated merely because the easiest available test layer passed.

## Preferred Seam Ladder

From best to worst:

1. direct real-path test with no new seam
2. real-path test through existing production contract
3. test-assembly subclass over `protected` or `virtual`
4. narrow `internal` seam
5. narrow wrapper around a true external boundary
6. reflection with explicit human approval
7. broad production test hooks

## Review Focus
- real runtime coverage versus fake-heavy coverage
- public API cleanliness
- component design cleanliness
- owned code versus boundary separation
- reflection usage on live code
- production test-hook pressure
- mobile validation ladder completeness
