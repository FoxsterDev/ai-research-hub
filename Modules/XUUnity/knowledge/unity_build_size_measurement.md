# XUUnity Knowledge: Unity Build Size Measurement

Use this file when a task investigates Unity build size, APK/AAB size, BuildReport numbers, packed asset attribution, plugin/code-size deltas, or mobile asset-size regressions.

## Rule
- Do not say `build size` as one number. Name the measured byte surface.
- Keep final artifact bytes, Unity build-output total, packed asset bytes, and native/managed code or metadata deltas separate.
- Treat packed asset rankings as asset evidence, not whole-build truth.
- For code, plugin, IL2CPP, stripping, or metadata questions, inspect final/generated artifact contents in addition to `BuildReport.packedAssets`.

## Measurement Surfaces
- **Final artifact bytes**: the APK/AAB/IPA or other file on disk. This is the user/download-sized artifact when the build output is a single file.
- **`BuildReport.summary.totalSize`**: Unity's reported total build output size. Do not relabel it as download size.
- **Packed asset total**: the sum of `BuildReport.packedAssets[].contents[].packedSize`. This is serialized asset/object data inside packed build files.
- **Native/managed artifact deltas**: changes inside generated files such as native libraries, managed metadata, symbols, Gradle/Xcode output, or package contents.
- **Runtime GPU/VRAM footprint**: `width × height × bpp` for a texture; it does not shrink with packaging. ETC2-RGBA / ASTC-4×4 = 8 bpp (1 B/px); RGBA32 = 32 bpp (4 B/px). This ≈ the packed/decompressed size and is a distinct surface from download bytes.

## Packed Asset Attribution
- Group `PackedAssetInfo` rows by `sourceAssetPath` before ranking.
- When `sourceAssetPath` is empty, group by `sourceAssetGUID` or an explicit generated/internal marker.
- Count entries as well as bytes; one source asset can produce multiple packed rows.
- Expect built-in Unity assets, generated assets, and internal resources in the ranking. Do not present the list as project-authored files only.

## Byte-Surface Facts (mobile textures)
- Resolution, not format, is usually the size driver: a 2048² sprite is ~4 MB at 8 bpp regardless of ETC2 versus ASTC-4×4.
- NPOT textures whose dimensions are not divisible by 4 fall back to uncompressed RGBA32 (block compressors need 4-aligned dimensions).
- On Android, non-streamed assets pack into `assets/bin/Data/data.unity3d`, which Unity compresses internally (LZ4HC/LZMA); the APK stores it `Stored` (0%) because it is already compressed. A single asset's download cost is its slice of that container, not its packed MB.
- Verify the split with `unzip -v <apk>` grouped by `lib/*.so` (IL2CPP + engine + SDK native), `classes*.dex` (SDK Java), and `assets/bin/Data`. For SDK-heavy games the download is dominated by native code + DEX, not assets.

## Controlled Build-Size Experiment
1. Fix the build target, compression, scripting backend, architecture, stripping, development-build state, and scene/reference set.
2. Change one variable at a time.
3. Measure final artifact bytes from disk.
4. Record `BuildReport.summary.totalSize`.
5. Record grouped packed asset bytes and top sources.
6. When the delta is not explained by assets, inspect generated/final artifact files for code, native, or metadata growth.
7. Keep raw outputs and enough settings detail for another run to reproduce or challenge the claim.

## Mobile Asset Decisions
- Texture format and block size are build-size, runtime-memory, bandwidth, and visual-quality decisions. Measure on the target platform and inspect visual cost on representative devices.
- Audio compression, sample rate, channel count, and load type are build-size and runtime-behavior decisions. Measure against the clip's access pattern and latency requirements.
- Font coverage, CJK source fonts, fallbacks, and subsets can materially affect mobile artifact size. Measure the shipped character coverage instead of assuming broad source fonts are free.

## Anti-Patterns
- Publishing one `build size` chart without naming the byte surface.
- Using `BuildReport.summary.totalSize` as APK/AAB download size.
- Presenting a texture's packed/VRAM MB as its download cost.
- Treating texture max-size as the download lever when native code and DEX dominate; download levers are release (non-development) build, code stripping/R8, AAB delivery, and single-ABI, while texture size is primarily a VRAM/runtime lever.
- Explaining a plugin or IL2CPP delta only with `packedAssets`.
- Treating exact MiB savings from a sample project as reusable constants.
- Turning a measured local result such as a texture format, audio quality, or font subset into a blanket public rule.

## Cross-Links
- `knowledge/validation_lanes.md` for the validation lane when artifact build evidence is required.
- `knowledge/unity_validation_boundaries.md` for generated-artifact proof boundaries.
- `skills/profiling/regression_detection.md` for before/after regression review.
- `skills/editor/import_pipeline.md` for import-setting validation.
