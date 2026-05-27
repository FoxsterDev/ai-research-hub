# Reference Report Workflow Roadmap

Date: `2026-05-23`
Status: first report upgrade completed; crawler/watch remains later
Scope: `Modules/AIReferenceWatch` plus host-local outputs

## Goal

Define the next report and workflow milestones after the first real
`ui_primitives` review.

The work should improve reports in this order:

1. lock the current first slice
2. produce XUUnity UI primitives design input
3. harden feature bag normalization
4. upgrade `transport.comparison.json`
5. upgrade `build_profiles.comparison.json`
6. only then add crawler/watch mode

## Current Baseline

The following report is the quality bar:

- `utilities/examples/reports/ui_primitives.comparison.json`

It has:

- manually reviewed external evidence
- code-confirmed implemented capabilities
- unknowns for missing direct analogs
- contradicted evidence for broad false inference
- a reference-first review ready for design

## Transport Report Upgrade

Target file:

- `utilities/examples/reports/transport.comparison.json`

Inputs:

- `unity_mcp_coplay`
- `unity_mcp_ivanmurzak`
- `mcp_unity_codergamester`
- current local `xuunity_light_unity_mcp` feature bag

Questions to answer:

- Which references have code-confirmed MCP server registration?
- Which references have client setup templates only as docs claims?
- Which references have real multi-client support versus generic MCP
  compatibility?
- Which references expose capability probes or tool-list probes?
- Which references support request final accounting or recovery semantics?
- Which pieces are direct analogs to XUUnity transport goals?

Completed outputs:

- updated transport feature bag evidence
- regenerated `transport.comparison.json`
- `transport.reference_first_review.json`
- explicit borrow/reject/differentiate notes

Design guardrails:

- do not treat generic MCP compatibility as direct proof of XUUnity-style
  same-host routing
- do not treat README client lists as implemented multi-client support unless
  setup templates or registry code are reviewed
- keep final accounting as a first-class XUUnity advantage unless another source
  proves it

## Build Profiles Report Upgrade

Target file:

- `utilities/examples/reports/build_profiles.comparison.json`

Questions to answer:

- Which references implement build tools?
- Which references implement test execution?
- Which references implement build profiles?
- Which references support compile validation without active platform switching?
- Which references support a matrix over target/defines/configs?
- Which references only run normal Unity builds?

Completed outputs:

- updated build feature bag evidence
- regenerated `build_profiles.comparison.json`
- `build_profiles.reference_first_review.json`
- confirmed gaps versus XUUnity's compile matrix posture

Design guardrails:

- implemented `manage_build` is not proof of compile matrix without active
  switch
- implemented `tests-run` is not proof of build profile support
- broad build surface should be decomposed into smaller capabilities

## Host-Local Workflow

All mutable live outputs must stay outside the public module.

Approved host-local output root:

```text
AIOutput/Operations/ReferenceWatch/
  snapshots/
  normalized/
  reports/
  reviews/
  issue_watch/
  source_audit/
```

Public module may contain:

- schemas
- prompts
- scripts
- examples
- reviewed summaries
- design docs

Public module must not contain:

- cloned repositories
- host-private absolute paths as canonical source
- secrets
- live issue dumps with private notes
- large mutable snapshots

## Crawler And Watch Mode

Crawler/watch mode is later work. It should not block the next design contract.

Minimum crawler:

- dependency-free or minimal standard-library implementation where practical
- fetch or inspect GitHub docs/tool registries
- write outputs only to `AIOutput/Operations/ReferenceWatch/`
- normalize into feature bags using existing schema

Issue-watch keywords:

- `ui`
- `build`
- `transport`
- `playmode`
- `lifecycle`

Issue-watch outputs:

- issue id/link
- title
- labels
- matched keywords
- theme
- possible XUUnity regression check
- evidence confidence

## Next Chat Execution Order

1. Open this roadmap.
2. Open `AIREFERENCEWATCH_FIRST_SLICE_LOCK_DESIGN_2026-05-23.md`.
3. Open `FEATURE_BAG_EVIDENCE_NORMALIZATION_DESIGN_2026-05-23.md`.
4. Verify direct analog metadata remains intact when adding new references.
5. Use `ui_visual_tree_read` as the next downstream contract-design input.
6. Run live benchmarks only into `AIOutput/Operations/ReferenceWatch/`.
7. Add crawler/watch mode after the contract design is stable.

## Done Criteria

- `transport` and `build_profiles` reach the same evidence quality as
  `ui_primitives` - done for the first pass
- each has a reference-first review - done for the first pass
- no crawler is introduced before direct analog normalization exists
- host-local outputs stay outside `Modules/AIReferenceWatch`
- `Operations/XUUnityLightUnityMcp/` remains read-only unless the user explicitly
  reopens it for edits
