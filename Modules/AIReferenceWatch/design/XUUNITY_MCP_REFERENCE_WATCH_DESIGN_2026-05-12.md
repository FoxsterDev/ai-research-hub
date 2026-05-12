# XUUnity MCP Reference Watch Design

Date: `2026-05-12`
Status: design proposal
Scope: public `AIReferenceWatch` module plus future
`AIRoot/Operations/ReferenceWatch/` implementation surface and host-local
comparison workflow

## Goal

Add a public-safe reference and comparison layer through the
`AIReferenceWatch` module and future `AIRoot/Operations/ReferenceWatch/`
surface so the team can:

1. track other Unity MCP and Unity AI automation tools
2. compare their current feature surface with `XUUnity Light Unity MCP`
3. understand feature gaps against competing solutions
4. know which repo is the best reference for a given feature, workaround, or
   implementation pattern
5. monitor external issue patterns and verify whether the same failure mode
   exists in `XUUnity`
6. measure progress over time against a stable comparison baseline

This design is intentionally separate from the UI primitive contract design.
This document defines how to watch, normalize, compare, and consume references.
The sibling UI primitives design consumes those outputs.

Related design:
- `AIRoot/Operations/XUUnityLightUnityMcp/Designs/XUUNITY_MCP_UI_PRIMITIVES_DESIGN_2026-05-12.md`

Authoritative durable doctrine:
- `AIRoot/Modules/AIReferenceWatch/knowledge/reference_selection_doctrine.md`

## Inputs Reviewed

The following public references were inspected as design inputs:

- `https://github.com/r1n7aro/Locus`
- `https://github.com/AlexMerzlikin/unity-agent-team`
- `https://github.com/IvanMurzak/Unity-MCP`
- `https://github.com/codergamester/mcp-unity`
- `https://github.com/AndreySkyFoxSidorov/UnifiedUnityMCP`
- `https://github.com/CoplayDev/unity-mcp`
- `https://github.com/Donchitos/Claude-Code-Game-Studios`
- `https://github.com/TheArcForge/UniClaude`

High-level takeaways:

- `unity-agent-team` is a useful reference for broader agent workflow framing
  around Unity work and may become more relevant as `AIReferenceWatch` expands
  beyond MCP-only comparison.
- `Unity-MCP` from Ivan Murzak is a strong reference for broad tool-surface
  design, install/distribution workflow, and large built-in command catalogs.
- `mcp-unity` exposes a broad scene/GameObject/component tool surface and useful
  resource surfaces.
- `unity-mcp` from Coplay has grouped tools such as `manage_ui`,
  `manage_build`, `manage_scene`, `manage_profiler`, and multi-instance
  routing.
- `UniClaude` shows the value of a large typed tool surface plus in-editor
  workflow integration.
- `Locus` is interesting more for runtime analysis, knowledge retention, and
  semantic editor operations than for minimal MCP design.
- `UnifiedUnityMCP` is useful as a reference for UI/layout automation concepts,
  even though a large part of its public messaging is skill-oriented rather than
  a compact tool protocol.
- `Claude-Code-Game-Studios` is better as an orchestration/workflow reference
  than as a direct Unity MCP capability reference.

## Recommendation Summary

ReferenceWatch should optimize for competitive engineering value, not for
maximal repo collection.

The primary goals are:

- understand the feature gap between `XUUnity` and other Unity MCP solutions
- know which reference is strongest for a given feature or workaround
- know which active repos are worth checking before designing a new capability
- monitor external issue patterns and verify whether the same failure mode exists
  in `XUUnity`
- measure progress over time against a stable comparison baseline

## Reference-First Design Rule

New public MCP feature design in `AIRoot` should normally be
`reference-informed` before the public contract is finalized.

This does not mean "copy another repo first". It means:

1. check whether tracked references already solve the same problem
2. identify the strongest `overall` and `capability` leaders for that area
3. compare command surface, constraints, and failure modes
4. decide explicitly what to borrow, what to reject, and what to do differently

The rule exists to reduce two recurring failures:

- inventing a weaker contract than existing references already proved out
- missing known failure modes that other tools already exposed through issues or
  workarounds

## Reference Adoption Rule

Reference code or patterns must never be copied blindly.

Use references only when all of the following are true:

- the idea solves a real `XUUnity` problem or closes a meaningful gap
- the source shows acceptable quality for the relevant area
- the pattern fits `XUUnity` architecture, safety, and contract style
- the team can explain why this reference is better than designing from first
  principles for this case

Required posture:

- use references to sharpen our own design
- use references to inspect tradeoffs and workarounds
- use references to validate or challenge our API direction
- do not mirror another repo's surface only because it exists
- do not copy another repo's implementation without a fresh design decision

Quality checks before borrowing from a reference should include:

- contract clarity
- evidence quality
- failure semantics
- maintainability
- fit for `XUUnity` users
- absence of hidden runtime or safety costs

## When Reference Review Is Required

Reference review is required before:

- adding a new public MCP operation family
- adding a new public command namespace such as `unity.ui.*`
- broadening an existing tool surface in a way that changes public contracts
- adding a new public workflow surface intended for reuse across repos

Reference review is not required for:

- small internal bug fixes
- local refactors that do not change public behavior
- implementation-only hardening of an existing contract
- host-local project hooks or monorepo-only wrappers

## Minimum Reference Review Output

Before a new public MCP feature is accepted for design, produce a short review
artifact with:

- `featureArea`
- current `XUUnity` state
- `overallLeaders`
- `capabilityLeaders`
- notable issue themes from references
- candidate contract options
- recommended direction
- explicit `borrow / reject / differentiate` notes

This can stay lightweight. The point is to force a deliberate look at the
market before public contract design, not to create heavy process.

## Public AIRoot Addition

Add a public-safe folder under:

- `AIRoot/Operations/ReferenceWatch/`

This folder should contain reusable contracts, schemas, and optional generic
scripts. It should not contain host-private paths, mutable machine-local state,
or secrets.

Recommended structure:

```text
AIRoot/Operations/ReferenceWatch/
  README.md
  feature_bag_schema.json
  reference_source_schema.json
  examples/
    reference_sources.example.yaml
    feature_bag.example.json
  prompts/
    compare_feature_bags.md
    extract_reference_feature_bag.md
  scripts/
    normalize_reference_repo.py
    compare_feature_bags.py
```

This is public-safe because:

- it defines how to compare tools
- it does not embed private repos or credentials
- it can be reused in other repos

## Source Registry And Mutable Outputs

Keep the reusable source registry in the public module:

- `AIRoot/Modules/AIReferenceWatch/reference_sources.yaml`

Consuming repos should keep mutable crawler outputs outside `AIRoot`.
Recommended host-local output structure:

```text
<host-output-root>/ReferenceWatch/
  snapshots/
  normalized/
  reports/
```

Reason for the split:

- public `AIRoot` should hold the reusable method and public source registry
- host-local output roots should hold snapshots and generated comparisons

## Reference Source Config

The crawler should use a typed source config.

Example:

```yaml
schemaVersion: xuunity.reference-sources.v1

sources:
  - id: locus
    kind: github_repo
    url: https://github.com/r1n7aro/Locus
    defaultBranch: main
    enabled: true
    tags: [unity, runtime-analysis, editor-agent]

  - id: unity_agent_team
    kind: github_repo
    url: https://github.com/AlexMerzlikin/unity-agent-team
    defaultBranch: main
    enabled: true
    tags: [unity, agents, workflow, orchestration]

  - id: unity_mcp_ivanmurzak
    kind: github_repo
    url: https://github.com/IvanMurzak/Unity-MCP
    defaultBranch: main
    enabled: true
    tags: [unity, mcp, broad-tool-surface, cli, runtime]

  - id: mcp_unity_codergamester
    kind: github_repo
    url: https://github.com/codergamester/mcp-unity
    defaultBranch: master
    enabled: true
    tags: [unity, mcp, scene-tools]

  - id: unity_mcp_coplay
    kind: github_repo
    url: https://github.com/CoplayDev/unity-mcp
    defaultBranch: main
    enabled: true
    tags: [unity, mcp, ui-tools, build-tools]
```

Each source entry should support:

- repo URL
- default branch
- pinned commit for reproducible comparison runs when a snapshot matters
- enabled/disabled
- tags
- optional preferred docs paths
- optional ignore paths
- optional extraction targets such as:
  - MCP server entrypoints
  - tool registration files
  - operation registry files
  - Unity package folders
  - schema or manifest files
- optional parser strategy override
- optional license notes when downstream implementation reference may be taken
- optional issue-watch config such as:
  - labels of interest
  - bug-only filtering
  - open-issue sampling limit
  - keywords for areas like `ui`, `playmode`, `build`, `transport`, `crash`
- classification fields such as:
  - `tier`
  - `candidateStrength`
  - `focusAreas`
  - `leadingCapabilities`
  - `watchMode`

## Crawler Pipeline

The system should be deterministic and cheap to rerun.

### Step 1: Fetch

Fetch reference materials from:

- README
- docs folder
- package manifest
- tool schemas or server spec files when they exist
- operation registries and handler entrypoints
- Unity package `Editor/` tool surfaces and registration code when present

Do not fetch entire git history by default.
Do fetch enough source files to verify whether a claimed capability is actually
implemented.

### Extraction Policy

Do not use one generic extraction strategy for all repos.

Required source categories:

- documentation surface
  - `README`
  - `docs/`
  - wiki pages when they are clearly part of the public contract
- protocol surface
  - MCP tool schema
  - server manifest
  - transport registration
- implementation surface
  - MCP server entrypoint
  - tool registry
  - operation handler files
  - Unity package source for editor/runtime tools

Each reference source should resolve to a parser strategy such as:

- `docs_only`
- `manifest_plus_code_registry`
- `unity_package_code_scan`
- `manual_review_required`

If a repo does not expose enough structure for reliable automated extraction,
the normalized output must say so explicitly and reduce confidence.

### Step 2: Snapshot

Store raw fetched artifacts under host-local `snapshots/`.

Each snapshot should record:

- source id
- fetch timestamp
- source commit or page revision when available
- fetched file list
- parser strategy used
- fetch warnings
- license snapshot or license file path when available

### Step 3: Normalize

Convert each reference into a `feature bag`.

### Step 4: Compare

Compare each normalized bag against current `XUUnity Light Unity MCP`.

### Step 5: Report

Generate:

- missing feature candidates
- stronger reference candidates
- implementation inspiration notes
- confidence and freshness notes
- issue-pattern candidates worth checking in `XUUnity`

### Step 6: Issue Watch

For selected active references, also sample public issue surfaces.

The goal is not to mirror their backlog. The goal is to detect:

- recurring setup pain
- transport failures
- Unity version compatibility breaks
- UI automation limitations
- editor lifecycle bugs
- compile/test runner failure patterns

Each sampled issue pattern should be normalized into:

- affected capability area
- issue theme
- signal strength
- whether `XUUnity` already has the same risk
- whether a local regression check should be added

## ReferenceWatch Risk Controls

ReferenceWatch must not be allowed to turn README marketing into roadmap truth.

Required controls:

- every normalized capability carries provenance
- every capability is marked as `implemented`, `claimed`, `unknown`, or
  `contradicted`
- only `implemented` or manually reviewed `claimed` capabilities may drive a
  backlog proposal
- grouped tools such as `manage_ui` require manual decomposition before they can
  be used as UI primitive evidence
- low-confidence bags may still inform research, but they must not be treated as
  feature parity facts

## Capability Provenance Model

Each capability record should include:

- `status`
- `confidence`
- `evidenceType`
- `sourceFiles`
- `sourceLines`
- `extractionMethod`
- `lastReviewedAtUtc`
- `reviewer`
- `notes`

Suggested status values:

- `implemented`
- `claimed`
- `unknown`
- `contradicted`

Suggested confidence values:

- `high`
- `medium`
- `low`

Suggested evidence types:

- `code_registry`
- `tool_schema`
- `manifest`
- `docs_claim`
- `manual_review`

## Feature Bag Schema

A `feature bag` is the comparison unit.

Suggested schema sections:

```json
{
  "toolId": "unity_mcp_coplay",
  "sourceUrl": "https://github.com/CoplayDev/unity-mcp",
  "capturedAtUtc": "2026-05-12T00:00:00Z",
  "transport": ["http", "stdio"],
  "editorFootprint": {
    "editorOnly": true,
    "runtimeCodeByDefault": false
  },
  "toolGroups": [
    "scene",
    "gameobject",
    "component",
    "build",
    "ui",
    "profiler"
  ],
  "operations": [
    {
      "id": "manage_ui",
      "category": "ui",
      "kind": "mixed",
      "notes": "Grouped UI tool; exact primitive boundaries need manual inspection."
    }
  ],
  "capabilities": {
    "sceneRead": true,
    "sceneWrite": true,
    "componentMutation": true,
    "playmodeControl": true,
    "gameViewCapture": true,
    "uiRead": "partial",
    "uiAction": "unknown",
    "buildProfiles": true,
    "runtimeProfiling": true,
    "multiProjectRouting": true
  },
  "capabilityDetails": {
    "uiRead": {
      "status": "claimed",
      "confidence": "medium",
      "evidenceType": "docs_claim",
      "sourceFiles": ["README.md"],
      "sourceLines": ["120-180"],
      "extractionMethod": "docs_only",
      "lastReviewedAtUtc": "2026-05-12T00:00:00Z",
      "reviewer": "human_or_agent_id",
      "notes": "Grouped UI surface is present, but exact primitive contract still needs code review."
    }
  },
  "evidence": {
    "explicitSchemas": false,
    "readmeClaims": true
  }
}
```

The bag should separate:

- `implemented`
- `claimed`
- `unknown`
- `contradicted`

That distinction matters. Many reference repos advertise capabilities at README
level that are not yet normalized into trustworthy command contracts.

Backlog rule:

- `claimed` alone is not enough to justify a feature-gap decision
- `implemented` may drive comparison conclusions
- `claimed` may drive a manual review task
- `contradicted` should be called out explicitly in reports

## Comparison Output

The comparison report should answer:

1. what `XUUnity` already does better
2. what competitors expose that `XUUnity` does not
3. which missing capabilities matter for our roadmap
4. which repo is the strongest reference for a specific capability

Suggested output:

```json
{
  "focus": "ui_primitives",
  "xuunityCurrentState": "missing_generic_ui_actions",
  "overallLeaders": [
    "unity_mcp_ivanmurzak",
    "unity_mcp_coplay"
  ],
  "capabilityLeaders": [
    {
      "capability": "ui_read",
      "sources": ["unity_mcp_coplay", "unified_unity_mcp"]
    }
  ],
  "candidateFeatures": [
    "unity.ui.query",
    "unity.ui.exists",
    "unity.ui.click",
    "unity.ui.get_text",
    "unity.ui.wait_for"
  ]
}
```

Comparison reports should also emit:

- `dataQuality`
- `staleSources`
- `manualReviewRequired`
- `backlogCandidates`
- `nonActionableClaims`

## Decision Loop

ReferenceWatch needs an explicit consumer workflow or it will become passive
research storage.

Required loop:

1. refresh or fetch sources
2. normalize into feature bags
3. generate a comparison report for a named focus area such as
   `ui_primitives`
4. produce zero or more backlog-ready candidate proposals
5. human review accepts, rejects, or parks each proposal
6. accepted proposals become MCP design or implementation work

For new public MCP feature work, insert a design gate between steps `3` and `4`:

- produce a `reference-first` review summary for the target feature area
- identify `overallLeaders` and `capabilityLeaders`
- record `borrow / reject / differentiate` decisions
- only then open or approve the public contract design artifact

## Portfolio Strategy

Do not treat all references equally.

ReferenceWatch should use three tiers:

### Tier 1: Core Benchmark Set

Keep only `2` references here.

Purpose:

- compare feature breadth
- compare operator experience
- compare tool-contract quality
- compare release and maintenance velocity

These are the repos checked first for:

- feature-gap decisions
- implementation inspiration
- issue-pattern review

### Tier 2: Active Candidate Set

Keep `3` references here.

Purpose:

- watch for fast-moving ideas
- watch for one unusually strong subsystem such as UI, runtime, or builds
- promote to Tier 1 if they become more relevant or more credible

### Tier 3: Parking Lot

All other references stay here.

Purpose:

- preserve discoverability
- allow occasional manual mining
- avoid paying continuous normalization cost

Promotion and demotion between tiers should be explicit and recorded.

## Reference Selection Criteria

Tier assignment should be based on weighted signals, not preference.

Recommended criteria:

- active maintenance
- breadth of relevant Unity MCP capability
- depth in one area we care about, such as UI or runtime
- evidence quality of public tool contracts
- issue volume that is high enough to be informative but not so noisy that it is
  mostly support churn
- relevance to `XUUnity` architecture and desired usage model
- licensing and practical reusability as an implementation reference

## Progress Scoreboard

ReferenceWatch should make progress measurable.

Track at least:

- current `XUUnity` capability coverage for each focus area
- number of gaps against Tier 1 benchmark references
- number of gaps with an accepted backlog item
- number of gaps closed since last comparison
- number of external issue themes checked locally
- number of local regression checks added from external issue themes

This should answer:

- are we catching up
- are we ahead in some areas
- are we learning from other teams' failures

## Ownership And Cadence

ReferenceWatch needs clear operational ownership.

Minimum policy:

- one owner for `reference_sources.yaml`
- one owner for normalization/parser maintenance
- refresh cadence:
  - on demand for an active feature area
  - plus periodic refresh, for example every 30 days, for tracked references
- stale threshold:
  - if a snapshot is older than the agreed cadence, mark comparison output as
    stale

## Backlog Proposal Contract

Comparison should not stop at a JSON summary. It should be able to produce
backlog-ready candidate items.

Suggested fields:

```json
{
  "focus": "ui_primitives",
  "candidateId": "unity_ui_query",
  "title": "Add unity.ui.query read primitive",
  "whyNow": "Needed to make user_like_interaction suites honest.",
  "xuunityCurrentState": "missing",
  "referenceEvidence": [
    {
      "sourceId": "unity_mcp_coplay",
      "capability": "uiRead",
      "status": "implemented",
      "confidence": "medium"
    }
  ],
  "requiredManualReview": true,
  "owner": "xuunity_mcp",
  "nextArtifact": "public_contract_design"
}
```

## Reference-First Design Artifact

Suggested minimal artifact:

```json
{
  "featureArea": "ui_primitives",
  "xuunityCurrentState": "missing_generic_ui_actions",
  "overallLeaders": [
    "unity_mcp_ivanmurzak",
    "unity_mcp_coplay"
  ],
  "capabilityLeaders": [
    {
      "capability": "ui_read",
      "sources": ["unity_mcp_coplay", "unified_unity_mcp"]
    }
  ],
  "issueThemes": [
    "selector ambiguity",
    "playmode lifecycle instability"
  ],
  "borrow": [
    "typed narrow commands instead of one giant grouped surface"
  ],
  "reject": [
    "blind UI automation without strong selector resolution"
  ],
  "differentiate": [
    "stronger evidence contract in scenario results"
  ],
  "recommendedDirection": "ship read-only ui primitives before action primitives"
}
```

## Issue-Derived Regression Contract

When ReferenceWatch finds a recurring external problem, it should be able to
emit a local follow-up item even if no feature gap exists.

Suggested fields:

```json
{
  "sourceId": "unity_mcp_coplay",
  "issueTheme": "Unity version compatibility break",
  "capabilityArea": "build_profiles",
  "externalSignal": "multiple recent fixes or issues",
  "xuunityRisk": "unknown",
  "recommendedCheck": "add targeted compatibility regression in host tests",
  "owner": "xuunity_mcp"
}
```

## What To Copy From References And What Not To Copy

Safe to borrow:

- tool taxonomy ideas
- feature bag categories
- command naming inspiration
- schema structure
- comparison heuristics

Do not copy blindly:

- code just because it exists in a popular repo
- APIs that do not improve `XUUnity`
- low-quality or weakly evidenced implementation ideas
- heavy runtime execution surfaces
- broad code-exec approaches
- giant grouped tools with weak contracts
- client-specific UX assumptions
- README claims without code-backed confirmation

## Immediate Next Steps

1. Stabilize the public module structure under `AIRoot/Modules/AIReferenceWatch/`.
2. Add `ReferenceWatch` operational assets under `AIRoot/Operations/` when the
   reusable scripts and schemas are ready.
3. Add host-local mutable watch folder under `AIOutput/Operations/`.
4. Normalize current `XUUnity` plus the tracked references into feature bags.
5. Generate the first comparison reports for `ui_primitives`,
   `transport`, and `build_profiles`.
6. Start issue-watch for Tier 1 references.
7. Require `reference-first` review before approving new public MCP feature
   contracts.
