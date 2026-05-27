# XUUnity Read-Only UI Primitives Downstream Design

Date: `2026-05-23`
Status: transferred to XUUnity operation design folder
Scope: downstream design prepared by `Modules/AIReferenceWatch`
Target consumer: `Operations/XUUnityLightUnityMcp`

Canonical operation-owned copy:

- `Operations/XUUnityLightUnityMcp/docs/architecture/designs/XUUNITY_MCP_READ_ONLY_UI_PRIMITIVES_DESIGN_2026-05-23.md`

## Read-Only Constraint

`Operations/XUUnityLightUnityMcp/` is currently read-only because a parallel
refactor is in progress. This document is intentionally stored in
`Modules/AIReferenceWatch/design/` as a downstream handoff. When XUUnity is open
for edits, this can be copied or adapted into the XUUnity operation design set.

## Goal

Add a first public read-only UI primitives surface for XUUnity that lets an MCP
client inspect Unity UI state semantically without clicking, waiting, or
mutating UI.

The first slice should answer four questions:

1. What UI nodes exist right now?
2. Which nodes match a selector?
3. Does a matching node exist?
4. What text does a matching node expose?

## Reference Evidence

This design is reference-first and based on `AIReferenceWatch` evidence.

Primary confirmed external evidence:

- Coplay `manage_ui` is implemented.
- Coplay `get_visual_tree` is implemented and serializes a Unity UI Toolkit
  VisualElement tree.
- Coplay `modify_visual_element` is implemented but is a mutation surface.

Explicit non-evidence:

- no reviewed reference confirmed a direct `query` primitive
- no reviewed reference confirmed a direct `exists` primitive
- no reviewed reference confirmed a direct `get_text` primitive
- no reviewed reference confirmed `click`
- no reviewed reference confirmed semantic `wait_for`

Canonical source artifacts:

- `Modules/AIReferenceWatch/utilities/examples/reports/ui_primitives.comparison.json`
- `Modules/AIReferenceWatch/utilities/examples/reviews/ui_primitives.reference_first_review.json`
- `Modules/AIReferenceWatch/utilities/examples/reviews/external_evidence_review_2026-05-23.md`
- `Modules/AIReferenceWatch/design/XUUNITY_UI_PRIMITIVES_REFERENCE_INPUT_DESIGN_2026-05-23.md`

## Non-Goals

This first slice does not include:

- clicking, tapping, submitting, dragging, or focusing UI
- semantic `wait_for`
- live mutation
- UI creation or UI asset editing
- broad `manage_ui` style grouped operations
- OCR-backed text assertions
- computer-vision-only UI querying
- runtime player instrumentation by default
- support for every Unity UI backend in the first pass

## Design Principles

- Read-only first.
- Narrow typed operations instead of one grouped command.
- Capability-gated behavior before reflection-heavy code paths.
- Explicit proof class in every response.
- Visual evidence and semantic UI evidence are separate.
- Ambiguity is reported, not hidden.
- Truncation is explicit.
- Missing backend support is a downgraded evidence result, not a fake failure.
- Direct analog evidence can open design work; broad related evidence cannot.

## Operation Family

Recommended public operation ids:

- `unity_ui_tree_snapshot`
- `unity_ui_query`
- `unity_ui_exists`
- `unity_ui_get_text`

Recommended capability ids:

- `ui_tree_snapshot`
- `ui_query`
- `ui_exists`
- `ui_get_text`

Optional short public names can be considered later. The explicit
`unity_ui_*` names fit the existing XUUnity operation naming style better than
generic `ui_*`.

## Supported Backends

Initial backend priority:

1. UI Toolkit `UIDocument`
2. uGUI `Canvas` and common `UnityEngine.UI` components
3. TextMeshPro text extraction when available and editor assemblies can resolve it

The first implementation may ship UI Toolkit only if uGUI/TMP support would
delay a stable contract. The response must report backend support explicitly.

Backend ids:

- `ui_toolkit`
- `ugui`
- `textmeshpro`
- `unknown`

## Target Model

Every command accepts a target descriptor.

Suggested request shape:

```json
{
  "target": {
    "kind": "active_scene",
    "backend": "ui_toolkit"
  }
}
```

Supported target kinds:

- `active_scene`: inspect all supported UI roots in the active scene
- `game_object_path`: inspect a specific GameObject path
- `game_object_name`: inspect a specific GameObject name
- `instance_id`: inspect a specific Unity instance id

Recommended constraints:

- `active_scene` can return multiple roots.
- GameObject name can be ambiguous.
- GameObject path is preferred when available.
- Instance id is precise but not stable across sessions.

Target resolution output must include:

- target kind
- requested value
- resolved object count
- ambiguity warnings
- backend selected
- backend support status

## Proof Classes

Every response includes `proofClass`.

Recommended enum:

- `semantic_ui_tree`: data came from Unity UI objects and serialized UI tree
- `semantic_ui_partial`: data came from UI objects but backend support,
  reflection, or truncation made it incomplete
- `visual_only`: screenshot or visual evidence exists, but semantic data does
  not
- `unavailable`: capability or backend is unavailable
- `error`: operation failed before evidence could be produced

Rules:

- `ui_get_text` must not return OCR as `semantic_ui_tree`.
- `ui_exists` from screenshot alone is not allowed in this slice.
- Reflection failures should downgrade to `semantic_ui_partial` or
  `unavailable` with warnings.

## Common Response Envelope

All commands should use a stable envelope.

```json
{
  "schemaVersion": "xuunity.ui.read.v1",
  "operation": "unity_ui_tree_snapshot",
  "success": true,
  "proofClass": "semantic_ui_tree",
  "generatedAtUtc": "2026-05-23T00:00:00Z",
  "target": {},
  "capabilities": {},
  "warnings": [],
  "errors": []
}
```

Common fields:

- `schemaVersion`
- `operation`
- `success`
- `proofClass`
- `generatedAtUtc`
- `target`
- `capabilities`
- `warnings`
- `errors`

Error objects:

```json
{
  "code": "ui_backend_unavailable",
  "message": "UI Toolkit UIDocument support is unavailable in this editor state.",
  "details": {}
}
```

Warning objects:

```json
{
  "code": "selector_ambiguous",
  "message": "Selector matched more than one node.",
  "details": {
    "matchCount": 3
  }
}
```

## UI Node Model

All commands that return nodes should use this normalized shape.

```json
{
  "nodeId": "ui-toolkit:MainMenu/StartButton",
  "backend": "ui_toolkit",
  "path": "MainMenu/StartButton",
  "type": "Button",
  "name": "StartButton",
  "classes": ["primary"],
  "text": "Start",
  "enabled": true,
  "visible": true,
  "interactable": true,
  "bounds": {
    "x": 120,
    "y": 80,
    "width": 240,
    "height": 48
  },
  "childCount": 0,
  "children": []
}
```

Required minimum fields:

- `nodeId`
- `backend`
- `type`
- `name`
- `path`
- `childCount`

Optional fields:

- `classes`
- `text`
- `enabled`
- `visible`
- `interactable`
- `bounds`
- `children`
- `truncated`
- `source`

Node id rules:

- stable within one snapshot
- not guaranteed stable across sessions unless backend provides a stable path
- must not be used as a durable save-file reference

## Operation: unity_ui_tree_snapshot

Purpose:

- return a read-only snapshot of supported UI nodes

Request:

```json
{
  "target": {
    "kind": "active_scene",
    "backend": "ui_toolkit"
  },
  "maxDepth": 8,
  "maxNodes": 500,
  "includeBounds": true,
  "includeText": true,
  "includeInactive": false
}
```

Response additions:

```json
{
  "roots": [],
  "nodeCount": 42,
  "truncated": false,
  "limits": {
    "maxDepth": 8,
    "maxNodes": 500
  }
}
```

Rules:

- default `maxDepth` should be conservative, for example 8.
- default `maxNodes` should be conservative, for example 500.
- if depth or node limits are hit, set `truncated: true`.
- partial data must include warnings.
- active scene snapshot can include multiple roots.

## Selector Model

Selectors are XUUnity-owned and intentionally small.

Selector shape:

```json
{
  "name": "StartButton",
  "type": "Button",
  "text": {
    "equals": "Start"
  },
  "class": "primary",
  "path": "MainMenu/StartButton",
  "visible": true,
  "enabled": true
}
```

Supported selector fields:

- `name`
- `type`
- `path`
- `class`
- `text.equals`
- `text.contains`
- `visible`
- `enabled`

Matching rules:

- selector fields combine with AND semantics
- text matching is case-sensitive by default
- optional future `caseInsensitive` can be added later
- class matches a single class at first
- regex is out of scope for the first slice

Ambiguity rules:

- zero matches: not found
- one match: unique
- more than one match: ambiguous
- ambiguous is still a successful query but not a successful single-node
  `get_text`

## Operation: unity_ui_query

Purpose:

- return nodes matching a selector

Request:

```json
{
  "target": {
    "kind": "active_scene",
    "backend": "ui_toolkit"
  },
  "selector": {
    "name": "StartButton",
    "type": "Button"
  },
  "maxDepth": 8,
  "maxNodes": 500,
  "maxMatches": 20
}
```

Response additions:

```json
{
  "selector": {},
  "matches": [],
  "matchCount": 1,
  "ambiguous": false,
  "truncated": false
}
```

Rules:

- query internally uses a tree snapshot.
- response should include enough node data for follow-up.
- if `maxMatches` is exceeded, set `truncated: true`.
- broad selectors should return warnings.

## Operation: unity_ui_exists

Purpose:

- boolean existence check over `unity_ui_query`

Request:

```json
{
  "target": {
    "kind": "active_scene",
    "backend": "ui_toolkit"
  },
  "selector": {
    "text": {
      "equals": "Play"
    }
  }
}
```

Response additions:

```json
{
  "exists": true,
  "matchCount": 2,
  "ambiguous": true
}
```

Rules:

- `exists` is true when match count is greater than zero.
- ambiguity is reported even when `exists` is true.
- `exists` does not return screenshots or OCR-derived results.

## Operation: unity_ui_get_text

Purpose:

- return semantic text from a single selected node

Request:

```json
{
  "target": {
    "kind": "active_scene",
    "backend": "ui_toolkit"
  },
  "selector": {
    "name": "TitleLabel"
  },
  "allowMany": false
}
```

Response additions:

```json
{
  "text": "Main Menu",
  "matches": [],
  "matchCount": 1,
  "ambiguous": false
}
```

Rules:

- zero matches returns `success: false` with `ui_node_not_found`.
- more than one match returns `success: false` with `selector_ambiguous` unless
  `allowMany: true`.
- if `allowMany: true`, return `texts` as an array of node/text pairs.
- empty string is valid text and must be distinguished from missing text.
- missing text field returns `ui_text_unavailable`.

## Capability Gating

XUUnity should expose capability state before these operations run.

Suggested capability entries:

```json
{
  "ui_tree_snapshot": {
    "supported": true,
    "proofClass": "semantic_ui_tree",
    "backends": ["ui_toolkit"],
    "notes": []
  },
  "ui_query": {
    "supported": true,
    "dependsOn": ["ui_tree_snapshot"]
  },
  "ui_exists": {
    "supported": true,
    "dependsOn": ["ui_query"]
  },
  "ui_get_text": {
    "supported": true,
    "dependsOn": ["ui_query"]
  }
}
```

Rules:

- operations should fail fast when capability probe says unsupported.
- backend-level failures should appear in operation responses and health data.
- capability names should be included in `unity_capabilities`.

## Implementation Architecture

Recommended internal layers:

1. operation handlers
2. target resolver
3. backend snapshot providers
4. normalized node mapper
5. selector matcher
6. response builder

Suggested types:

- `XUUnityLightMcpUiTarget`
- `XUUnityLightMcpUiSnapshotOptions`
- `XUUnityLightMcpUiSnapshot`
- `XUUnityLightMcpUiNode`
- `XUUnityLightMcpUiSelector`
- `XUUnityLightMcpUiQueryResult`
- `XUUnityLightMcpUiProofClass`

Provider interface:

```csharp
internal interface IXUUnityLightMcpUiSnapshotProvider
{
    string BackendId { get; }
    bool IsAvailable(out string reason);
    XUUnityLightMcpUiSnapshot Capture(
        XUUnityLightMcpUiTarget target,
        XUUnityLightMcpUiSnapshotOptions options);
}
```

## UI Toolkit Provider Notes

UI Toolkit snapshot source:

- find `UIDocument` components
- read `rootVisualElement`
- serialize VisualElement tree

Suggested fields:

- `GetType().Name` -> `type`
- `VisualElement.name` -> `name`
- `GetClasses()` -> `classes`
- `TextElement.text` -> `text`
- `resolvedStyle` -> bounds/style-derived visibility
- `enabledSelf` / enabled in hierarchy where available -> `enabled`
- display/visibility style where available -> `visible`

Guardrails:

- never mutate VisualElement state.
- handle null root as partial/unavailable.
- do not require play mode unless backend needs it.
- avoid excessive reflection where public API exists.

## uGUI Provider Notes

Potential uGUI snapshot source:

- find `Canvas` roots
- traverse child `GameObject`s
- map common components:
  - `UnityEngine.UI.Text`
  - `UnityEngine.UI.Button`
  - `UnityEngine.UI.Image`
  - `UnityEngine.UI.Toggle`
  - `UnityEngine.UI.InputField`
  - `RectTransform`

Suggested text extraction:

- `Text.text`
- `InputField.text`
- TMP text only if TMP assemblies/types resolve safely

Guardrails:

- if TMP cannot resolve, do not fail the whole snapshot.
- report partial text support.

## Error Codes

Recommended codes:

- `ui_capability_unavailable`
- `ui_backend_unavailable`
- `ui_target_not_found`
- `ui_target_ambiguous`
- `ui_snapshot_empty`
- `ui_snapshot_truncated`
- `ui_selector_invalid`
- `ui_node_not_found`
- `ui_text_unavailable`
- `selector_ambiguous`
- `ui_internal_error`

## Safety And Privacy

Read-only UI snapshots may expose user-visible strings from the Unity project.

Rules:

- do not write snapshots to disk unless caller asks for output.
- do not include screenshots by default.
- do not include asset contents beyond UI node metadata.
- do not include editor window titles or OS-level UI.
- keep response size bounded.

## Testing Plan

Unit tests:

- selector matching by name/type/class/text/path
- AND semantics
- zero/one/many matches
- ambiguity behavior
- `exists` with multiple matches
- `get_text` zero/many/missing text
- truncation metadata
- proof-class downgrades

EditMode tests:

- UI Toolkit fixture with UIDocument and nested labels/buttons
- inactive/hidden node behavior
- max depth truncation
- max node truncation
- target not found
- ambiguous target name

Optional PlayMode tests:

- UI Toolkit root after play mode starts
- uGUI Canvas with Text/Button
- TMP text if available in fixture project

Smoke tests:

- `unity_capabilities` reports UI capabilities
- `unity_ui_tree_snapshot` returns at least one fixture node
- `unity_ui_query` finds a known button
- `unity_ui_exists` returns true for known label
- `unity_ui_get_text` returns known label text

## Rollout Plan

Phase 1:

- UI Toolkit provider only
- operations:
  - `unity_ui_tree_snapshot`
  - `unity_ui_query`
  - `unity_ui_exists`
  - `unity_ui_get_text`
- capability gating
- EditMode fixture tests

Phase 2:

- uGUI provider
- optional TMP text extraction
- broaden selector fields only if needed

Phase 3:

- consider semantic `ui_wait_for`
- consider action primitives such as click only after a separate reference and
  safety review

## Backward Compatibility

This is an additive operation family.

Existing screenshot and Game View operations remain visual evidence. They should
not be reclassified as semantic UI state.

## Acceptance Criteria

The first implementation is acceptable when:

- UI capabilities appear in capability probe output.
- read-only UI Toolkit snapshot returns normalized nodes.
- query/exists/get_text work over the same normalized node model.
- ambiguous selectors are visible to the caller.
- response size limits and truncation are enforced.
- screenshot evidence is not used as semantic proof.
- no click, wait, or mutation operation is exposed.
- tests cover selector behavior and proof-class downgrades.

## Open Questions

- Should the first provider support only active scene, or also prefab stage?
- Should selector text matching default to case-sensitive or case-insensitive?
- Should uGUI ship in phase 1 if it is straightforward?
- Should response include local transform bounds, screen-space bounds, or both?
- Should node `path` use GameObject hierarchy, VisualElement hierarchy, or a
  backend-prefixed hybrid?

## Next Step

When XUUnity is writable again, create the consumer-owned implementation design
under `Operations/XUUnityLightUnityMcp/` using this document as the source.
