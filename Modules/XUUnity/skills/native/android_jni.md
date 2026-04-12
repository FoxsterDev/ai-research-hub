# Skill: Android JNI

## Use For
- JNI bridge implementation
- Android plugin audits
- Unity to Java or Kotlin marshaling

## Rules
- `JNIEnv` is thread-local and must never cross threads.
- Native threads must attach before JNI work and detach before exit.
- Check and handle JNI exceptions after each critical call.
- Validate local and global reference lifetime explicitly.
- Cache `jmethodID`, `jfieldID`, and class references during stable init paths.
- Use `DeleteLocalRef` inside loops to avoid local reference table overflow.
- Do not treat `UnitySendMessage` as the default bridge for arbitrary background-thread callbacks.

## Review Focus
- JNI ownership
- exception handling
- thread attachment safety
- marshaling cost and bridge correctness
