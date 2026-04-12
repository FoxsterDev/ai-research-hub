# Skill: Ownership

## Use For
- native resource lifetime
- wrapper safety
- interop boundaries

## Rules
- Make ownership of native handles, listeners, and buffers explicit.
- Avoid ambiguous cleanup responsibilities across C#, Java/Kotlin, and Objective-C/Swift layers.
- Prefer safe teardown over aggressive reuse when lifecycle uncertainty is high.
- Contain bridge failures so they do not take down the Unity runtime.
