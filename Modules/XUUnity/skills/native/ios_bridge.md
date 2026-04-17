# Skill: iOS Bridge

## Use For
- Objective-C, Objective-C++, and Swift bridge code
- Unity as a Library integration
- native callback design

## Rules
- Keep UIKit and app lifecycle work on the main thread.
- Gate permission prompts by active app state instead of assuming startup flows are already in a valid presentation state.
- Use `@autoreleasepool` on high-frequency or background native paths when needed.
- Make delegate lifetime explicit for callbacks into C#.
- Unless the bridge contract explicitly opts out, return Unity-facing callbacks, events, and async results to the Unity main thread before managed consumers continue.
- Handle Core Foundation ownership explicitly on both success and failure paths.
- If native code returns strings or buffers to C#, make memory handoff explicit and release from managed code in a deterministic cleanup path.
- If the bridge exposes a direct native request API, make duplicate calls single-flight safe instead of relying only on higher-level async wrappers.
- Use `[weak self]` in closures that capture long-lived controllers or bridge objects unless strong ownership is required.
- In Unity as a Library setups, validate init order, lifecycle callbacks, symbolication, and `MachHeader` handoff.
- If Swift is called directly from C#, keep thread isolation explicit with `@_cdecl`, `nonisolated`, and `@MainActor` as needed.
- If the bridge uses observer-style Apple networking APIs such as `NWPathMonitor`, start them on a dedicated queue, keep callback work cheap, and make teardown explicit with the matching cancellation path.
- Do not escalate advisory network-path observations into strong product decisions inside native code. Normalize the signal, preserve confidence, and let managed policy decide how much certainty is required.
- When inspecting system proxy state through Core Foundation or CFNetwork APIs, keep parsing nil-safe and type-safe instead of assuming keys, value classes, or collection shapes are always present.
- If bridge code combines multiple native signals into one Unity-facing state object, deduplicate state changes before dispatching into managed code so path observers do not create avoidable callback churn.

## Review Focus
- ARC and ownership safety
- callback lifetime
- lifecycle correctness
- embedding risk
- observer queue ownership and teardown symmetry
- Core Foundation parsing safety on lossy or partially populated dictionaries
