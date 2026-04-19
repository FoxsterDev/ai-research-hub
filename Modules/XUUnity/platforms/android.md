# Android Platform Guidance

## Use For
- Android-specific checks after the shared `XUUnity` skill layer is loaded
- JNI, permissions, lifecycle, and ANR-sensitive Android behavior

## Load First
- `skills/native/android_jni.md`
- `skills/native/bridge_contracts.md`
- `skills/native/callback_lifetime.md`
- `skills/optimization/bridge_performance.md`
- `skills/mobile/critical_flows.md`
- `skills/mobile/graphics_api_selection.md`

## Android-Specific Checks
- Validate permission flow behavior against the actual Android feature set and SDK usage.
- Review Android lifecycle paths for pause, resume, notification return, and process recreation sensitivity.
- Confirm JNI thread attachment and callback threading on real Android flows, not only editor assumptions.
- Check ANR risk on startup, resume, purchase, and ad-return flows.
- When diagnosing manifest or dependency regressions, confirm that the inspected Gradle and merged-manifest outputs belong to the same fresh build under investigation.
- Inspect the same-build `Editor.log` for resolver, manifest merger, and `IPostGenerateGradleAndroidProject` callback execution before concluding that a vendor postprocessor failed.
- If `Library/` was recently deleted or the project was reimported, bias toward artifact freshness validation before recommending source-manifest edits.
- Treat source-level duplication of vendor-managed Android declarations as a workaround, not a default fix, unless the project intentionally takes ownership of that declaration.
- Verify graphics API ordering explicitly when Vulkan versus `OpenGLES3` tradeoffs affect startup, crash risk, or device coverage.
- Require representative OEM and GPU-family validation before recommending `Vulkan`-preferred Android builds at scale.
- Keep a forward-looking verification note in release/compliance reviews:
  - re-check upcoming Android developer verification and distribution-policy milestones by date and region
  - call out when those milestones may affect non-Play or multi-channel distribution plans

## Review Output
- Android-only lifecycle risks
- JNI and ANR risks that remain after shared skill review
- permission and manifest concerns
- build-log-backed ownership and freshness conclusions for manifest issues
