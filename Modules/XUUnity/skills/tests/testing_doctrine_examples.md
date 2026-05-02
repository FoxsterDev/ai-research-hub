# Skill: Testing Doctrine Examples

## Purpose
Provide compact worked examples for the canonical testing doctrine.

Use these examples to recognize strong versus weak test shapes before adding seams, mocks, wrappers, or test-only production changes.

Prefer sourcing new worked examples from real reviewed project tests rather than inventing them abstractly.
If a reviewed project test is genuinely strong and closes a current doctrine blind spot, promote that real example instead of fabricating a cleaner but less representative sample.

## Good Examples

### 1. Test-Assembly Subclass Over A Narrow Production Seam
Good shape:
- production component exposes a narrow `protected`, `protected virtual`, or `internal` seam with real runtime value
- test assembly adds a subclass that triggers or observes the real production behavior
- the test executes the owned production branching and assertions are made on contract-level outcomes

Why good:
- real owned logic stays real
- public API is not widened for tests
- no broad test-only production hooks are needed

### 2. Mocked Native Boundary With Real Unity Orchestration
Good shape:
- JNI, Objective-C, Swift, vendor SDK, or keychain shell is faked or mocked
- Unity-side orchestration above that boundary remains real
- test verifies retry policy, callback routing, state recovery, or request shaping through real owned code

Why good:
- the closed boundary is isolated correctly
- the owned runtime behavior is still under real execution
- test confidence targets the code the team actually owns

### 3. Persisted-State Matrix Test
Good shape:
- the suite covers:
  - fresh install
  - existing persisted state
  - stale or conflicting persisted state
  - recovery or reset path
- assertions are made on runtime-visible outcomes, not only on storage helper internals

Why good:
- aligns with real production state transitions
- catches upgrade, cache, and recovery regressions early

## Bad Examples

### 4. Public `...ForTests` API
Bad shape:
- production component adds a public setter, flag, or control method only so tests can force internal state

Why bad:
- pollutes public API
- weakens component design for test convenience
- often hides the need for a narrower seam or a better real-path test

### 5. Mirrored Fake Logic
Bad shape:
- test helper or fake reproduces production branching, fallback choice, retry ordering, or cache logic
- the test passes because the mirrored helper and the expected assertion drift together

Why bad:
- creates stale confidence
- validates the test scaffolding more than the product behavior

### 6. Reflection Over Live Code Without Approval
Bad shape:
- test uses reflection to mutate private state or invoke private flow in live production code
- no explicit human exception decision is recorded

Why bad:
- bypasses doctrine approval
- usually signals a missing seam or an overreaching test goal

### 7. Fake-Heavy Orchestration Test
Bad shape:
- most owned runtime collaborators are mocked
- only thin forwarding code remains real
- assertions prove that mocks were called rather than that user-visible runtime behavior is correct

Why bad:
- low production confidence
- easy to keep green through regressions in real runtime behavior

## Review Heuristics

When comparing two test shapes, prefer the one that:
- executes more real owned production logic
- uses fewer production test hooks
- keeps assertions closer to observable runtime outcomes
- stays readable without building a second framework in the tests
- leaves fewer opportunities for stale confidence after refactors
