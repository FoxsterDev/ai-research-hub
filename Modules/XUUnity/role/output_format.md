# XUUnity Output Format

## Default
- Scope
- Findings or plan
- Risks
- Validation

## Review Format
Use:
- Findings
- Open questions or assumptions
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate test cases when evidence is sufficient
- Scorecard
- Release recommendation or residual risk

Review findings may still use the compact table:
`Category | Issue | Severity | Remediation`

### Feature And Core-Flow Risk Assessment
For each materially affected feature, user flow, or core flow, include:
- flow or feature name
- what changed
- breakage probability from `0` to `100`
- risk class:
  - `low`
  - `moderate`
  - `high`
  - `confirmed bug`
- user impact if it breaks
- why this score was assigned

Rules:
- use `100` only when the reviewer can explain a deterministic failure from the current code or diff
- otherwise use a probability estimate and state the main assumptions
- when the change does not touch a user-visible flow directly, still score the affected technical core flow such as startup, save/load, ads, IAP, notifications, auth, or scene transitions

### QA Manual Validation Recommendations
For risky or changed flows, include:
- which scenarios QA should verify first
- device, lifecycle, network, cold-start, resume, locale, account, or config variants that matter
- what failure signal QA should watch for

### Candidate Test Cases
When the reviewer has enough code context to design strong validation, include candidate tests.
Prefer:
- concise manual test cases for high-risk flows
- automation candidates when the scenario is stable and repeatable

Each candidate test should include:
- title
- preconditions
- steps
- expected result
- recommended level:
  - `manual`
  - `integration`
  - `unit`
  - `playmode`
  - `device`

If the tests are worth writing but not included in full, explicitly say so and offer the next step.

## Knowledge Capture Format
- Problem
- Solution
- Rule
- Destination
- Confidence
