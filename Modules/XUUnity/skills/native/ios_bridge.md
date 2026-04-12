# Skill: iOS Bridge

## Use For
- Objective-C, Objective-C++, and Swift bridge code
- Unity as a Library integration
- native callback design

## Rules
- Keep UIKit and app lifecycle work on the main thread.
- Use `@autoreleasepool` on high-frequency or background native paths when needed.
- Make delegate lifetime explicit for callbacks into C#.
- Handle Core Foundation ownership explicitly on both success and failure paths.
- Use `[weak self]` in closures that capture long-lived controllers or bridge objects unless strong ownership is required.
- In Unity as a Library setups, validate init order, lifecycle callbacks, symbolication, and `MachHeader` handoff.
- If Swift is called directly from C#, keep thread isolation explicit with `@_cdecl`, `nonisolated`, and `@MainActor` as needed.

## Review Focus
- ARC and ownership safety
- callback lifetime
- lifecycle correctness
- embedding risk
