# Skill: Android Graphics API Selection

## Use For
- Android graphics API choice
- Vulkan versus OpenGLES3 tradeoffs
- startup and stability review for Android rendering configuration

## Rules
- Do not assume Vulkan is enabled automatically in Unity Android builds; graphics API ordering must be configured explicitly.
- `OpenGLES3`-only remains a valid broad-compatibility and predictability-first baseline for Android.
- For wide consumer Android distribution, prefer `Vulkan` first with `OpenGLES3` fallback over `Vulkan`-only when testing budget allows.
- Treat graphics API choice as a device-risk decision, not only a theoretical performance decision.
- Validate graphics API changes on a representative device matrix across OEMs, GPU families, and low/mid-tier Android hardware.
- When evaluating startup impact, compare graphics API initialization against bigger startup drivers such as SDK init, shader setup, and first-scene/content load.
- If Vulkan is enabled, collect runtime evidence by device model, GPU family, selected graphics API, and crash cluster before treating it as a stable broad-market default.

## Review Prompts
- Is this project optimizing for broad compatibility or for maximum render performance on modern hardware?
- Is `Auto Graphics API` disabled when deterministic ordering is required?
- Does the build keep `OpenGLES3` fallback when Vulkan-tail driver risk is non-trivial?
- Has the team tested Samsung, Pixel, Xiaomi/Redmi, and at least one or two lower-tier devices?
- Are startup regressions being attributed correctly, rather than assuming the graphics API is the dominant cost?

## Anti-Patterns
- enabling `Vulkan` and assuming “supported” means production-safe across vendor firmware
- treating `Vulkan`-only as the default recommendation for mass-market Android
- blaming startup time on the graphics API without separating SDK init, content load, and shader work
- changing API ordering without device-matrix validation
