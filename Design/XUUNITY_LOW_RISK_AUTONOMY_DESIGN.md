# XUUnity Low-Risk Autonomy Design

Date: 2026-04-02
Status: proposed operating design
Scope: portfolio-wide low-risk autonomy lane for AI-assisted work

## Goal
Define a low-risk autonomy model that protects production stability first.

Primary operating posture:
- zero new crash risk
- zero new ANR risk
- no autonomous edits to runtime-critical production paths

This document treats "low-risk autonomy" as a strict allowlist system, not as broad agent freedom.

## Core Principle
The safest 2026 best practice for production-facing AI automation is:
- allow autonomy only on pre-classified safe surfaces
- deny autonomy by default everywhere else
- require artifact generation and human approval before merge

The model should assume that any change touching startup, threading, SDK initialization, manifests, native bridges, monetization core flows, save/load, or consent can create crash, ANR, compliance, or revenue risk.

## Zero-Risk Interpretation
Absolute zero engineering risk does not exist.

For this portfolio, "zero-risk for prod" means:
- the autonomy lane must exclude all known crash-sensitive and ANR-sensitive surfaces
- autonomous work must be constrained to changes whose failure mode cannot realistically create production crashes, freezes, ANRs, or corrupted live behavior
- merge remains human-gated

## Recommended Autonomy Levels
- `L0`
  - answer only
- `L1`
  - analyze and propose
- `L2`
  - implement only on strict low-risk allowlist, then generate validation artifacts
- `L3`
  - disabled for production code in the current portfolio state

Recommended portfolio default:
- all projects default to `L1`
- `L2` is opt-in per change category
- `L3` is off

## Non-Negotiable Denylist
Autonomy must not modify these areas without explicit human escalation:

### Runtime-Critical
- app startup and bootstrap
- async orchestration with failure consequences
- background-to-main-thread handoff logic
- scene loading critical path
- save/load and persistence
- session lifecycle

### Platform And Native
- Android manifests
- iOS plist, entitlements, privacy manifests
- JNI, Java, Kotlin
- Objective-C, Objective-C++, Swift
- native plugin bridges
- postprocess build scripts

### SDK And Compliance
- ads SDK initialization
- analytics initialization
- attribution SDK behavior
- consent and privacy logic
- push notification initialization
- IAP and purchase flows
- payout, cashout, or geo-eligibility flows

### Product Safety
- reward-granting logic
- economy balances
- tournament or loyalty submission logic
- remote-config-sensitive core flow logic

### Operational Safety
- broad refactors across shared runtime layers
- portfolio-wide prompt changes without review
- any change with uncertain blast radius

## Strict Allowlist For L2
Only these categories are eligible for low-risk autonomous implementation:

### Category A: Documentation And AI Artifacts
- `AIRoot` docs
- project memory summaries
- AI audit reports
- SDK inventory summaries
- backlog and review notes

Why safe:
- no runtime production effect

### Category B: Tests Without Runtime Logic Changes
- new unit tests
- new integration tests
- new smoke-check definitions
- test-only helper code

Guardrail:
- tests may reference production code
- tests may not modify production behavior as part of the same autonomous change

### Category C: Editor-Only Validation Tooling
- editor validation utilities
- report exporters
- static analyzers for config or asset consistency
- non-runtime inspectors that do not alter build output automatically

Guardrail:
- no implicit mutation of runtime settings
- no post-build mutation

### Category D: Isolated Non-Critical UI Wiring
- purely presentational UI binding
- label text hookups
- icon hookups
- layout-safe inspector references

Guardrail:
- must not affect navigation contract
- must not affect rewarded flow, purchase flow, consent flow, or startup flow

### Category E: Local Config Surface With No Runtime Criticality
- non-sensitive dev tooling config
- AI operation config
- reporting config

Guardrail:
- excludes Unity `ProjectSettings`, manifests, SDK config, build config, and any runtime-loaded remote/local config that changes app behavior

## Explicit Exclusions From L2
Even if a change looks small, it is excluded from the autonomy lane if it touches:
- `Assets/Plugins/`
- `ProjectSettings/`
- build templates
- bootstrap or startup folders
- ad trigger or reward-granting logic
- observer event contracts
- SDK adapters
- shared hub runtime layers

## Required Validation Contract For L2
Every autonomous `L2` change must produce:

1. Scope classification
- state why the change is inside the allowlist

2. Touched-surface report
- list touched files
- confirm denylist surfaces were not touched

3. Validation report
- tests run, if any
- static checks run, if any
- manual verification points if runtime execution was not possible

4. Risk note
- expected failure mode
- why it does not create crash/anr-sensitive production risk

5. Human merge gate
- no autonomous merge to protected branches

## Routing Rules
Before entering `L2`, the system should classify the task:

### Route To L0/L1 Automatically
- if the task is exploratory
- if requirements are ambiguous
- if runtime ownership is unclear

### Block L2 Automatically
- if touched files intersect denylist paths
- if the change affects runtime-critical control flow
- if the change modifies shared product logic
- if the change changes user-visible monetization or recovery behavior

### Allow L2 Only When All Are True
- changed files are in allowlist paths
- blast radius is local
- no runtime-critical surfaces are touched
- validation artifact can be generated
- human approval is present before merge

## Path-Based Policy
Recommended safe default path policy:

### Usually Eligible
- `AIRoot/**`
- `*/Assets/AIOutput/**`
- `*/Tests/**`
- editor-only validation tooling paths after manual review

### Usually Ineligible
- `*/Assets/_*/Scripts/**`
- `*/Assets/Bootstrapper/**`
- `*/Assets/ThirdPartiesAdapters/**`
- `*/Assets/Plugins/**`
- `*/Packages/**`
- `*/ProjectSettings/**`

## Why Crash And ANR Risk Stay Low
This model keeps the autonomy lane away from:
- startup deadlocks
- background-thread misuse
- SDK callback issues
- manifest and native integration failures
- runtime reward/economy regressions

In other words:
- autonomy is allowed on documentation, tests, and carefully bounded tooling
- autonomy is denied on the surfaces most likely to create production incidents

## Promotion Policy
No category should move into broader autonomy until it has:
- multiple successful low-risk executions
- stable validation rules
- no production regressions attributable to that category
- explicit owner approval

Recommended promotion sequence:
1. docs and AI artifacts
2. tests
3. editor validation tooling
4. tightly bounded UI wiring

Do not promote startup, SDK, manifest, native, consent, monetization, or save/load into autonomy-safe categories in the current portfolio phase.

## Interaction With Future MCP / Tooling Automation
External tooling automation should consume this policy, not bypass it.

That applies to future integrations such as:
- Jira task intake and status updates
- Unity batch verification
- GitLab or Bitbucket PR creation
- automated report publication

Recommended rule:
- external automation may prepare, classify, and report
- external automation may not bypass the denylist or merge gate

## Initial Deliverables
1. `AIOutput/Registry/project_registry.yaml`
2. `AIRoot/Modules/XUUnity/knowledge/autonomy_levels.md`
3. `AIRoot/Modules/XUUnity/knowledge/low_risk_change_categories.md`
4. `AIRoot/Modules/XUUnity/knowledge/autonomy_exclusions.md`
5. `start_session.md` routing note for autonomy classification

## Registry Interaction
The autonomy layer should treat `AIOutput/Registry/project_registry.yaml` as the portfolio metadata index.

Recommended rule:
- low-risk autonomous updates to the registry are allowed only for evidence-backed metadata refreshes
- registry updates should be triggered automatically during portfolio/system reviews when stale fields are obvious from current repo structure
- destructive registry edits such as project removal or ambiguous reclassification require human review

## Recommended Portfolio Default Today
- docs and AI artifacts: `L2`
- tests: `L2`
- editor validation tooling: `L1` by default, `L2` only after owner approval
- all production runtime code: `L1`
- startup, SDK, native, manifest, monetization, and persistence: human-reviewed only

## Success Criteria
- no autonomous change can realistically introduce a new crash or ANR through allowed categories
- autonomy saves engineering time on low-value routine work
- every autonomous change leaves an auditable artifact trail
- merge authority remains human-controlled
