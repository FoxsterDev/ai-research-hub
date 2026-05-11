# XUUnity Low-Risk Change Categories And Exclusions Plan

Date: 2026-05-11
Status: implementation plan
Scope: allowlist and denylist model for low-risk XUUnity autonomy

## Purpose
Define which change categories may enter the reduced-review autonomy lane and which surfaces are explicitly excluded, even when the diff looks small.

This plan is intentionally conservative. It treats low-risk autonomy as an allowlist, not as a general permission model.

## Goal
Make it clear which tasks can be handled as low-risk implementation work and which tasks must remain human-reviewed or planning-only.

The result should prevent the main failure mode of autonomy systems: treating small changes as safe when they touch critical production surfaces.

## Source Constraints
- Workstream 7 requires:
  - low-risk change categories
  - explicit exclusion list
  - reduced-review clarity for tech leads
- Current XUUnity policy packs now cover high-risk repeated families:
  - SDK
  - startup
  - manifest/native
  - monetization
  - save/load
  - UI-heavy flows
- Any task that triggers one of those packs should be treated as at least `L1` unless a future approved category says otherwise.

## Allowlist Principles
A category may be autonomy-eligible only when:
- its failure mode is non-runtime or locally reversible
- it does not affect startup, SDK, native, manifest, monetization, save/load, privacy, store compliance, or user-owned state
- it has a clear file boundary
- validation is cheap and repeatable
- the final artifact can explain why the category is safe

## Proposed `L2` Eligible Categories

### Category A: Documentation And AI Reports
Eligible examples:
- system progress reports
- system health reports
- implementation plans
- protocol review summaries
- project memory draft reports
- README updates that describe existing behavior

Constraints:
- must not change executable code
- must not expose secrets or project-private details into public core
- must preserve storage rules

Expected validation:
- path placement check
- secret redaction check
- link/reference check where practical

### Category B: Public-Core Prompt Documentation With No Runtime Effect
Eligible examples:
- clarifying existing `AIRoot/Modules/XUUnity/` docs
- adding public-safe examples
- adding routing comments that do not change task behavior
- improving output format guidance

Constraints:
- no project-private identifiers
- no conflicting routing rules
- no new dead knowledge file without a route

Expected validation:
- `rg` reachability check
- public-core boundary review
- system health review when routing changes

### Category C: Test-Only Additions
Eligible examples:
- unit tests for existing owned logic
- integration tests that exercise existing public behavior
- smoke-check scripts that do not mutate production settings
- test fixtures that do not change runtime code

Constraints:
- no production behavior changes in the same autonomous commit
- no broad test-only production APIs by default
- no fake-heavy tests pretending to validate real runtime or device behavior

Expected validation:
- run the narrow test suite if available
- run test-quality self-review
- report any missing runtime/device proof

### Category D: Non-Destructive Editor Or Validation Tooling
Eligible examples:
- editor menu checks that only inspect state
- report exporters
- static validators for asset or config consistency
- project health scripts that read structure

Constraints:
- no automatic mutation of runtime settings
- no build-output mutation
- no postprocess hooks without review
- no editor-only code under runtime asmdef scope

Expected validation:
- editor assembly compile or source inspection when compile lane is unavailable
- path and asmdef boundary check
- dry-run output where possible

### Category E: Registry And Metadata Refresh With Direct Evidence
Eligible examples:
- project registry field refresh when path evidence is direct
- report index refresh
- task registry snapshot reconciliation
- AI operations metadata with append-only event rules

Constraints:
- no ambiguous project removal
- no inferred platform change without source evidence
- no lifecycle reclassification without human review
- append-only history must remain append-only

Expected validation:
- before/after registry diff
- path existence checks
- schema/shape check when available

### Category F: Isolated Non-Critical UI Wiring After Review
Eligible examples:
- label or icon binding on non-critical screen
- inspector reference wiring for non-critical presentation
- copy-only UI state labels

Constraints:
- disabled by default until the project has a clear UI ownership model
- no navigation, lifecycle, async loading, reward, ad, IAP, save/load, consent, startup, or account impact
- no changes to view/presenter ownership contracts

Expected validation:
- source inspection plus interactive validation gap statement
- promote only after repeated safe examples

## Conditional Categories
These start at `L1` and may become `L2` only after project-owner or tech-lead approval:
- editor validation tooling that can create or modify assets
- generated AI artifacts that update durable `ProjectMemory/`
- mechanical refactors inside prompt files that change routing
- test support seams near production code
- non-critical UI wiring in shared project UI layers

## Explicit Exclusions
Always exclude from reduced-review autonomy in the current phase:

### Runtime-Critical Flows
- app startup
- first interactive flow
- scene loading
- lifecycle resume or backgrounding
- threading and main-thread dispatch
- async orchestration with user-visible failure consequences

### SDK, Native, Platform, And Build
- SDK initialization
- SDK wrappers and adapters
- Android manifests
- iOS plist, entitlements, privacy manifests
- JNI, Java, Kotlin, Objective-C, Objective-C++, Swift
- native plugins
- Gradle, Xcode, resolver, and postprocess build behavior
- Unity `ProjectSettings/`
- package manifests and lock files unless the task is explicit package maintenance with human review

### Monetization, Economy, And Entitlements
- ads and rewarded flows
- IAP and purchase-adjacent entitlement logic
- ad revenue callbacks
- reward grants
- currency, inventory, economy balance
- payout, loyalty, tournament, or cashout behavior

### Save/Load, Account, And User-Owned State
- persistence schema
- migrations
- restore behavior
- cache/local/remote merge logic
- account switch and logout state
- cloud save or offline sync
- destructive reset and clear-data paths

### Compliance And Privacy
- consent
- ATT, GDPR, privacy flags
- store submission declarations
- privacy manifest behavior
- analytics identity or attribution identity changes

### Architecture And Broad Shared Runtime
- broad refactors
- shared runtime service ownership changes
- cross-module contracts
- event contracts
- observer contracts
- presenter lifetime model changes
- public API compatibility changes

## Path-Based Denylist
The implementation should include a path-sensitive denylist, with project routers allowed to add stricter local exclusions.

Usually ineligible:
- `*/Assets/Plugins/**`
- `*/ProjectSettings/**`
- `*/Packages/manifest.json`
- `*/Packages/packages-lock.json`
- `*/Assets/**/Plugins/**`
- `*/Assets/**/SDK*/**`
- `*/Assets/**/Native*/**`
- `*/Assets/**/Bootstrap*/**`
- `*/Assets/**/Startup*/**`
- `*/Assets/**/Save*/**`
- `*/Assets/**/Persistence*/**`
- `*/Assets/**/IAP*/**`
- `*/Assets/**/Ads*/**`

Usually eligible with checks:
- `AIOutput/Reports/**`
- `AIOutput/Operations/**`
- `AIRoot/Modules/XUUnity/**/*.md`
- `<Project>/Assets/AIOutput/**`
- `*/Tests/**`

Important:
- path allowlist is not sufficient by itself
- behavior classification wins over path classification
- a markdown file can still be risky if it changes routing or policy

## Required Shared Outputs
Implement as public-safe reusable core:
1. `AIRoot/Modules/XUUnity/knowledge/low_risk_change_categories.md`
2. `AIRoot/Modules/XUUnity/knowledge/autonomy_exclusions.md`
3. `AIRoot/Modules/XUUnity/tasks/start_session.md` category/exclusion routing references
4. Optional later:
   - `AIRoot/Modules/XUUnity/reviews/autonomy_gate_review.md`

## Classification Algorithm
Before treating work as `L2`, classify:
1. requested action:
   - answer
   - plan
   - implement
   - commit
   - publish
2. touched surface:
   - docs/report
   - test-only
   - editor-only
   - registry/metadata
   - production runtime
   - shared prompt routing
3. risk family:
   - none
   - SDK
   - startup
   - manifest/native
   - monetization
   - save/load
   - UI-heavy
   - privacy/store
4. allowlist result:
   - allowlisted
   - conditional
   - not allowlisted
5. exclusion result:
   - no exclusion
   - path exclusion
   - behavior exclusion
   - policy-pack exclusion

Decision:
- if any exclusion exists, route to `L1`
- if conditional, route to `L1` unless the user or owner explicitly approves
- if allowlisted and no exclusion exists, allow `L2`

## Acceptance Criteria
The deliverable is done when:
- allowed categories are explicit and narrow
- exclusions cover all current policy-pack families
- path and behavior denylist rules are both present
- conditional categories do not silently become `L2`
- start-session can explain why a task is or is not autonomy-eligible
- project routers can add stricter local exclusions without editing public core

## Validation Plan
Use sample tasks to test classification:
- write a system report -> `L2` eligible
- update a project memory draft -> conditional
- add a unit test only -> `L2` eligible if no production changes
- modify startup code -> excluded
- modify an ad callback -> excluded
- modify a save migration -> excluded
- update README routing text -> conditional or `L2` depending on behavior impact
- update `Packages/manifest.json` -> excluded by default

Expected result:
- no production-critical task reaches `L2` by default
- docs/test/report work can reach `L2` with validation artifacts
- ambiguous prompt-routing edits remain review-visible

## Rollout Plan
1. Add category and exclusion knowledge files.
2. Wire them into start-session only for implementation or commit/publish requests.
3. Run system health review for knowledge reachability.
4. Use the classifier on at least five real tasks.
5. Adjust allowlist only after repeated clean outcomes.

## Risks
- overbroad allowlist can route unsafe work into reduced review
- path rules can miss behavior risk
- agents may treat `AIRoot` markdown as always safe even when routing changes are material

## Controls
- deny by default
- behavior classification overrides path classification
- policy-pack trigger prevents default `L2`
- final answer must report the autonomy decision and validation gap
