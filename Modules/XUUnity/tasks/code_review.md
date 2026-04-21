# XUUnity Task: Code Review

## Goal
Review code for production risk in Unity and native integration paths.

## Focus
- Bugs and regressions first
- Threading and ownership risk
- Allocation and performance cost
- Missing tests or missing validation coverage
- Feature and core-flow breakage risk
- QA validation needs for changed user journeys
- Callback ownership, dispatch ownership, and cleanup ownership
- Policy or launch-mode decisions living at the wrong layer
- Strategy-versus-platform boundary drift in SDK and native wrapper code

## Output
- Findings ordered by severity
- Open questions
- Feature and core-flow risk assessment with breakage probability
- QA manual validation recommendations
- Candidate test cases when the reviewer has enough evidence
- Residual risk
