# AIReferenceWatch Module

## Purpose

`AIReferenceWatch` is a public-safe module for tracking external AI tooling
references, comparing capability surfaces, and feeding better design decisions
back into public `AIRoot` modules.

The initial delivery focus is Unity MCP comparison and feature-gap analysis.
The longer-term scope is wider:

- enrich `XUUnity`
- support other `AIRoot` modules
- track reference patterns, issues, and implementation ideas across public AI
  tool ecosystems

Canonical module path:
- `AIRoot/Modules/AIReferenceWatch/`

## Current Scope

Right now this module is responsible for:

- reference-watch strategy
- feature-bag normalization and comparison design
- issue-watch strategy
- reference-first design gating for new public features
- MCP UI primitive reference-informed design support

## Structure

- `reference_sources.yaml`
  - public source registry for external references tracked by the module
- `design/`
  - active design plans for the module
- `knowledge/`
  - durable comparison doctrine and selection rules
- `utilities/`
  - future reusable utilities, prompts, and workflows for reference ingestion

## Current Knowledge Docs

- `knowledge/reference_selection_doctrine.md`

## Continuation

- `CONTINUATION_2026-05-12.md`

## Active Design Docs

- `design/XUUNITY_MCP_REFERENCE_WATCH_DESIGN_2026-05-12.md`

Downstream consumer design currently using this module:

- `AIRoot/Operations/XUUnityLightUnityMcp/XUUNITY_MCP_UI_PRIMITIVES_DESIGN_2026-05-12.md`

## Module Direction

This module should stay generic.

It may start from Unity MCP work because that is the current highest-value use
case, but the design should not hard-code itself into one protocol family if the
same comparison system can later improve other public modules.
