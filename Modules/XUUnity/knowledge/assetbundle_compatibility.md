# XUUnity Knowledge: AssetBundle Compatibility

Use this file when a task touches AssetBundles, Addressables-backed remote content, bundled prefabs, bundled ScriptableObjects, bundle manifests, Type Trees, or content intended to work across multiple shipped client versions.

## Rule

- Treat an AssetBundle as serialized data loaded by an already-shipped Player, not as a code patch.
- A shared production bundle must be compatible with the oldest supported client, Unity runtime, platform target, scripting defines, packages, and serialized type identities.
- If bundle content requires new runtime behavior, publish it through a client-version lane instead of claiming one bundle works for all clients.
- Every MonoBehaviour or ScriptableObject type serialized into a bundle must already exist in every target client.
- Keep bundled script type identity stable:
  - assembly or asmdef ownership
  - namespace
  - class name
- Keep Type Trees enabled for compatibility-sensitive shared bundles. Do not use `DisableWriteTypeTree` unless every target player has an exact matching serialized layout.
- Treat serialized field names, field types, and enum integer values as compatibility contracts.
- Add fields only when they are optional and default-safe.
- Do not hide serialized fields used by bundled content behind platform or scripting-define conditions unless every target client and bundle lane is built with the same schema expectation.
- Do not reorder, reuse, or repurpose enum integer values that may already exist in published content.
- Unknown enum values, missing optional fields, missing prefab slots, and missing optional references must be ignored or degraded safely.
- `FormerlySerializedAs` is an editor migration aid; do not rely on it as the only proof that remote bundles remain safe for old clients.
- Load bundle dependencies before dependent bundles or assets, and keep dependencies alive while dependent objects are alive.
- For SpriteAtlas-backed remote content, compatibility requires both atlas data and an atlas binding path: Unity's automatic loading/binding when the bundle lane was built with SpriteAtlas `Include in Build` enabled, or explicit late binding when it was disabled. Do not disable `Include in Build` for a shared bundle lane until every target client can register and resolve the remote atlas, or the content is version-gated.

## Hard Breakers

- Building the bundle with a Unity version newer than a target client can load.
- Building for the wrong platform target.
- Disabling Type Trees for a bundle that must survive schema drift.
- Renaming or moving a bundled script type by assembly, asmdef, namespace, or class.
- Adding bundled components or ScriptableObjects whose classes do not exist in older clients.
- Removing or stripping types that are only referenced from bundled content.
- Changing scripting defines or platform conditions so the serialized layout differs between bundle build lanes and target clients.
- Changing serialized field types in a way older clients cannot interpret.
- Changing bundle asset ids, names, labels, or manifest/dependency contracts expected by runtime code.
- Publishing a bundle without the dependent bundles, shaders, fonts, materials, or resources required by its serialized references.
- Unloading dependencies while dependent bundled objects are still alive.

## Semantic Breakers

- A new field is structurally ignored by old clients but required for correct UI or gameplay.
- A new enum value is sent to old clients that cannot safely ignore it.
- An existing enum integer is renamed with a changed meaning.
- Server or content data depends on a new prefab slot, view path, shader, font, package, or runtime mapper that old clients do not have.
- A bundle contains a SpriteAtlas, but old clients cannot auto-bind it and no late-binding handler registers it, so packed sprites render blank.
- New-client tests pass but the oldest supported client has not been smoke-tested.

## Review Checklist

Before publishing a shared production bundle, record:

1. Oldest supported client version.
2. Oldest supported Unity runtime.
3. Platform target for each bundle.
4. Build options, especially whether Type Trees are present.
5. Runtime script types serialized in the bundle.
6. Assembly, namespace, class, and asmdef identity changes.
7. Serialized fields added, removed, renamed, or type-changed.
8. Enum values added, reordered, reused, or repurposed.
9. Scripting defines or platform conditions that change serialized fields.
10. Required packages, shaders, fonts, materials, and dependent bundles.
11. Dependency load order and unload/lifetime ownership.
12. SpriteAtlas `Include in Build` / automatic binding setting used when the bundle lane was built.
13. Runtime SpriteAtlas late-binding registration or equivalent atlas request path, when automatic binding is disabled.
14. Atlas registration cleanup on bundle unload and destructive unload-all paths.
15. Old-client behavior if new data is ignored.
16. New-client behavior with old bundle data.
17. Oldest-client smoke result.
18. Newest-client smoke result.
19. Verdict: shared bundle safe, or version-gated content required.

## Retiring Published Objects

- Content-addressed keys can make every release leave the previous release's objects absent from the newest manifest while shipped clients continue resolving manifests they fetched earlier. Deleting objects merely because the newest manifest no longer names them can remove exactly what live clients still request.
- Define the authoritative retained-reference set as the union of every published manifest that a supported client may still hold under the product's publication and retention policy. Re-read that authority at the destructive call instead of trusting a local snapshot that may predate another publisher.
- Use object age as an additional fail-safe gate, sized by the maximum supported manifest-hold window rather than CDN TTL; age alone does not prove that an object is unreferenced. If the product policy defines no finite hold window, time-based retirement is not authorized. A missing or unparseable timestamp must read as *new*, so a parse failure protects the object instead of exposing it.

## Decision Test

If the oldest supported client can load the bundle and the product accepts its degraded behavior, one shared bundle may be safe.

If correctness depends on code, assets, mappings, enum meanings, or prefab slots that only newer clients have, the bundle must be version-gated.
