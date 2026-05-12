# XUUnity Workstream 3 Policy-Pack Coverage Prompt: Master

Use this in a fresh chat from the monorepo root when you want one pass that creates all three missing policy packs consistently.

```text
xuunity implement the next Workstream 3 policy-pack coverage slice.

Repo: host monorepo
Target project for validation context: a representative Unity consumer project
Target shared files to create:
1. AIRoot/Modules/XUUnity/reviews/policy_packs/monetization_changes.md
2. AIRoot/Modules/XUUnity/reviews/policy_packs/save_load_changes.md
3. AIRoot/Modules/XUUnity/reviews/policy_packs/ui_heavy_changes.md

Task:
Load the repo router, the current XUUnity start-session flow, the current system health baseline, and the current system progress baseline. Then create these 3 missing policy packs as public-core shared review overlays.

Working-context rule:
- You may use relevant working artifacts from the host monorepo, including audits, review artifacts, SDK reviews, code reviews, knowledge drafts, and system reports, when they help derive stronger policy-pack content.
- You may use all existing shared and internal XUUnity skills, reviews, utilities, and knowledge files already present in the monorepo.
- Load only the narrowest relevant artifacts and skills.
- If historical artifacts conflict with current shared prompts or current source, current shared prompts and current source win.
- Do not leak project-private details into new public-core policy packs; promote only reusable public-safe review logic.
- Before writing the new policy packs, inspect the narrowest relevant existing artifacts in the host monorepo for monetization, save/load, and UI-heavy review patterns, and reuse any public-safe review logic that is already proven there.

Required outcome:
- Each file must be production-usable, not placeholder text.
- Each pack must define:
  - when it should be loaded
  - trigger signals / routing hints
  - main review questions
  - required evidence
  - validation expectations
  - common failure modes
  - release-risk framing
  - what must be reported in the final review
- Keep them additive and narrow. They are policy-pack overlays, not full standalone review protocols.
- Match the house style and depth of:
  - AIRoot/Modules/XUUnity/reviews/policy_packs/sdk_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/startup_changes.md
  - AIRoot/Modules/XUUnity/reviews/policy_packs/manifest_native_changes.md
- Use current roadmap and execution-plan intent as source constraints:
  - AIRoot/Roadmaps/AI_AUTOMATION_ROADMAP.md
  - AIRoot/Roadmaps/AI_AUTOMATION_EXECUTION_PLAN.md
- Update shared routing only if needed so these new packs are actually reachable from start-session behavior.
- Do not broaden the stack unnecessarily.
- Do not rewrite unrelated shared prompts.
- Preserve the public-core vs internal-overlay boundary.

Expected substance:
- monetization_changes.md should cover ads, rewarded flows, purchase-adjacent monetization hooks, revenue callback sequencing, consent/startup interactions, payout/reward integrity, and rollout-sensitive monetization regressions.
- save_load_changes.md should cover persistence ownership, serialization boundaries, migrations, absent-vs-explicit-field semantics, stale/local/remote merge risk, restore contracts, compatibility envelope, and corruption/loss risk.
- ui_heavy_changes.md should cover long-lived screens, popup/flow presenters, lifecycle re-entry, first-visible-state truthfulness, async loading/UI orchestration, state ownership, and interactive validation expectations.

Validation:
- Verify the files are consistent with the existing policy-pack style and reachable by the current routing model.
- If you update routing, keep the change minimal and explain exactly why.
- Summarize any remaining gap if there is a routing decision you chose not to encode.

Final answer format:
1. What you created
2. Any routing updates made
3. Why the pack boundaries are correct
4. Validation performed
5. Remaining gaps or follow-ups
```
