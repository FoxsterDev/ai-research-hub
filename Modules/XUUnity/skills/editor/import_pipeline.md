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
