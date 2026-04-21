# XUUnity Review: SDK Integration

## Check
- Initialization order
- Threading model
- callback ownership
- callback dispatch ownership
- cleanup ownership
- strategy-versus-platform responsibility split
- launch or policy decisions implemented too low in the stack
- privacy and store declarations
- dependency version risk
- version and connector inventory accuracy
- startup cost and repeated bridge crossings
- public API misuse risk
- wrapper contract quality
- lifecycle and order-of-operations misuse
- test coverage for hangs, malformed data, retries, and callback-thread issues
- merged manifest or plist drift when build tooling can rewrite declarations
- feature and core-flow risk for startup, consent, ads, IAP, attribution, auth, notifications, or resume flows touched by the SDK
- deterministic bug versus probabilistic breakage assessment
- manual QA scenarios needed for risky integration paths

## Output
- Findings table:
  - `Category | Issue | Severity | Remediation`
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate manual or automation test cases when evidence is sufficient

## Escalate To
If the integration is high-risk or breakage-prone, also load:
- `reviews/sdk_breakage_review.md`

Also load `knowledge/sdk_stability_scoring.md` when the review compares SDK versions, wrapper releases, bundled native SDKs, or connector-track choices.
