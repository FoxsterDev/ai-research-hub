# XUUnity Workstream 3 Policy-Pack Prompt: Monetization

Use this in a fresh chat when you want to create only the monetization policy pack.

```text
xuunity create a new shared policy pack:
AIRoot/Modules/XUUnity/reviews/policy_packs/monetization_changes.md

Goal:
Implement a public-core XUUnity review overlay for risky monetization changes.

Context:
- Follow the style and scope discipline of the existing policy packs:
  - AIRoot/Modules/XUUnity/reviews/policy_packs/sdk_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/startup_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/manifest_native_changes.md
- Align with the roadmap and execution plan, which explicitly call for a monetization policy-pack family.
- This is a shared reusable file in AIRoot, so keep it public-safe and project-agnostic.
- You may use relevant existing host monorepo review artifacts, audits, SDK reviews, code reviews, knowledge drafts, and all already-existing XUUnity shared/internal skills when they help derive stronger public-safe policy-pack logic.
- Reuse proven review patterns, but do not copy project-private details into AIRoot.

The pack should cover at minimum:
- ads
- rewarded flows
- interstitial / rewarded timing risks
- reward-grant integrity
- double-grant / missed-grant failure modes
- IAP-adjacent monetization hooks when relevant
- consent / startup / SDK-readiness interactions that affect monetization correctness
- ad revenue callbacks / ordering / identity / attribution-sensitive consequences when applicable
- rollout-sensitive monetization regressions
- required validation and release-risk framing

Deliverable quality bar:
- not a generic essay
- not a duplicate of sdk/startup policy packs
- must act as an additive review-routing overlay
- must tell the agent what to inspect, what evidence to demand, and what to call risky

If needed, make the smallest routing update so the new file is reachable from start-session logic for monetization-sensitive tasks. Keep any routing edit narrow and justified.

Final answer:
- created file(s)
- routing changes, if any
- why the policy-pack boundary is correct
- validation performed
- remaining follow-up
```
