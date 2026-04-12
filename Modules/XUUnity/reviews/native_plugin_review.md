# XUUnity Review: Native Plugin

## Check
- Ownership and memory lifetime
- JNI or ARC correctness
- thread affinity
- callback deregistration
- marshaling cost
- API validity for the supported platform range
- core-flow breakage probability for the user journeys that depend on the bridge
- deterministic bug versus probabilistic bridge instability
- manual QA scenarios for lifecycle, backgrounding, resume, permissions, and callback timing

## Output
- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate device or integration test cases when evidence is sufficient
