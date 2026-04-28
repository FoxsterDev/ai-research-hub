# XUUnity Review: SDK Breakage Review

## Goal
Review a third-party SDK integration as a public API breakage surface, not only as a normal code review.
Treat Unity lifecycle, scene/reload behavior, and async/threading assumptions as part of the public integration contract.

## Use For
- high-risk SDK integrations
- wrapper API review
- migration between SDK versions
- pre-release stability review
- public API misuse analysis
- test design for breakage-prone integrations

## Load First
- `skills/sdk/discovery_and_inventory.md`
- `skills/sdk/wrapper_design.md`
- `skills/sdk/callback_safety.md`
- `skills/async/main_thread.md`
- `skills/async/awaitable.md` when Unity `Awaitable` is present
- `skills/native/android_jni.md` when Android native/plugin paths exist
- `skills/native/ios_bridge.md` when iOS native/plugin paths exist
- `skills/native/callback_lifetime.md`
- `skills/tests/integration_tests.md`
- `skills/tests/smoke_and_release_checks.md`

Also load:
- `knowledge/sdk_stability_scoring.md` when the review compares upgrade candidates, connector tracks, or bundled native version lines
- `knowledge/severity_matrix.md` when the breakage review needs shared severity framing

## Review Angle
Act like:
- a rushed integrator trying to ship fast
- a realistic adversary trying to make the integration crash, hang, corrupt data, or behave inconsistently

Use at least one realistic Unity persona when shaping misuse scenarios:
- Unity junior who forgets cleanup and lifecycle ordering
- game systems engineer optimizing for performance first
- plugin integrator working across JNI or Objective-C boundaries
- mobile QA exercising permissions, backgrounding, and interruption paths
- malicious actor abusing timing, malformed input, or deep-link/native entry points

Focus on failures reachable through:
- public wrapper APIs
- configuration
- lifecycle usage
- callbacks
- threading
- integration order

Reject shallow review behavior:
- do not stop at API shape if lifecycle, reload, build, or stripping behavior is unverified
- do not accept “probably main-thread” or “probably safe” assumptions without evidence
- do not mark a review complete until misuse scenarios and test obligations are explicit

## Required Checks

### Public API Contract Map
- identify public entry points
- identify callback and event surfaces
- identify configuration objects
- identify lifecycle-sensitive APIs
- identify threading and async assumptions
- identify scene, reload, and persistence-sensitive integration points

For each public entry point, record:
- thread affinity:
  - main-thread-only / background-safe / re-entrant / unknown
- async model:
  - callback / `Task` / `Awaitable` / coroutine / sync
- lifecycle sensitivity:
  - init / shutdown / pause / resume / destroy / scene change / reload
- nullability and Unity null semantics
- order-of-operations constraints and idempotency expectations
- behavior after destroy or shutdown
- error model:
  - exception / result / callback error / silent failure risk
- stripping or AOT sensitivity
- allocation or hot-path risk if the entry point is high-frequency

### Breakage Categories
- input and argument misuse
- lifecycle and order-of-operations misuse
- concurrency and callback races
- error handling and recovery failures
- performance and resource exhaustion
- compatibility and upgrade breakage
- build and stripping risk
- mobile runtime constraints
- malicious or abuse-oriented misuse

Minimum scenario coverage:
- at least one lifecycle misuse scenario
- at least one threading or async misuse scenario
- at least one build or stripping scenario when reflection, generics, JNI, or native interop exists
- at least one abuse or stress scenario for externally reachable APIs

### Unity-Specific Checks
- Unity main-thread affinity
- Mono vs IL2CPP behavior
- managed stripping and R8 or ProGuard impact
- scene reload and `DontDestroyOnLoad`
- domain reload and static state
- background, pause, resume, and permission-sensitive behavior
- continuation thread correctness for callbacks, `Task`, `Awaitable`, or other async wrappers

### Native And Platform Checks
- JNI thread attachment and reference lifetime
- iOS native callback lifetime and thread isolation
- Android ANR risk
- iOS background and lifecycle limits

### Test Obligation Rules
- findings that can crash, ANR, corrupt state, or silently misbehave on device must include device-oriented test coverage
- findings involving IL2CPP, stripping, R8, JNI, or `__Internal` must include build-context-aware test or validation notes
- findings involving lifecycle, pause/resume, reload, or destroy behavior must include integration or playmode-style test guidance
- findings involving API spam, retry loops, polling, or callback storms must include stress or soak-style test guidance
- if no meaningful test shape is proposed, the finding is incomplete

## Severity Rules
- `Critical`
  - native crash, ANR, irreversible corruption, security-sensitive abuse, or broad release-blocking breakage
- `High`
  - common lifecycle, threading, stripping, or callback misuse that can crash, deadlock, or silently break core flows
- `Medium`
  - misuse that degrades reliability, leaks state, or causes significant but recoverable incorrect behavior
- `Low`
  - narrow edge cases, weak diagnostics, or minor contract clarity gaps without meaningful runtime danger

Raise severity by one level when:
- the issue is likely on mass-market device paths
- the issue affects startup, ads, IAP, rewards, save/load, or attribution flows
- the issue is hard to detect without explicit tests or telemetry

## Required Output
When the review is output or saved as a report, include review metadata at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`

For each finding:
- Title
- Impacted API and file paths
- Runtime and build context:
  - Editor vs device
  - Mono vs IL2CPP
  - stripping, R8, or ProGuard sensitivity if relevant
- Persona
- Category
- Severity
- Likelihood
- What breaks
- Manual repro steps
- Test case idea
- Fix recommendation

Require findings to be evidence-backed and test-case-ready.
If the claim depends on inferred behavior rather than direct code evidence, state that explicitly.

## Completion Criteria
The review is incomplete unless it includes:
- a public API contract map or an explicit statement that no meaningful public SDK surface exists
- Unity build/runtime context checks:
  - Editor vs device
  - Mono vs IL2CPP
  - stripping or R8 sensitivity when relevant
- lifecycle and teardown misuse coverage
- callback or async-threading coverage when callbacks, events, or async APIs exist
- native-boundary coverage when JNI, Objective-C, or native bridges exist
- concrete test additions for the highest-value breakage paths

The review should block release-readiness confidence when:
- critical API contracts are undocumented or unverifiable
- thread affinity is ambiguous on Unity-touching paths
- stripping/AOT/native risk exists without preservation or build validation
- top misuse scenarios have no proposed tests

## Review Output
- Public API contract risks
- realistic misuse scenarios
- missing tests for misuse and breakage paths
- top high-value breakage tests to add
- lifecycle and reload contract risks
- build-context-sensitive breakage risks
- release-blocking unknowns
