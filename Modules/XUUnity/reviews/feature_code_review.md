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

## Output
- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment:
  - `Flow | Breakage Probability | Risk Class | Why It Can Break | User Impact`
- QA manual validation recommendations
- Candidate test cases when evidence is sufficient
