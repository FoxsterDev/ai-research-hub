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

## Output
- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment:
  - `Flow | Breakage Probability | Risk Class | Why It Can Break | User Impact`
- QA manual validation recommendations
- Candidate test cases when evidence is sufficient
