# XUUnity Workstream 3 Policy-Pack Prompt: Save Load

Use this in a fresh chat when you want to create only the save/load policy pack.

```text
xuunity create a new shared policy pack:
AIRoot/Modules/XUUnity/reviews/policy_packs/save_load_changes.md

Goal:
Implement a public-core XUUnity review overlay for risky save/load and persistence changes.

Context:
- Match the style and discipline of the existing policy packs:
  - AIRoot/Modules/XUUnity/reviews/policy_packs/sdk_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/startup_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/manifest_native_changes.md
- Align with roadmap/execution-plan requirements for a save/load policy-pack family.
- Keep it public-safe and reusable across Unity projects.
- You may use relevant existing Apperfun monorepo review artifacts, audits, SDK reviews, code reviews, knowledge drafts, and all already-existing XUUnity shared/internal skills when they help derive stronger public-safe policy-pack logic.
- Reuse proven review patterns, but do not copy project-private details into AIRoot.

The pack should cover at minimum:
- persistence ownership
- serialization boundaries
- migration risk
- compatibility envelope
- corrupted / partial / missing data handling
- absent field vs explicit field semantics
- cache / local / remote merge boundaries
- startup restore behavior
- runtime overwrite and stale-write risk
- destructive reset / clear-data risk
- data loss, duplication, regression, and silent fallback failure modes
- validation and release-risk framing

Important:
- incorporate the repo’s shared decision-rule posture around partial-update semantics and merge boundaries
- keep the file additive and narrow as a policy-pack overlay
- make the review operational: what to inspect, what to prove, what to report

If routing needs a small update so save/load-sensitive work can load this pack, make the smallest safe change and explain it.

Final answer:
- created file(s)
- routing changes, if any
- why the policy-pack boundary is correct
- validation performed
- remaining follow-up
```
