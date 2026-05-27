# XUUnity UI Primitives Reference Input Design

Date: `2026-05-23`
Status: downstream design drafted
Scope: design input produced by `Modules/AIReferenceWatch`

## Goal

Define the reference-first input for a future XUUnity read-only UI primitives
contract.

This is not an implementation plan inside `Operations/XUUnityLightUnityMcp/`.
That operation is a read-only consumer context while its refactor is happening.
This document only records what `AIReferenceWatch` recommends based on external
evidence.

## External Evidence Summary

Reviewed references:

- `unity_mcp_coplay`
- `unity_mcp_ivanmurzak`
- `mcp_unity_codergamester`

Confirmed Coplay evidence:

- `manage_ui` is present in `manifest.json`.
- `Server/src/services/tools/manage_ui.py` defines a tool schema with actions.
- `MCPForUnity/Editor/Tools/ManageUI.cs` implements the Unity-side command.
- `get_visual_tree` resolves a `UIDocument` and serializes a VisualElement tree.
- `modify_visual_element` can mutate text/classes/style/enabled/visible/tooltip
  on a named VisualElement.

Not confirmed:

- no direct `query` primitive
- no direct `exists` primitive
- no direct `get_text` primitive
- no direct `click` primitive
- no semantic `wait_for` primitive

## Recommended XUUnity Contract Direction

Build a read-only semantic UI contract around a tree snapshot.

Initial command family:

- `ui_tree_snapshot`
- `ui_query`
- `ui_exists`
- `ui_get_text`

Explicitly defer:

- `ui_click`
- `ui_wait_for`
- live mutation

Reason:

- external evidence confirms tree snapshot capability
- external evidence does not confirm direct click/wait/action primitives
- XUUnity should avoid copying a broad grouped `manage_ui` surface
- XUUnity should keep visual evidence separate from semantic UI state

## Proposed Command Semantics

### ui_tree_snapshot

Purpose:

- return a read-only UI tree for a target UI surface

Expected output shape:

- target metadata
- snapshot timestamp
- capability/proof class
- root node
- truncation metadata
- warnings

Suggested node fields:

- stable path when available
- type name
- name
- classes
- text when available
- enabled/interactable when available
- visible/display state when available
- bounds when available
- child count
- children up to requested depth

Important constraints:

- depth limit must be explicit
- truncation must be explicit
- missing capability must return a downgraded proof class, not pretend success
- screenshot evidence is optional visual evidence, not semantic proof

### ui_query

Purpose:

- query the snapshot with XUUnity-owned selector semantics

Selector design should start small:

- by name
- by type
- by text exact
- by text contains
- by class
- by stable tree path when available

Output:

- zero or more matching nodes
- match count
- ambiguity status
- proof class
- warnings when selector is broad or unstable

### ui_exists

Purpose:

- boolean wrapper around `ui_query`

Output:

- `exists: true/false`
- match count
- same ambiguity/proof metadata as query

Rule:

- `exists` must not hide ambiguous results. If 5 nodes match, return
  `exists: true` plus `matchCount: 5` and an ambiguity warning.

### ui_get_text

Purpose:

- return text from one selected UI node

Rules:

- if zero matches, return not found
- if more than one match, return ambiguous unless caller explicitly allows many
- do not infer text from screenshots
- if text is missing because the UI backend cannot expose it, return an evidence
  downgrade

## Deferred Commands

### ui_click

Reason to defer:

- no reviewed reference proves a direct click analog
- selector stability is not designed yet
- playmode/editor lifecycle semantics are not designed yet
- click requires stronger safety and idempotency rules than read-only commands

### ui_wait_for

Reason to defer:

- no reviewed reference proves semantic UI wait behavior
- wait semantics need timeout, polling, lifecycle, domain reload, and proof-class
  decisions
- it should be designed after `ui_query` is stable

### live mutation

Reason to defer:

- Coplay has `modify_visual_element`, but XUUnity's first UI primitive slice
  should stay read-only
- mutation belongs behind a separate safety review

## Borrow, Reject, Differentiate

Borrow:

- Coplay's idea of reading a `UIDocument` visual tree
- explicit depth/truncation
- text extraction from tree nodes when the backend exposes it

Reject:

- a giant grouped `manage_ui` command
- treating visual screenshot as semantic state
- treating Coplay as proof for click/wait primitives
- live UI mutation in the first slice

Differentiate:

- narrow typed commands
- capability gating
- explicit proof classes
- source-backed evidence notes
- stable failure semantics

## Next Artifact

The downstream public contract design has been drafted in this module while
`Operations/XUUnityLightUnityMcp/` remains read-only.

Downstream handoff:

- `XUUNITY_READ_ONLY_UI_PRIMITIVES_DOWNSTREAM_DESIGN_2026-05-23.md`

Source design input:

- this document
- `utilities/examples/reports/ui_primitives.comparison.json`
- `utilities/examples/reviews/ui_primitives.reference_first_review.json`
- `utilities/examples/reviews/external_evidence_review_2026-05-23.md`
