# Skill: TextMeshPro Static Font Asset Generation

## Use For
- generating or rebuilding a static SDF `TMP_FontAsset` from a source font in editor code
- a label that renders nothing, or `UnassignedReferenceException` from `GetFallbackMaterial`, right after a font asset rebuild
- a font asset whose file name claims a weight its glyphs do not show

## Generation Recipe
1. `TMP_FontAsset.CreateFontAsset(font, samplingPointSize, padding, GlyphRenderMode.SDFAA, atlasWidth, atlasHeight, AtlasPopulationMode.Dynamic, enableMultiAtlasSupport: false)`.
2. `TryAddCharacters(characterSet, out missing)` and treat a non-empty `missing` as a failure.
3. Switch `atlasPopulationMode` to `Static`, then persist the atlas texture and material with `AssetDatabase.AddObjectToAsset`.

## Rules
- A static asset must fit in **one** atlas. With multi-atlas enabled, overflow glyphs land on atlas index 1. That secondary texture is not persisted as a sub-asset, so the glyphs render as nothing and the fallback-material lookup throws. Lower `samplingPointSize` or raise the atlas size until every glyph in the saved asset has `m_AtlasIndex: 0`.
- Rebuild a shared asset **in place**: keep the asset GUID and the existing material and atlas-texture fileIDs. Serialized `m_sharedMaterial` references in prefabs point at those fileIDs and break silently when a fresh asset replaces the file.
- After a shared rebuild, render **every** consumer, not only the screen that triggered the change.
- Trust the asset's face data, not its file name: check `m_FaceInfo.m_StyleName` and the source font reference before relying on a weight.

## What This Is Not
- Runtime dynamic atlases and fallback chains, where secondary atlases are created at runtime → `glyph_coverage.md`.
- Choosing which characters a product needs → `glyph_coverage.md` (artifact-size note).
