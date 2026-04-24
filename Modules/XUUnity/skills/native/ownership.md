# Skill: Ownership

## Use For
- native resource lifetime
- wrapper safety
- interop boundaries

## Rules
- Make ownership of native handles, listeners, and buffers explicit.
- Treat Unity-returned Android Java wrappers as borrowed unless ownership is explicit. Do not blindly call `Dispose` on wrappers returned from Unity-owned surfaces.
- Treat `AndroidApplication.currentActivity` specifically as borrowed Unity-owned state, not as a caller-owned `AndroidJavaObject`.
- Avoid ambiguous cleanup responsibilities across C#, Java/Kotlin, and Objective-C/Swift layers.
- Prefer safe teardown over aggressive reuse when lifecycle uncertainty is high.
- Contain bridge failures so they do not take down the Unity runtime.
- For single-in-flight native requests, keep pending completion ownership in one slot and use one take-and-clear handoff so success, error, dispose, and duplicate-request paths cannot double-complete.
- Keep orchestration ownership and platform ownership separate. Strategies or equivalent orchestration layers should own launch policy, public callback adaptation, and high-level flow. Platform adapters should own native contract calls, listener lifetime, payload parsing, and platform-thread rules.
- If wrapper lifetime policy changes across Unity versions or platform access paths, keep that branching in a narrow interop helper instead of scattering ownership decisions across bridge call sites.
- If native teardown depends on a specific platform thread, do not silently retry the same native cleanup off-thread after scheduling failure. Log the failure and prefer managed-state cleanup only.
