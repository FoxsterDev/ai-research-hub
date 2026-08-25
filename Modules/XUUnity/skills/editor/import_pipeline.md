# Skill: Import Pipeline

## Use For
- asset import automation
- validation on import
- platform import settings

## Rules
- Enforce import settings that are critical for mobile memory, texture size, and compression.
- Treat texture format, audio format, and font coverage/subsetting as mobile build-size settings that need validation and reporting, not only visual or audio quality settings. Keep exact size deltas project-local unless they were measured in the target project.
- Avoid hidden import-time mutations that are hard to debug.
- Keep import hooks deterministic and idempotent.
- Separate validation from auto-fix when the change may be risky.
- When moving a Unity asset without changing its meaning or visual output, move the existing `.meta` with it and preserve the GUID.
- Treat a regenerated GUID as a new asset identity, not as a harmless import detail.
- Before broad YAML reference rewrites after an asset move, check whether restoring the original `.meta` GUID would preserve references with a smaller, safer diff.
- When consolidating child-project copies into a shared asset, audit duplicate GUIDs and visually identical local copies before deleting assets or rewriting references.
- You cannot persist `.meta` edits on registry or git UPM packages (the package cache is immutable; `SaveAndReimport` on a package asset does not stick). To retune import settings on third-party package assets non-destructively and upgrade-safely, drive an `AssetPostprocessor.OnPreprocessTexture` (it runs for package assets) from a version-controlled override table (path-glob to per-platform max size / format / crunch). Apply only to explicit table entries, never as a blanket rule. Alternative: vendor the asset into the project.
- A texture's sprite sub-asset identity depends on its sprite mode, and changing that mode rewrites every reference to it. In single-sprite mode the sprite carries the fixed legacy local file id `21300000` (the same family of constants as `2800000` for the texture itself); in multi-sprite mode each sub-sprite gets a generated 64-bit id, negative as often as not recorded in the importer's id-to-name table and referenced from prefabs and scenes by that id. Switching multi to single deletes those sub-objects, so every existing reference resolves to nothing and renders as a missing sprite; switching back restores them, because the importer keeps the stale table on purpose. Treat a sprite-mode change on a referenced sheet as a reference migration, not an import tweak: repoint every referrer in the same change, or widen a sub-rect while keeping its generated id, which is the reference-preserving alternative.
- Before switching a referenced sheet to single-sprite mode, measure whether the referenced sub-rect is the full texture or a crop. If it is a crop, the switch also changes the rendered region and the sprite's dimensions, so it is a visual change on top of a reference change — keep such sheets in multi-sprite mode instead of "unifying" them.
- Reference-by-generated-id is also a review-cost problem, not only a correctness one: the serialized referrer shows an opaque signed integer instead of a sprite name, so a reviewer cannot distinguish a valid reference from a broken one without cross-reading the importer's id-to-name table. Prefer the single-sprite shape for new art precisely so that references stay readable.
