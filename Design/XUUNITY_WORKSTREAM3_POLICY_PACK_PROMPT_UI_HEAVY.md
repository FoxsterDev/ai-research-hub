# XUUnity Workstream 3 Policy-Pack Prompt: UI Heavy

Use this in a fresh chat when you want to create only the UI-heavy policy pack.

```text
xuunity create a new shared policy pack:
AIRoot/Modules/XUUnity/reviews/policy_packs/ui_heavy_changes.md

Goal:
Implement a public-core XUUnity review overlay for risky UI-heavy changes.

Context:
- Follow the style and scope of the current policy packs:
  - AIRoot/Modules/XUUnity/reviews/policy_packs/sdk_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/startup_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/manifest_native_changes.md
- Align with roadmap/execution-plan intent for a UI-heavy policy-pack family.
- Keep it public-core safe and reusable, not tied to monorepo-private presenter implementation details.
- You may use relevant existing Apperfun monorepo review artifacts, audits, SDK reviews, code reviews, knowledge drafts, and all already-existing XUUnity shared/internal skills when they help derive stronger public-safe policy-pack logic.
- Reuse proven review patterns, but do not copy project-private details into AIRoot.

The pack should cover at minimum:
- long-lived screens
- popup / modal / one-shot flow UIs
- first-visible-state truthfulness
- async loading and UI gating
- lifecycle re-entry and resume behavior
- duplicate open / duplicate close / stuck state risks
- ownership of view state vs backing state
- network-dependent progression vs UI entry contract
- user-visible sequencing regressions
- interactive validation expectations
- release-risk framing

Important:
- this is not a UI style guide
- it is a review-routing overlay for regression-prone UI changes
- keep it compatible with both generic Unity UI work and presenter-driven flow review
- if routing should recognize UI-heavy changes more explicitly, make the smallest justified update

Final answer:
- created file(s)
- routing changes, if any
- why the policy-pack boundary is correct
- validation performed
- remaining follow-up
```
