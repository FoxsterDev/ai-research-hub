# Feature Bag Evidence Normalization Design

Date: `2026-05-23`
Status: implemented for first pass
Scope: `Modules/AIReferenceWatch/utilities`

## Goal

Harden feature bag normalization so broad reference claims do not accidentally
look like confirmed direct capabilities.

This design covers three work items:

- add an evidence checklist to examples and prompts
- add a `direct_analog: true/false` pattern
- add a small fixture/test for contradicted capabilities

## Problem

The first seed bags started with public comparison evidence. That was useful for
bootstrapping, but broad grouped tools can mislead the comparison system.

Example:

- Coplay has `manage_ui`.
- `manage_ui` really implements `get_visual_tree`.
- `manage_ui` does not prove direct `query`, `exists`, `get_text`, `click`, or
  `wait_for` primitives.

Without a direct-analog signal, future reviewers may promote broad grouped
surfaces too aggressively.

## Evidence Checklist

Add a reusable checklist to prompts and examples.

For every capability marked `implemented`, require:

- source repo id
- reviewed source file or URL
- evidence type
- tool or operation id
- registry/schema/manifest/handler evidence
- direct analog assessment
- notes explaining what was not confirmed

Checklist fields can be represented in notes first, then promoted to schema
fields once examples settle.

Recommended prompt checklist:

```text
Evidence checklist:
- What exact capability is being evaluated?
- Is this a direct analog to the target capability?
- Which file proves registration or schema?
- Which file proves implementation?
- Is the capability only documented but not code-confirmed?
- Is a broad grouped tool being decomposed into narrower capabilities?
- What related capabilities were searched but not found?
- Should the status be implemented, claimed, unknown, or contradicted?
```

## direct_analog Pattern

Add direct analog metadata to capability details.

Recommended shape:

```json
{
  "directAnalog": true,
  "analogTarget": "ui_visual_tree_read",
  "analogNotes": "Coplay get_visual_tree directly maps to read-only tree snapshot input, but not to query/click/wait_for."
}
```

Rules:

- `directAnalog: true` means the reviewed reference capability directly maps to
  the target capability.
- `directAnalog: false` means the reference is related, but not a direct contract
  match.
- missing `directAnalog` should be treated as unknown during the transition.

Examples:

- Coplay `ui_visual_tree_read`: `directAnalog: true`
- Coplay `ui_tool_surface`: `directAnalog: false`
- Coplay `generic_ui_read_primitives`: `directAnalog: false` and
  `status: contradicted`

## Implementation Status

Completed:

- `feature_bag.schema.json` accepts optional `directAnalog`, `analogTarget`, and
  `analogNotes`.
- `comparison_report.schema.json` allows the same fields in reference status
  entries.
- prompts include an evidence checklist and direct analog checklist.
- seed feature bags include direct analog metadata for reviewed external
  capabilities.
- tests cover implemented non-direct and contradicted behavior.

Remaining:

- Future schema pass can make direct analog metadata required for implemented
  reference capabilities after more examples settle.

## Schema Update Plan

Updated `feature_bag.schema.json` capability details:

- add optional `directAnalog`
- add optional `analogTarget`
- add optional `analogNotes`

Kept optional first so existing examples stay easy to migrate.

After examples are updated, add tests that enforce:

- implemented capabilities with focus `ui_primitives` should include
  `directAnalog`
- broad grouped surfaces should not be direct analogs unless manually justified

## Prompt Update Plan

Update:

- `utilities/prompts/extract_reference_feature_bag.md`
- `utilities/prompts/compare_feature_bags.md`

Prompt requirements:

- ask the reviewer to decompose grouped tools
- ask whether the capability is a direct analog
- require contradicted status when source review disproves an earlier broad
  inference
- forbid backlog recommendations from claimed-only evidence

## Fixture And Test Plan

Add a small fixture or inline unit-test feature bag with:

- local XUUnity missing a capability
- reference capability marked `contradicted`
- another reference capability marked `claimed`

Expected comparison output:

- no backlog candidate
- contradicted claim appears in `contradictedClaims`
- claimed-only evidence appears in manual review or non-actionable claim
- capability leader is not confirmed from contradicted evidence

Suggested test name:

- `test_contradicted_reference_does_not_create_backlog`

## Done Criteria

- schema accepts direct analog metadata
- prompts include evidence checklist
- tests cover claimed, manual-review-claimed, implemented, and contradicted paths
- checked-in examples validate
- `ui_primitives.comparison.json` still shows Coplay direct UI primitives
  correctly: visual tree implemented, generic primitives contradicted, click and
  wait unknown
