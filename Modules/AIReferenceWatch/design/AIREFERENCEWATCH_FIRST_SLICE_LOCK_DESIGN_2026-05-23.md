# AIReferenceWatch First Slice Lock Design

Date: `2026-05-23`
Status: implemented for first operational slice
Scope: `Modules/AIReferenceWatch`

## Goal

Lock the first operational slice of `AIReferenceWatch` so future work does not
blur evidence quality, backlog readiness, or reference-first review semantics.

This design exists so a new chat can continue without reopening the same
questions:

- `implemented` means there is code, schema, manifest, registry, or repo-verified
  evidence.
- `claimed`, `unknown`, and `contradicted` remain separate states.
- claimed-only evidence must not become backlog.
- the current `ui_primitives` review is the first working standard for future
  comparison reports.

## Current Canonical Artifacts

- `Modules/AIReferenceWatch/utilities/examples/feature_bags/*.json`
- `Modules/AIReferenceWatch/utilities/examples/reports/ui_primitives.comparison.json`
- `Modules/AIReferenceWatch/utilities/examples/reviews/ui_primitives.reference_first_review.json`
- `Modules/AIReferenceWatch/utilities/examples/reviews/external_evidence_review_2026-05-23.md`
- `Modules/AIReferenceWatch/utilities/scripts/compare_feature_bags.py`
- `Modules/AIReferenceWatch/utilities/tests/test_reference_watch_utilities.py`

## Evidence Status Rules

### implemented

Use `implemented` only when at least one of these is true:

- tool code was reviewed
- server registry or command registry was reviewed
- tool schema was reviewed
- manifest entry plus implementation handler was reviewed
- local repo-verified evidence exists for the local tool

Valid evidence examples:

- `evidenceType: code_registry`
- `evidenceType: tool_schema`
- `evidenceType: manifest`
- `evidenceType: repo_verified`

Invalid evidence for `implemented`:

- README claim only
- docs marketing copy only
- broad comparison text without source inspection
- grouped tool name without decomposing what it actually does

### claimed

Use `claimed` when public docs say a capability exists but no code/schema/registry
evidence has been reviewed.

Rules:

- never create backlog from `claimed`
- include it in `manualReviewRequired`
- mark capability leader as `provisional`

### unknown

Use `unknown` when the reviewed surface does not confirm the capability.

Rules:

- do not treat `unknown` as negative proof by itself
- do not create backlog from `unknown`
- keep notes specific about what was searched

### contradicted

Use `contradicted` when an earlier broad inference is actively disproven by
source review.

Example:

- Coplay `manage_ui` confirms `get_visual_tree`, but does not confirm direct
  `query`, `exists`, `get_text`, `click`, or `wait_for` primitives.
- Therefore the old broad inference `generic_ui_read_primitives` is
  `contradicted` as a direct primitive claim.

Rules:

- show it in `contradictedClaims`
- do not create backlog
- use it as a design guardrail

## Backlog Rule

Only `implemented` reference capabilities can generate backlog candidates.

`claimed`, `unknown`, `contradicted`, and `not_a_base_goal` must not generate
backlog candidates.

Regression test expectation:

- `claimed + docs_claim` produces manual review, not backlog
- `claimed + manual_review` still produces manual review, not backlog
- `implemented + code_registry` can produce backlog when XUUnity is missing it

## UI Primitives Review As First Standard

The `ui_primitives` review is the first working standard because it now contains:

- external evidence review
- code-confirmed capability promotion
- direct-analog rejection
- contradicted evidence handling
- reference-first design recommendation
- checked examples and utility regression tests

Future reports for `transport` and `build_profiles` should be upgraded to the
same bar before they drive design.

## Implementation Status

Completed:

- `compare_feature_bags.py` treats only `implemented` direct analog evidence as
  actionable.
- `claimed`, `unknown`, `contradicted`, and implemented non-direct evidence do
  not open backlog.
- Regression tests cover claimed-only, manual-review-claimed, implemented
  direct analog, implemented non-direct, and contradicted capabilities.
- `ui_primitives`, `transport`, and `build_profiles` reports are regenerated
  from the hardened comparison rules.

Remaining:

- Run live benchmarks before upgrading reliability/performance claims.
- Keep future crawler/watch outputs host-local.

## Implementation Tasks

1. Keep `compare_feature_bags.py` strict: actionable references are only
   `implemented` and direct analogs.
2. Keep tests for claimed-only, manual-review-claimed, non-direct implemented,
   and contradicted behavior.
3. When normalizing new references, require source notes for every implemented
   capability.
4. Update docs whenever a capability is promoted or demoted.

## Done Criteria

- `validate_examples.py` passes.
- `unittest` passes.
- JSON examples parse with `python3 -m json.tool`.
- `ui_primitives.comparison.json` contains `implemented`, `unknown`, and
  `contradicted` where appropriate.
- No file under `Operations/XUUnityLightUnityMcp/` is modified by this module
  work.
