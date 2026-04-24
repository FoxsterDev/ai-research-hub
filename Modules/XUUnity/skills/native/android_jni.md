# Skill: Android JNI

## Use For
- JNI bridge implementation
- Android plugin audits
- Unity to Java or Kotlin marshaling

## Rules
- `JNIEnv` is thread-local and must never cross threads.
- Native threads must attach before JNI work and detach before exit.
- Check and handle JNI exceptions after each critical call.
- Any `AndroidJavaObject` or `AndroidJavaClass` call from C# must handle `AndroidJavaException`, either directly at the call site or through a centralized interop wrapper.
- Validate local and global reference lifetime explicitly.
- Do not assume `AndroidJavaObject` wrappers returned from Unity APIs are caller-owned. Verify ownership before calling `Dispose`, especially for activity and context accessors.
- Treat `AndroidApplication.currentActivity` as a Unity-owned borrowed wrapper. Do not call `Dispose()` on that object from SDK or bridge code.
- Keep Unity `currentActivity` access and Android UI-thread posting in one small interop helper instead of repeating ownership and thread-handoff logic at every bridge call site.
- Prefer paired interop wrappers for Java calls:
  - `CallOrThrow` or equivalent for required bridge operations
  - `TryCall` or `TryDispose` or equivalent for best-effort cleanup and teardown
- Pass a human-readable operation name into interop wrappers so Android bridge failures are translated into consistent managed errors and logs without repeating string formatting at every call site.
- Normalize `AndroidJavaException` into one managed exception shape at the interop boundary instead of scattering ad-hoc catch blocks across platform code.
- Prefer extension methods or equivalent helper surface on `AndroidJavaObject` and `AndroidJavaClass` when they reduce repeated null checks, exception translation, and cleanup boilerplate without hiding real ownership decisions.
- Cache `jmethodID`, `jfieldID`, and class references during stable init paths.
- Use `DeleteLocalRef` inside loops to avoid local reference table overflow.
- Do not treat `UnitySendMessage` as the default bridge for arbitrary background-thread callbacks.
- Name Android bridge collaborators by role such as payment bridge, browser class, or listener proxy instead of generic `_bridge` or `_proxy` fields when the class owns more than one native concern or is likely to grow.

## Review Focus
- JNI ownership
- Unity-owned versus caller-owned wrapper lifetime assumptions
- exception handling
- thread attachment safety
- marshaling cost and bridge correctness
- interop helper quality
- strict-versus-best-effort JNI call separation
- operation-name context quality in Android bridge failures
