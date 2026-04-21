# Skill: Bridge Contracts

## Use For
- JNI bridges
- Objective-C, Objective-C++, Swift bridges
- Unity-to-native contracts

## Rules
- Keep bridge payloads explicit, versionable, and minimal.
- Validate nullability, optional values, and failure cases across the boundary.
- Prefer one clear ownership model per bridge API.
- Recoverable bridge startup failure should become explicit bridge state, not uncaught native or managed exception control flow.
- Keep bridge ownership narrow. Do not let a permission, privacy, or SDK wrapper own unrelated attribution, plist, or product-domain responsibilities.
- Keep Unity-facing wrappers stable even if native details change.
- When a higher orchestration layer already owns public callbacks, prefer platform bridge methods that execute or throw rather than mixing direct user callback invocation with exception control flow in the same platform path.
- Prefer direct, typed bridge contracts over stringly-typed fallback channels on critical paths.
- For high-frequency callbacks, use bridge shapes that preserve thread ownership and reduce marshaling overhead.
- By default, callbacks, events, and async completions that re-enter Unity from native code should hand off to the Unity main thread unless the contract explicitly says otherwise.
- If a bridge exposes both Unity-safe and immediate threaded callback surfaces, make the thread-affinity difference explicit in API naming and documentation.
- For queued callback hops, prefer safe ownership-transfer shapes over carrying raw unmanaged pointers across the hop when a safer object or string transfer can express the same data.
- If the public bridge exposes a direct native request entrypoint, protect the request path itself against duplicate in-flight calls instead of relying only on higher-level async sharing.
- When platform split is already enforced by factory or assembly boundaries, do not duplicate platform routing with runtime platform checks inside the platform-specific implementation.
- In platform-specific implementations, keep `#if` usage narrow and limited to code that would not compile on the current target, such as interop declarations or editor-only APIs.
- If a platform-specific managed bridge file is still compiled for other targets, wrap native interop declarations such as `DllImport("__Internal")` in compile-time platform defines and provide same-signature fallback stubs for unsupported targets so IL2CPP and native link steps never see unresolved symbols from the wrong platform.
- If a native bridge call can wait on non-cooperative lower layers, design a bounded recovery path instead of trusting caller cancellation alone.
- Prefer ANR prevention and flow recovery over perfect cleanup when the native side can hang outside application control.
