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

## Packed Asset Attribution
- Group `PackedAssetInfo` rows by `sourceAssetPath` before ranking.
- When `sourceAssetPath` is empty, group by `sourceAssetGUID` or an explicit generated/internal marker.
- Count entries as well as bytes; one source asset can produce multiple packed rows.
- Expect built-in Unity assets, generated assets, and internal resources in the ranking. Do not present the list as project-authored files only.

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
- Explaining a plugin or IL2CPP delta only with `packedAssets`.
- Treating exact MiB savings from a sample project as reusable constants.
- Turning a measured local result such as a texture format, audio quality, or font subset into a blanket public rule.

## Cross-Links
- `knowledge/validation_lanes.md` for the validation lane when artifact build evidence is required.
- `knowledge/unity_validation_boundaries.md` for generated-artifact proof boundaries.
- `skills/profiling/regression_detection.md` for before/after regression review.
- `skills/editor/import_pipeline.md` for import-setting validation.
