# XUUnity Git Change Review Report

## Review Metadata
- Date: `2026-08-26 08:58:58 -03`
- Repo: `AIRoot`
- Target project: `Modules/XUUnity`
- Branch: `master`
- Commit: `e8f792865b8d4cb2c4df799cc1a3da62e642489e`
- Review type: `Git change review`
- Review scope: four unstaged Markdown changes under `Modules/XUUnity/` (`17` insertions, `0` deletions)
- Comparison base: `origin/master` at the same commit as `HEAD`; committed branch delta is empty
- Included local delta: `yes`; unrelated local edits outside `Modules/XUUnity/` were excluded
- Comparison-base project memory: the `HEAD` versions of the four changed files
- Branch-derived candidate evidence: the local evidence-provenance, UI-closeout, PlayMode-loop, and testing-doctrine additions
- Independent approval: `none`
- Unresolved evidence conflicts: dirty-worktree identity, non-code editor freshness, PlayMode-loop scope, and UI-specific authorization ownership

## Findings

| Severity | File | Issue | Why It Matters | Recommended Fix |
| --- | --- | --- | --- | --- |
| Medium | `Modules/XUUnity/knowledge/unity_validation_boundaries.md:42` | The prescribed artifact identity cannot prove the common dirty-worktree case and treats editor recompilation as the generic freshness signal. A player built from uncommitted edits still reports the pre-fix `HEAD`; a timestamp does not prove which dirty content was built. Recompilation also does not prove that a changed scene, prefab, texture, UXML, or other imported asset was saved and loaded. | The rule can reject valid pre-commit evidence or accept stale/non-matching content while claiming provenance. That weakens the exact guarantee the section is intended to add. | Define identity by change type: commit plus clean/dirty state and a diff/content digest or emitted build manifest for player artifacts; compile completion for scripts; import/save/hash or persisted scene/prefab identity for non-code editor assets. State explicitly that timestamps are supporting metadata, not content identity. |
| Medium | `Modules/XUUnity/skills/tests/playmode_tests.md:23-25` | The loop applies to anything visible at runtime, then universally requires a failing PlayMode reproduction with a payload injected through an existing seam. This includes copy-only/static visual changes and interaction defects that need no external payload, despite the same skill reserving PlayMode for behavior that cannot be trusted in pure tests and the UI policy excluding forced automation for pure visual/copy work. | Agents may manufacture an unnecessary test seam, declare a false capability gap, or spend PlayMode cost on claims that a narrower lane can prove. That conflicts with the anti-hook and anti-overdesign doctrine. | Narrow the trigger to claims that depend on live scene wiring, input, lifecycle, async ordering, or rendered runtime state. Make injection conditional: when controlled external input is required, use an existing production-valid boundary; otherwise drive the real user/input path. Preserve manual or static evidence for pure copy/visual cases. |
| Medium | `Modules/XUUnity/skills/tests/playmode_tests.md:29` | A generic PlayMode skill imports the UI-heavy pack's plan-approval gate for every runtime evidence loop, even though the skill also covers gameplay integration and the UI pack has explicit trigger conditions. The companion addition in `ui_heavy_changes.md:86` further states that approval gates the first run without defining how an existing user request for validation execution satisfies that gate. | Non-UI PlayMode work can be routed through an inapplicable policy, and already-authorized validation can stop for a redundant approval. Different agents can reasonably reach opposite authorization decisions from the same text. | Keep the approval rule in the UI-heavy pack and scope it to newly designed UI smokes. Put any general PlayMode authorization rule in a common execution contract. Define whether an explicit user request to execute validation is sufficient and when a materially changed smoke plan needs fresh approval. |

## Open Questions And Assumptions
- Assumed `origin/master` is the intended integration base because no `develop` ref exists and `master` tracks `origin/master` with `0/0` divergence.
- Assumed the new evidence rules are intended to support validation before commit, which is the normal state for implementation and local Git-change review.
- No runtime code, synchronization primitive, state owner, wrapper, or production test seam changed; complexity-budget delta is `none` for those categories.

## Quality Score
- Overall score: `67 / 100`
- Distance from top tier: `23`
- Scope note: score applies only to the reviewed 17-line protocol delta if landed, not to XUUnity as a whole.
- Scoring confidence: `Medium`; the textual evidence is complete and guardrails ran, but the changed semantic paths have no executable contract coverage.
- Reweighting note: security/privacy and runtime data integrity are out of scope. Weight was redistributed toward protocol correctness, boundary ownership, validation confidence, evidence operability, and project fit.

## Dimension Breakdown

| Dimension | Weight | Score | Why |
| --- | ---: | ---: | --- |
| Protocol correctness | 30 | 70 | The intent is sound, but the identity and runtime-loop rules overclaim their applicable proof surface. |
| Architecture and ownership clarity | 20 | 68 | Evidence ownership improves, while UI-specific approval leaks into the generic PlayMode owner. |
| Validation and release confidence | 30 | 60 | Existing guardrails pass, but they do not exercise dirty builds, asset-only changes, loop routing, or authorization semantics. |
| Observability and operability | 10 | 75 | Retrievable evidence is explicitly required, though the identity recipe is incomplete. |
| Simplicity, project fit, maintainability, and change safety | 10 | 65 | The new loop is concise, but its unconditional payload and approval rules create avoidable workflow branching. |

## Product Interpretation
The change is moving toward stronger proof, but it is not reliable enough to become shared policy yet. In common pre-commit, asset-only, non-UI, and no-payload cases, agents can either stop valid work or record evidence under the wrong identity.

## Supplementary Change-Review Lenses
- Core-flow safety: `not applicable`; no player/runtime core-flow implementation changes.
- Project fit: `62 / 100`; the cross-file rules conflict with existing lane-selection, anti-hook, and UI-pack boundaries.
- QA readiness: `58 / 100`; current protocol tests pass but do not cover the newly introduced semantics.

## Feature And Core-Flow Risk Assessment

| Flow | What Changed | Breakage Probability | Risk Class | User Impact | Reasoning |
| --- | --- | ---: | --- | --- | --- |
| Validation evidence attribution | Adds mandatory artifact identity rules | 70 | high | Reviewers may accept stale evidence or reject valid pre-commit evidence | Dirty builds and non-code Unity changes are routine, but the prescribed identity signals do not cover them. |
| Runtime-visible regression validation | Adds mandatory red/green PlayMode loop | 60 | moderate | Implementation closeout can become unnecessarily expensive or blocked | The trigger and payload rule are broader than the established PlayMode and UI-policy boundaries. |
| Validation authorization routing | Reuses UI approval in generic PlayMode guidance | 45 | moderate | Agents may pause already-authorized work or apply UI rules to gameplay | The owner and satisfaction condition for approval are not defined consistently. |

## QA Manual Validation Recommendations

| Priority | Scenario | Variants | What To Verify | Failure Signal |
| --- | --- | --- | --- | --- |
| P0 | Apply the provenance rule to a player built from an uncommitted script fix | clean `HEAD`; dirty working tree; same commit with different diffs | The evidence record uniquely identifies the actual built content | Timestamp and `HEAD` are the only identity, or two different dirty builds look identical |
| P0 | Apply the provenance rule to an asset-only Unity change | scene; prefab; UXML; texture/import setting | The rule identifies saved/imported content without requiring irrelevant C# compilation | Recompile is treated as proof that the asset change is present |
| P1 | Route a visible interaction defect with no external payload | button wiring; navigation; local animation | Real input can provide the red/green without inventing an injection seam | The workflow demands a fake payload or reports a capability gap |
| P1 | Route a gameplay-visible PlayMode regression | UI-heavy pack inactive; explicit validation request present/absent | Only applicable authorization policy is loaded and the approval decision is deterministic | Generic gameplay work inherits the UI-smoke gate or two agents make opposite decisions |
| P2 | Route a copy-only or static visual correction | localization string; static label; art-only change | The narrowest representative evidence is allowed | A mandatory failing PlayMode test is required despite no runtime behavioral claim |

## Candidate Test Cases

| Title | Level | Preconditions | Steps | Expected Result |
| --- | --- | --- | --- | --- |
| Dirty-worktree evidence identity contract | Protocol guardrail | Temporary commit plus two distinct uncommitted diffs | Evaluate the documented identity fields for both builds | Records differ without relying on timestamp alone |
| Asset-only editor freshness contract | Protocol guardrail | Scene/prefab edit with no script compile | Apply the evidence rule | Saved/imported artifact identity is required; compilation is not treated as sufficient |
| Conditional runtime input injection | Protocol guardrail | One remote-data UI case and one local button-wiring case | Route both through the loop | Only the remote-data case requires controlled boundary input |
| Authorization ownership matrix | Protocol guardrail | UI/non-UI crossed with validation requested/not requested | Resolve the first-run rule | One unambiguous owner and outcome exists for each case |

## Validation Performed
- `git diff --check -- Modules/XUUnity`: passed.
- `python3 -m unittest discover -s Modules/XUUnity/scripts/tests -p 'test_protocol_guardrails.py' -v`: 6/6 passed.
- `system_installation_audit.py --skip-composed-checks`: completed with pre-existing findings outside the reviewed XUUnity files; no changed-file link finding was reported.

## Release Recommendation
- Verdict: `proceed after targeted fixes`
- Why: the direction is good, but all three findings can alter agent behavior in realistic validation workflows.
- Required next actions: make artifact identity dirty-worktree and asset-aware; narrow the Runtime Evidence Loop and conditionalize payload injection; give PlayMode authorization one correctly scoped owner; add focused protocol guardrails for those semantics.
