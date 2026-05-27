# External Evidence Review - 2026-05-23

Scope: `unity_mcp_coplay`, `unity_mcp_ivanmurzak`, and `mcp_unity_codergamester`.

Constraint: `Operations/XUUnityLightUnityMcp/` was read-only context only.

## Method

- Cloned public references into `/private/tmp/AIReferenceWatch-source-audit-20260523/`.
- Reviewed real tool manifests, server registries, tool schemas, and Unity-side handlers.
- Promoted `claimed` to `implemented` only when code registry, tool schema, or Unity handler evidence was present.
- Left direct UI primitives as `unknown` or `contradicted` when only broad/grouped claims existed.
- Added `directAnalog` classification so implemented but non-direct reference
  capabilities stay as design input instead of backlog.

## CoplayDev/unity-mcp

Confirmed implemented:

- `manage_ui` is listed in `manifest.json`.
- `Server/src/services/tools/manage_ui.py` declares the `manage_ui` tool and its action schema.
- `MCPForUnity/Editor/Tools/ManageUI.cs` implements the action switch.
- `get_visual_tree` resolves a target `UIDocument` and serializes `type`, `name`, `classes`, `resolvedStyle`, `text`, and `children`.
- `modify_visual_element` uses `root.Q(elementName)` and can change text, classes, style, enabled state, visibility, and tooltip.

Not confirmed:

- No standalone UI `query`, `exists`, `get_text`, `click`, or semantic `wait_for` primitive was found in the reviewed `manage_ui` surface.
- `get_visual_tree` can support future XUUnity query/get_text design, but it is not itself the same contract.

Decision input:

- Borrow the visual-tree snapshot idea.
- Do not copy the grouped `manage_ui` contract.
- Do not use Coplay as proof for click/wait_for/action primitives.

## IvanMurzak/Unity-MCP

Confirmed implemented:

- `docs/default-mcp-tools.md` lists built-in tool ids such as `gameobject-find`, `gameobject-component-modify`, `tests-run`, `screenshot-game-view`, and `reflection-method-call`.
- `Unity-MCP-Plugin/.../API/Tool/*.cs` contains many `[AiTool]` annotated tool implementations.
- `Tool.List.cs` exposes a registry list path for registered Unity-MCP tools.
- `Tests.Run.cs`, `Profiler.CaptureFrame.cs`, and `Screenshot.GameView.cs` confirm develop/test, profiler, and visual evidence surfaces.

Not confirmed:

- No dedicated semantic UI Toolkit `query`, `exists`, `get_text`, `click`, or `wait_for` primitive was found in the reviewed default tool set.

## CoderGamester/mcp-unity

Confirmed implemented:

- `Server~/src/index.ts` creates the MCP server and registers scene, GameObject, component, material, tests, console, and batch tools.
- `Server~/src/tools/updateComponentTool.ts` defines the `update_component` zod schema and bridge handler.
- `Editor/Tools/UpdateComponentTool.cs` implements add/update component behavior in Unity.
- `Server~/src/tools/getSceneInfoTool.ts` and `Editor/Tools/GetSceneInfoTool.cs` confirm scene-info read support.

Not confirmed:

- No dedicated UI primitive registry was found in the reviewed server registry or Unity tool handlers.

## XUUnity UI Primitive Direction

Use external evidence only for this first design direction:

- Start from a read-only UI tree snapshot.
- Build XUUnity-specific `query`, `exists`, and `get_text` semantics on top of that snapshot.
- Keep screenshot evidence separate from semantic UI state.
- Defer `click` and `wait_for` until selector stability and playmode lifecycle rules are designed and tested locally.

## Transport Direction

Current result:

- XUUnity remains ahead on same-host routing, capability probe gating, final
  accounting, low footprint, and easy disable/uninstall.
- CoderGamester confirms an implemented IDE-to-Unity bridge, but it is marked
  `directAnalog: false` for XUUnity transport because it does not prove the same
  same-host/final-accounting contract.
- IvanMurzak confirms custom tool extensibility, but it is marked
  `directAnalog: false` because it is not a current XUUnity base transport goal.

Decision input:

- Do not open transport backlog from current external evidence.
- Use external bridge registries as setup/documentation taxonomy only.

## Build Profiles Direction

Current result:

- XUUnity remains ahead on compile validation, active-target-free compile matrix,
  and build-config compile matrix.
- Coplay confirms `manage_build`, but it is marked `directAnalog: false` for
  XUUnity compile-matrix semantics.
- Coplay and CoderGamester confirm test-run surfaces; these are direct analogs
  for generic test execution, but they do not create a gap because XUUnity has
  an EditMode validation lane.

Decision input:

- Do not add a broad build runner from this evidence.
- Keep broad build/profile tooling as taxonomy input for future polish.
