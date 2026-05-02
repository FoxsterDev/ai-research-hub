# XUUnity Review: Test Quality

## Goal
Review the quality of a test suite or a selected group of tests against the canonical testing doctrine and produce a concrete cleanup, refactor, improvement, or deletion plan.

This review is not about whether tests merely exist.
It is about whether the tests create real production confidence without polluting runtime design, public API shape, or project cognition.

## Use For
- `xuunity review tests`
- reviewing existing tests before refactoring or cleanup
- scoring the quality of a feature, package, or project test suite
- identifying fake-heavy, empty, brittle, stale, or low-value tests
- finding worked-example candidates for the doctrine after a real review

## Load First
- `skills/tests/testing_doctrine.md`
- relevant `skills/tests/` files for the test types involved
- relevant project memory
- relevant current production code, not only the tests

## Scope Classification
Classify the review target before scoring.

### Axis 1: target scope
- `single_test`
- `single_test_file`
- `feature_test_surface`
- `package_test_surface`
- `project_test_surface`

### Axis 2: dominant test surface
- `unit_heavy`
- `integration_heavy`
- `playmode_heavy`
- `native_boundary_heavy`
- `persisted_state_heavy`
- `mixed`

### Axis 3: dominant risk
- `low_confidence_fake_heavy`
- `runtime_design_pollution`
- `stale_contract_risk`
- `mobile_validation_gap`
- `legacy_exception_surface`

State the chosen classifications in the report.

## Review Questions

### Real Runtime Confidence
- Does the suite exercise real owned production code?
- Are rare but UX-critical branches covered where they matter?
- Are owned orchestration paths kept real, or were they displaced by mocks or mirrored helpers?

### Design Cleanliness
- Did testability pollute the public API?
- Did the tests pressure the production design into extra interfaces, facades, hooks, or indirection that exist mainly for mocking?
- Are test seams narrow and runtime-valid?

### Test Quality
- Are tests elegant, readable, and understandable to a human without reconstructing a second framework?
- Do the tests assert observable contract outcomes instead of weak surrogate signals?
- Could the tests keep passing after a meaningful runtime regression?
- Are there tests that mostly validate mocks, fake environments, or test scaffolding instead of product behavior?

### Mobile Validation Fit
- Does the suite satisfy the mobile validation ladder appropriate for the changed risk?
- For native or platform-sensitive areas, is there clarity about what is fake-backed contract validation versus real runtime/device validation?
- For persisted-state-sensitive behavior, do tests cover more than fresh-state happy paths?

### Deletion Pressure
- Which tests are effectively empty?
- Which tests are redundant happy-path noise?
- Which tests only prove that mocks or fake env wiring still matches itself?
- Which tests should be deleted rather than improved?

## Scoring Model

Score each reviewed test or test group on a `0-100` scale.

### 90-100
- strong real-path confidence
- narrow seams
- no design pollution
- readable and maintainable
- good doctrine alignment

### 75-89
- useful test
- some quality issues or incomplete validation depth
- should usually be improved, not deleted

### 50-74
- mixed value
- partial confidence, brittle scaffolding, weak assertions, fake-heavy structure, or shallow branch selection
- usually requires refactor or replacement

### 25-49
- low-value test
- mostly validates scaffolding, fake environment, or duplicated logic
- strong candidate for replacement or deletion

### 0-24
- empty, misleading, stale, or doctrine-violating
- should normally be deleted

## Decision Ladder

Every scored item must end with one explicit next-step decision:

- `keep`
- `improve`
- `refactor`
- `replace with real-path test`
- `delete`
- `keep as legacy exception`
- `promote as worked example candidate`

Rules:
- choose `delete` for empty or confidence-faking tests
- choose `replace with real-path test` when the current test shape is fake-heavy or mirrored
- choose `keep as legacy exception` only when the review explicitly justifies the exception
- choose `promote as worked example candidate` only for genuinely strong doctrine-aligned tests

## Review Process
1. Define the review target:
   - package, feature, folder, file, or explicit test list
2. Read the production code that the tests claim to validate.
3. Group tests by behavioral surface instead of file name only:
   - pure logic
   - runtime orchestration
   - lifecycle
   - persisted state
   - native boundary
   - wrapper contract
4. For each test or meaningful test cluster:
   - identify the real owned code under test
   - identify fake or mocked boundaries
   - identify any design pollution added for the test
   - identify whether the assertions are contract-level or surrogate-level
   - identify whether the test would likely survive a meaningful runtime regression
5. Score the test or cluster.
6. Assign the decision ladder outcome.
7. Build cleanup themes across the reviewed set:
   - delete noise
   - refactor scaffolding
   - replace fake-heavy tests with real-path tests
   - strengthen branch coverage for UX-critical paths
   - add missing runtime validation where doctrine requires it
8. Identify strong tests that may become doctrine worked examples after cleanup.

## Output
When the review is output or saved as a report, include review metadata at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`
- `Target scope`
- `Dominant test surface`
- `Dominant risk`

Then include:

### 1. Suite Verdict
- overall score
- biggest strengths
- biggest weaknesses
- immediate cleanup recommendation

### 2. Test Score Table
Use this table shape:

`Test Target | Score | What Is Good | What Is Weak | Doctrine Failure Or Risk | Next-Step Decision`

Rules:
- the `Test Target` may be one test, one file, or one tightly related test cluster
- do not hide low-value tests inside an averaged file score if they need deletion

### 3. Cleanup Plan
- `Delete`
- `Replace With Real-Path Tests`
- `Refactor Scaffolding`
- `Improve Coverage Of Rare UX-Critical Branches`
- `Add Missing Mobile Validation`

### 4. Worked Example Candidates
- list any tests worth preserving as doctrine examples
- explain why they are strong
- prefer real reviewed project tests over invented examples
- prioritize candidates that close current doctrine blind spots or strengthen underrepresented patterns
- do not create example artifacts automatically unless the user asks for extraction

## Default Findings Bias
- prefer calling out misleading confidence over celebrating high test counts
- prefer deleting low-value tests over preserving them for coverage optics
- prefer runtime confidence, readability, and design cleanliness over theoretical branch count
