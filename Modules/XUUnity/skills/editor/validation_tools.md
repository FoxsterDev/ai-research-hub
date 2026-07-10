# Skill: Validation Tools

## Use For
- content validation
- pre-build checks
- release sanity checks

## Rules
- Validate assets, scenes, configs, SDK settings, and critical references before release.
- Prefer actionable validation messages over generic warnings.
- Group high-severity mobile blockers such as missing references, bad import settings, and conflicting SDK config.
- Keep validators easy to run in CI or pre-release workflows.
- After shared asset consolidation, audit scenes, prefabs, ScriptableObjects, and relevant `.meta` files for missing GUIDs and duplicate GUIDs.
- Make shared-asset audits source-aware: project-local duplicates are valid only when they are intentional visual or behavior overrides, not identical copies of the shared asset.
- Validate enum-keyed config maps for completeness: a `List<{enum, asset}>` resolved by `List.Find` returns a default entry with a null asset for any unmapped enum value — silently, with no error — so flag every enum value missing from the map.

## Editing Serialized Scenes/Prefabs By Hand
- Prefer the editor or an editor-scripted / MCP mutation; hand-edit `.unity`/`.prefab` YAML only when no editor path can perform the specific change.
- Removing a GameObject means deleting all of its records — the `GameObject` block and every component block (`Transform`, `MonoBehaviour`, …) — AND every reference to their fileIDs: the owning `m_Component` list, the parent Transform's `m_Children`, and the scene `m_Roots`/`SceneRoots` list. A leftover reference (for example a `Transform` whose `m_Father` points at a parent that no longer lists it) is a silently broken scene, not a warning.
- For an in-place class rename, deliberately reuse the freed script guid in the new `.cs.meta` so existing scene/prefab `m_Script` references resolve without a manual rebind; Unity then reports it as a `.meta` rename.
- Validate after editing: grep the removed fileIDs/guid across the asset (expect zero stray references) and open/import the scene or prefab in the editor (or via MCP) to confirm no missing-script or load error before trusting the change.
