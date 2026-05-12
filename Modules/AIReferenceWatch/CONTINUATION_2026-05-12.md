# AIReferenceWatch Continuation

Date: `2026-05-12`
Status: handoff snapshot for next chat

## Goal

Build `AIReferenceWatch` as a reusable public infrastructure module for:

- tracking external AI and MCP references
- understanding feature gaps against other solutions
- identifying the best reference per capability
- monitoring external issue patterns
- feeding better design decisions into `XUUnity` and other public `AIRoot`
  modules

Current highest-priority use case:

- Unity MCP comparison and design support for `XUUnity Light Unity MCP`

## What Was Done

### Module Structure

Created the public module:

- `AIRoot/Modules/AIReferenceWatch/`

Current structure:

- `README.md`
- `design/README.md`
- `design/XUUNITY_MCP_REFERENCE_WATCH_DESIGN_2026-05-12.md`
- `knowledge/README.md`
- `knowledge/reference_selection_doctrine.md`
- `utilities/README.md`

### Design Split And Ownership

The old combined design was split.

Current ownership:

- `AIReferenceWatch` owns:
  - reference-watch strategy
  - feature-gap comparison design
  - issue-watch design
  - reference-first design gate
  - durable reference-selection doctrine
- `XUUnity Light Unity MCP` owns:
  - `AIRoot/Operations/XUUnityLightUnityMcp/Designs/XUUNITY_MCP_UI_PRIMITIVES_DESIGN_2026-05-12.md`

MCP-specific compatibility and split notes now live with the MCP operation under
`AIRoot/Operations/XUUnityLightUnityMcp/Designs/`.

### Durable Knowledge Added

Added:

- `AIRoot/Modules/AIReferenceWatch/knowledge/reference_selection_doctrine.md`

It defines:

- `overall leader` vs `capability leader`
- tiering rules
- benchmark selection rules
- capability leader selection rules
- adoption quality bar
- issue-watch to regression-check mapping
- selection workflow
- stability rule

### Host-Local Mutable Layer Added

Initial source registry moved into the public module:

- `AIRoot/Modules/AIReferenceWatch/reference_sources.yaml`

Host-local snapshots, normalized feature bags, and comparison reports should be
created by consuming repos only when they run the workflow.

### Current Reference Set

Configured references:

- Tier 1
  - `IvanMurzak/Unity-MCP`
  - `CoplayDev/unity-mcp`
- Tier 2
  - `codergamester/mcp-unity`
  - `AndreySkyFoxSidorov/UnifiedUnityMCP`
  - `AlexMerzlikin/unity-agent-team`
- Tier 3
  - `r1n7aro/Locus`
  - `TheArcForge/UniClaude`
  - `Donchitos/Claude-Code-Game-Studios`

### Rules Explicitly Locked In

The design now explicitly says:

- do not copy reference code or APIs blindly
- use references only when there is real value for `XUUnity` or another target
  module
- use references to sharpen local design, not to mirror another repo
- new public MCP feature design should normally be `reference-first`

## Important Canonical Paths

Public module:

- `AIRoot/Modules/AIReferenceWatch/README.md`
- `AIRoot/Modules/AIReferenceWatch/design/XUUNITY_MCP_REFERENCE_WATCH_DESIGN_2026-05-12.md`
- `AIRoot/Modules/AIReferenceWatch/knowledge/reference_selection_doctrine.md`

Public source registry:

- `AIRoot/Modules/AIReferenceWatch/reference_sources.yaml`

Downstream MCP consumer design:

- `AIRoot/Operations/XUUnityLightUnityMcp/Designs/XUUNITY_MCP_UI_PRIMITIVES_DESIGN_2026-05-12.md`

## Current Gaps

The module has design and doctrine, but not yet the first reusable operational
assets.

Still missing:

- schema for `reference_sources.yaml`
- reusable normalization schema artifacts in the module
- first compare/normalize scripts
- first host-local normalized feature bags
- first comparison reports
- first issue-watch outputs
- first `reference-first` review artifact generated from real reference data

## Recommended Next Steps

1. Add a public schema for `reference_sources.yaml` under
   `AIRoot/Modules/AIReferenceWatch/`.
2. Add the first reusable artifacts under `utilities/`:
   - feature bag schema
   - normalization prompt or script
   - comparison output shape
3. Create host-local output folders in the consuming repo when the workflow is
   run:
   - snapshots
   - normalized feature bags
   - comparison reports
4. Produce the first normalized feature bags for:
   - `unity_mcp_coplay`
   - `unity_mcp_ivanmurzak`
   - one Tier 2 specialist candidate
5. Generate the first focused reports for:
   - `ui_primitives`
   - `transport`
   - `build_profiles`
6. Start issue-watch for Tier 1 references.
7. Use the first report to create the first real `reference-first` review for a
   public `XUUnity` MCP feature.

## Suggested Next Chat Prompt

Use `AIRoot/Modules/AIReferenceWatch/CONTINUATION_2026-05-12.md` as the start
point and continue by implementing the first operational assets for the module:

- source schema
- normalization artifacts
- first feature bags
- first compare report
