# XUUnity Review: Full Review

## Goal
Run the widest relevant review bundle over a target and then synthesize one stability-first verdict.

This is an orchestration review.
It does not replace narrower reviews.
It assembles them, reuses shared evidence, deduplicates overlapping findings, and produces one production-priority summary.

## Use For
- whole-project or whole-package audits
- `review all`
- `full review`
- pre-release confidence sweeps
- high-risk SDK or native integration audits
- branch or package state reviews where the user wants the broadest credible review surface in one pass

## Load First
- `knowledge/review_quality_scoring.md`
- `knowledge/severity_matrix.md`
- `knowledge/risk_classification.md`
- relevant project memory
- relevant prior reports only when they materially reduce uncertainty or help compare repeated findings

## Scope Classification Contract
Before assembling the bundle, classify the target on two axes.

### Axis 1: review target kind
- `current_state_sdk`
- `current_state_feature`
- `current_state_project`
- `change_sdk`
- `change_feature`
- `change_project`

Use:
- `current_state_*` when the user asks to review the current codebase, package, project, or subsystem as it exists now
- `change_*` when the user asks to review a diff, PR, branch delta, commit range, or a described change proposal

### Axis 2: dominant risk families
- `sdk_sensitive`
- `startup_sensitive`
- `manifest_native_sensitive`
- `core_flow_sensitive`
- `release_sensitive`

Rules:
- classify every full review target explicitly
- list the chosen target kind and active risk families in the report metadata or assumptions
- if evidence is mixed, keep more than one active risk family instead of flattening to one vague label

## Policy-Pack Activation Rules
Full review must integrate the existing policy-pack system instead of bypassing it.

Activate:
- `reviews/policy_packs/sdk_changes.md` when `sdk_sensitive` is active
- `reviews/policy_packs/startup_changes.md` when `startup_sensitive` is active
- `reviews/policy_packs/manifest_native_changes.md` when `manifest_native_sensitive` is active

Policy-pack rules:
- use the packs to strengthen stack assembly and validation expectations
- do not blindly duplicate every layer from every active pack
- when more than one pack is active, merge them by missing coverage only
- list active packs in the full-review report

If no policy pack is active:
- state that explicitly
- explain why the target does not justify SDK, startup, or manifest-native escalation

## Review Assembly Rules
Full review means all relevant review protocols for the target, not blind loading of every review file.

Always include:
- `reviews/architecture_review.md`
- `reviews/delivery_risk_review.md`
- `reviews/release_readiness_review.md`

Choose one primary code-surface review:
- `reviews/sdk_code_review.md` for SDKs, packages, wrappers, public APIs, integrations, and reusable service layers
- `reviews/feature_code_review.md` for gameplay, UI, feature-flow, or product-surface code without a dominant SDK-wrapper boundary

Add breakage-oriented overlays when relevant:
- `reviews/sdk_breakage_review.md` when public SDK surface, wrapper contract, upgrade sensitivity, misuse exposure, or integration-order risk exists
- `reviews/native_plugin_review.md` when JNI, Objective-C, Swift, plugins, manifests, plist, entitlements, or device-only bridge behavior exists
- `reviews/git_change_review.md` when the review target is an explicit diff, PR, commit range, or branch delta rather than only current state

## Deterministic Bundle Matrix
Use this matrix before applying judgment-call heuristics.

### Required by target kind
- `current_state_sdk`
  - required:
    - `architecture_review`
    - `sdk_code_review`
    - `delivery_risk_review`
    - `release_readiness_review`
  - conditional:
    - `sdk_breakage_review` when public API, wrapper contract, or misuse exposure exists
    - `native_plugin_review` when native or build-merged device surfaces exist
- `current_state_feature`
  - required:
    - `architecture_review`
    - `feature_code_review`
    - `delivery_risk_review`
  - conditional:
    - `release_readiness_review` when rollout or production safety is part of the ask
    - `native_plugin_review` when native, manifest, or plist-sensitive code is in the feature surface
    - `sdk_code_review` only when the feature is mainly a wrapper or vendor integration surface
- `current_state_project`
  - required:
    - `architecture_review`
    - `delivery_risk_review`
    - `release_readiness_review`
  - conditional:
    - `sdk_code_review` for SDK-heavy projects
    - `feature_code_review` for feature-heavy projects
    - `sdk_breakage_review` when public integration contracts dominate project risk
    - `native_plugin_review` when device or merged-artifact correctness is material
- `change_sdk`
  - required:
    - `git_change_review`
    - `architecture_review`
    - `sdk_code_review`
    - `delivery_risk_review`
    - `release_readiness_review`
  - conditional:
    - `sdk_breakage_review`
    - `native_plugin_review`
- `change_feature`
  - required:
    - `git_change_review`
    - `feature_code_review`
    - `delivery_risk_review`
  - conditional:
    - `architecture_review` when ownership or boundaries materially change
    - `release_readiness_review` when stable production or rollout safety is part of the question
    - `native_plugin_review` when native or merged-artifact sensitivity exists
    - `sdk_code_review` when the change primarily affects an SDK boundary
- `change_project`
  - required:
    - `git_change_review`
    - `architecture_review`
    - `delivery_risk_review`
    - `release_readiness_review`
  - conditional:
    - `sdk_code_review`
    - `feature_code_review`
    - `sdk_breakage_review`
    - `native_plugin_review`

### Required by risk family
- `sdk_sensitive`
  - force:
    - `sdk_code_review`
  - strongly prefer:
    - `sdk_breakage_review`
- `startup_sensitive`
  - force:
    - `release_readiness_review`
    - `delivery_risk_review`
- `manifest_native_sensitive`
  - force:
    - `native_plugin_review`
    - `release_readiness_review`
- `release_sensitive`
  - force:
    - `release_readiness_review`
- `core_flow_sensitive`
  - force:
    - `delivery_risk_review`

### Conflict resolution
- if target-kind requirements and risk-family requirements disagree, keep the broader bundle
- if both `sdk_code_review` and `feature_code_review` appear plausible, choose the one that matches the dominant boundary and explicitly justify not running the other
- if uncertainty about whether native or merged-artifact behavior matters is material, include `native_plugin_review`
- if uncertainty about public contract misuse matters, include `sdk_breakage_review`

Default bundles by target shape:
- whole mobile SDK package:
  - `architecture_review`
  - `sdk_code_review`
  - `sdk_breakage_review`
  - `native_plugin_review` when native paths exist
  - `delivery_risk_review`
  - `release_readiness_review`
- whole feature or subsystem:
  - `architecture_review`
  - `feature_code_review`
  - `delivery_risk_review`
  - `release_readiness_review`
  - `native_plugin_review` only when native or manifest-sensitive code is part of the feature
- explicit change review:
  - `git_change_review`
  - plus the relevant architecture, feature, SDK, breakage, native, and release overlays from the changed surface

Rules:
- if both SDK and native/plugin surfaces exist, run both `sdk_code_review` and `native_plugin_review`
- if public contract misuse is a meaningful risk, include `sdk_breakage_review` even when `sdk_code_review` already ran
- do not run irrelevant reviews only to maximize count
- record skipped reviews explicitly with the reason
- for every review that is skipped despite being plausible, write the suppression reason in one line:
  - `not relevant`
  - `subsumed by stronger review`
  - `target kind mismatch`
  - `insufficient evidence but risk accepted`
  - `user explicitly excluded`

## Execution Order
1. Define target scope:
   - repo, project, package, feature, subsystem, or explicit change set
2. Determine git metadata:
   - `Date`
   - `Repo`
   - `Target project`
   - `Branch`
   - `Commit`
3. Classify target kind and active risk families
4. Activate policy packs
5. Assemble the review bundle:
   - list reviews that will run
   - list reviews skipped and why
6. Build one shared evidence inventory:
   - architecture boundaries
   - critical flows
   - native and build surfaces
   - public APIs
   - tests and validation surface
7. Run the selected sub-review passes
8. Normalize all findings into one canonical issue list
9. Produce one stability-first synthesis, release verdict, and overall quality score using `knowledge/review_quality_scoring.md`

## Review Artifact Contract
- Follow `reviews/review_artifact_contract.md`.
- Use `utilities/report_export.md` for the destination map.

## Bundle Rationale Contract
The full review must leave behind a clear audit trail for why each protocol was or was not run.

For every protocol in the candidate set, record:
- status:
  - `run`
  - `skipped`
- why:
  - one sentence tied to target kind, risk family, or evidence
- what unique signal it was expected to contribute

If another reviewer cannot reconstruct the bundle from the report, the full review is incomplete.

## Canonical Finding Merge Rules
When two or more review passes report the same root cause:
- output one canonical finding, not duplicated findings
- keep the strongest justified severity
- keep every contributing review in the finding provenance
- preserve the strongest production-impact framing
- explicitly mark whether the issue is:
  - confirmed deterministic bug
  - reproducible high-probability breakage risk
  - plausible but still inference-heavy risk
  - validation or coverage gap

Do not split one root cause into multiple findings only because:
- architecture and release reviews describe it differently
- native and SDK reviews see different consequences of the same defect
- one review frames it as design debt and another frames it as ship risk

## Evidence Contract
Every canonical finding must include:
- affected files, flows, or APIs
- evidence refs:
  - file paths with line references when available
  - build artifact or runtime context when source alone is insufficient
- finding class:
  - confirmed deterministic bug
  - reproducible high-probability breakage risk
  - plausible inference-heavy risk
  - validation or coverage gap
- stable-production consequence:
  - crash
  - ANR
  - broken startup
  - broken monetization
  - broken lifecycle
  - silent wrong state
  - release blocker
  - maintainability only
- confidence:
  - `high`
  - `medium`
  - `low`
- validation obligation:
  - what must be tested, built, or manually verified next

Preferred but optional when evidence exists:
- shortest plausible repro
- rollback or mitigation hint

If a grouped or canonical finding lacks enough evidence to guide triage, it is not ready for the full-review summary.

## Protocol Disagreement Rules
If sub-reviews disagree on severity, root cause, or release impact:
- keep the disagreement visible in the condensed protocol notes
- use the strongest severity that is directly justified by evidence
- if the stronger severity depends on inference, keep that severity but lower confidence and say why
- never silently average disagreements into a softer summary

## Stability-First Prioritization Rules
Stable production without bugs is the default objective.

Group and order the canonical findings like this:
1. release blockers, confirmed bugs, crashes, ANRs, irreversible corruption, privacy or store blockers
2. startup, threading, native bridge, lifecycle, and core monetization breakage risks
3. high-probability core-flow regressions, callback contract failures, and silent wrong-state risks
4. architecture, ownership, and test-surface gaps that can hide production breakage
5. lower-risk maintainability, clarity, and consistency findings

Inside each group, sort by:
- `Critical` before `High`, `Medium`, `Low`
- deterministic bug before probabilistic risk
- broader user impact before narrower impact
- harder-to-detect issues before obvious issues

Never bury a confirmed production bug below a cleaner but less dangerous architecture observation.

## Required Output
For any saved review artifact, include the base metadata from `reviews/review_artifact_metadata.md`, plus:
- `Review scope`
- `Target kind`
- `Active risk families`
- `Policy packs active`
- `Review bundle run`
- `Review bundle skipped`

The final output must contain:
- a stability-first executive summary
- bundle rationale:
  - which protocols were considered
  - which were run
  - which were skipped and why
- the list of review protocols actually run
- the list of skipped review protocols with reasons
- a canonical findings summary table:
  - `Priority band | Group | Severity | Confidence | Finding class | Affected reviews | Evidence refs | Root issue | Why stable prod cares | Required action`
- grouped findings from most critical to least critical
- condensed per-protocol notes:
  - what that protocol added that others did not
  - what unknowns remain
- QA manual validation recommendations
- candidate automated or device test cases
- final release recommendation

When saving, prefer:
- `AIRoot/Templates/XUUNITY_FULL_REVIEW_REPORT_TEMPLATE.md`

By default:
- produce one aggregate report as the primary artifact
- do not emit separate per-protocol markdown files unless the user asks for them or the review is too large to remain readable

## Completion Criteria
The review is incomplete unless it:
- states the assembled review bundle and skipped protocols explicitly
- states target kind, active risk families, and active policy packs explicitly
- deduplicates overlapping findings into canonical root-cause findings
- prioritizes output for stable production rather than by protocol order
- makes release blockers and confirmed bugs obvious at the top
- distinguishes deterministic bugs from design debt and from validation gaps
- makes evidence strength and confidence explicit for canonical findings
- includes concrete QA or test follow-up for the highest-risk findings

The review should block release confidence when:
- a high-risk relevant sub-review was skipped without a solid reason
- the aggregate summary hides protocol disagreement or unresolved uncertainty
- critical native, startup, threading, or monetization risks remain unvalidated
