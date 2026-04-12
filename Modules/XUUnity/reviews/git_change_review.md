# XUUnity Review: Git Change

## Goal
Review a concrete git change set as a production-risk surface, not only as isolated code snippets.

Use this review when the user wants:
- a review of current staged or unstaged changes
- a review of commits on the current branch
- a review of a feature branch against `develop`
- a judgment on whether the change is safe to move toward production

## Diff Source Rule
Choose the review scope in this order:
1. If the user names specific commits, a commit range, or another explicit comparison target, review that explicit git scope.
2. Otherwise, review the branch change against `develop` using the merge base.
3. If staged or unstaged local changes also exist, review them as an additional uncommitted delta unless the user explicitly asked for committed changes only.
4. If `develop` does not exist or the repository uses another integration branch, detect the intended integration branch. If that remains ambiguous, stop and ask instead of assuming the wrong base.

Default expectation:
- if instructions do not say otherwise, evaluate the change relative to `develop`
- if local working-tree changes exist, call them out separately from the committed branch diff

Do not silently review the wrong comparison base or mix unrelated local edits into the main verdict.

## Review Angle
Treat the change as something that may:
- regress existing behavior
- break critical flows
- degrade startup, runtime, ANR, or battery posture
- violate project boundaries or shared patterns
- be technically correct but still not production-ready

Prefer critical review over approval-seeking summary.

## Load First
- `tasks/code_review.md`
- `reviews/feature_code_review.md`
- `reviews/architecture_review.md` when boundaries or ownership changed materially
- `reviews/release_readiness_review.md` when rollout or production safety is in question
- relevant `skills/` based on the changed code surface

## Required Checks

### Diff Integrity
- identify the actual files changed
- identify the effective comparison base
- distinguish branch-vs-`develop` changes from local working-tree changes
- exclude unrelated local edits from the main verdict when they are outside the intended review scope
- call out when review confidence is reduced because the diff scope may be incomplete
- if the branch diff is too large for a trustworthy single-pass review, split it into review areas, state reduced confidence, and avoid giving a false-green release verdict

### Large Diff Triage
Use explicit triage when the branch diff is broad enough that a single verdict would be shallow.
Signals include:
- many files across multiple subsystems
- mixed protocol, tooling, project-router, and product-code changes in one branch
- a diff size large enough that line-by-line review confidence is obviously reduced

When this happens:
- partition the review by change area first
- name which areas were reviewed deeply versus only sampled
- lower `release_readiness` when full review coverage is not yet credible
- prefer `needs another review pass` over a confident production-safe verdict

### Risk Review
- behavior regressions
- critical flow risk
- crash and ANR exposure
- async, callback, and lifecycle safety
- allocation, performance, and startup cost
- architecture and ownership drift
- missing tests or weak validation
- code style and maintainability issues
- project-pattern compliance
- feature and core-flow breakage probability
- whether any issue is a deterministic bug versus a probabilistic regression risk
- what manual QA must verify before release confidence is credible
- whether the reviewer can already propose strong manual or automated test cases

### Production Readiness
- can this go to production as-is
- what blocks release confidence
- what requires staged rollout, guardrails, or extra validation
- what is acceptable technical debt versus unacceptable release risk

## Required Output
1. Findings first, ordered by severity.
2. Concrete file references and why the issue matters.
3. Suggested fixes or safer alternatives.
4. A scorecard.
5. Feature and core-flow risk assessment.
6. QA manual validation recommendations.
7. Candidate test cases when evidence is sufficient.
8. A release recommendation.

## Persistent Review Report
After running this review for a concrete project, also save a short durable report under the project-local AI output tree:
- `<Project>/Assets/AIOutput/CodeReviews/`

The saved report should be concise and PR-friendly:
- review scope
- comparison base
- included local delta, if any
- top findings
- feature and core-flow risk summary
- QA validation summary
- scorecard
- release recommendation

Use the canonical short template:
- `AIRoot/Templates/XUUNITY_GIT_CHANGE_REVIEW_TEMPLATE.md`

Preferred saved report shape:

```md
# XUUnity Git Change Review Report

## Review Metadata
- Date:
- Project:
- Review scope:
- Comparison base:
- Included local delta:

## Findings
- `Severity | File | Issue | Why It Matters | Recommended Fix`

## Scorecard
- Risk:
- Architecture:
- Quality:
- Code style:
- Project fit:
- Release readiness:
- Core-flow safety:
- QA readiness:

## Feature And Core-Flow Risk Assessment
- `Flow | What Changed | Breakage Probability | Risk Class | User Impact | Reasoning`

## QA Manual Validation Recommendations
- `Priority | Scenario | Variants | What To Verify | Failure Signal`

## Candidate Test Cases
- `Title | Level | Preconditions | Steps | Expected Result`

## Release Recommendation
- Verdict:
- Why:
- Required next actions:
```

Use collision-safe filenames.
Preferred shape:
- `YYYY-MM-DD_HH-MM-SS_git_change_review_<branch_slug>_vs_<base_slug>.md`

Normalization rules:
- replace spaces and slashes with `_`
- keep branch and ref names short but recognizable
- if the review includes local uncommitted changes, append `_with_local_delta`
- if branch or base names are unavailable, use stable fallbacks such as `working_tree` or `unknown_base`

Do not overwrite an earlier review report from the same day.
Each run should produce its own timestamped file so the project keeps a review trail for later PR work.

## Scorecard
Score each area from `0` to `100`:
- `risk`
- `architecture`
- `quality`
- `code_style`
- `project_fit`
- `release_readiness`
- `core_flow_safety`
- `qa_readiness`

Interpretation:
- `90-100`
  - strong
- `75-89`
  - acceptable with visible caveats
- `60-74`
  - risky, should not move forward without fixes
- `<60`
  - not production-ready

Scoring anchors:
- `risk`
  - lower when crash, ANR, lifecycle, rollback, or critical-flow exposure is visible
- `architecture`
  - lower when ownership, dependency direction, or subsystem boundaries degrade
- `quality`
  - lower when correctness, invariants, or validation quality degrade
- `code_style`
  - lower when readability, consistency, or maintainability regress materially
- `project_fit`
  - lower when the change conflicts with established project patterns, memory, or protocol expectations
- `release_readiness`
  - lower when tests, observability, rollout safety, or production confidence are insufficient
- `core_flow_safety`
  - lower when the diff touches startup, monetization, save/load, ad flow, IAP, auth, notifications, deep links, scene transitions, reward paths, or other core flows with visible breakage risk
- `qa_readiness`
  - lower when the review cannot map clear manual validation scenarios, or when risky scenarios are visible but not yet covered by tests or explicit QA checks

## Feature And Core-Flow Risk Scoring
For each changed feature or core flow, include:
- `breakage_probability`
  - `0-100`
- `risk_class`
  - `low`
  - `moderate`
  - `high`
  - `confirmed bug`
- `impact`
  - what the player, operator, or release process loses if this breaks
- `reasoning`
  - why the score was assigned

Anchors:
- `0-24`
  - low visible breakage chance
- `25-49`
  - plausible regression, should be checked
- `50-74`
  - likely breakage under realistic usage
- `75-99`
  - very likely breakage or release pain
- `100`
  - use only when the current change proves a deterministic bug or guaranteed failure under stated conditions

Do not claim `100% bug` from intuition alone.
State the exact assumption if the bug is deterministic only under a specific lifecycle, platform, or config.

## QA Validation Layer
For the changed area, include:
- priority manual scenarios
- environment variants that matter
- what to verify on success
- what failure signal QA should watch for

If you can derive strong tests from the code, propose them directly.
If writing them would be high leverage but needs user approval or more context, say that explicitly.

## Release Recommendation
End with one of:
- `safe to proceed`
- `proceed after targeted fixes`
- `needs another review pass`
- `not ready for production`

## Output Format
Use:
- Findings
- Open questions or assumptions
- Scorecard
- Feature and core-flow risk assessment
- QA manual validation recommendations
- Candidate test cases when useful
- Release recommendation
