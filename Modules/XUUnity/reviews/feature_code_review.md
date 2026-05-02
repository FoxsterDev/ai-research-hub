# XUUnity Review: Feature Code

## Check
- Behavior regressions
- Incorrect assumptions
- Async and state management risks
- Optimistic UI versus authoritative server or backend state reconciliation risks
- Whether repeated actions are blocked until authoritative state arrives when the UI moves ahead optimistically
- Whether temporary interaction blocking scope matches reconciliation scope instead of unnecessarily disabling unrelated items
- Whether full snapshot reconciliation prunes missing entities and recomputes section availability from current visible state
- Allocation and performance costs
- Missing tests or missing validation coverage
- Whether the testing approach follows the mobile validation ladder instead of stopping at fake-backed confidence
- Feature and core-flow breakage probability
- Whether any path is already a deterministic bug
- Manual QA scenarios needed to validate the changed flow
- For Unity lifecycle wrappers, whether raw engine signals are separated from derived consumer-facing state
- For consumer-facing lifecycle enums, whether states express product meaning instead of raw callback-order combinations
- Whether Android transient focus loss can be mistaken for real backgrounding
- Whether iOS save behavior relies on quit instead of focus-loss or pause-safe paths
- Whether `Application.lowMemory` handling is bounded and idempotent enough for repeated pressure
- Whether `DontDestroyOnLoad` runtime-service integration tests were placed in PlayMode rather than forced into EditMode
- Whether testability was achieved without unnecessary test-only pollution of production APIs
- Whether hard-to-reach branch coverage was pursued through broad test-only hooks that should have been rejected in favor of narrower policy, boundary, or contract tests
- Whether tests on live production code use reflection over private state or private methods without an explicit human decision and a clear justification for why a smaller seam was not the better answer
- Whether mocks or fakes were used for owned production orchestration that should have remained real
- Whether test subclasses or wrappers only expose production behavior instead of mirroring production logic
- Whether editor execution follows the same main orchestration path as runtime production code when validating shared runtime helpers
- Whether preprocessor branch order is correct when `UNITY_EDITOR` can coexist with platform-target symbols
- Whether wrapper tests validate the wrapper's real default contract instead of a nearby custom-configured dependency shape
- For Unity-facing realtime transports or callback pipelines that can burst or fan out heavily, whether heavy ingress work stays off the main thread and whether backlog is bounded and budgeted instead of being drained unbounded on one frame
- For open-if-installed or install-if-missing flows, whether installed-app identity is modeled separately from store-destination identity instead of one overloaded field being used for both
- For SDK-driven external-open flows, whether fallback order preserves both UX quality and attribution opportunity instead of jumping straight to a blunt direct-store fallback

## Output
When the review is output or saved as a report, include review metadata at the top:
- `Date`
- `Repo`
- `Target project`
- `Branch`
- `Commit`
- `Review type`

- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment:
  - `Flow | Breakage Probability | Risk Class | Why It Can Break | User Impact`
- QA manual validation recommendations
- Candidate test cases when evidence is sufficient
