# Skill: Bridge Contracts

## Use For
- JNI bridges
- Objective-C, Objective-C++, Swift bridges
- Unity-to-native contracts

## Rules
- Keep bridge payloads explicit, versionable, and minimal.
- Validate nullability, optional values, and failure cases across the boundary.
- Prefer one clear ownership model per bridge API.
- Keep bridge ownership narrow. Do not let a permission, privacy, or SDK wrapper own unrelated attribution, plist, or product-domain responsibilities.
- Keep Unity-facing wrappers stable even if native details change.
- Prefer direct, typed bridge contracts over stringly-typed fallback channels on critical paths.
- For high-frequency callbacks, use bridge shapes that preserve thread ownership and reduce marshaling overhead.
- By default, callbacks, events, and async completions that re-enter Unity from native code should hand off to the Unity main thread unless the contract explicitly says otherwise.
- If the public bridge exposes a direct native request entrypoint, protect the request path itself against duplicate in-flight calls instead of relying only on higher-level async sharing.
- When platform split is already enforced by factory or assembly boundaries, do not duplicate platform routing with runtime platform checks inside the platform-specific implementation.
- In platform-specific implementations, keep `#if` usage narrow and limited to code that would not compile on the current target, such as interop declarations or editor-only APIs.
- If a native bridge call can wait on non-cooperative lower layers, design a bounded recovery path instead of trusting caller cancellation alone.
- Prefer ANR prevention and flow recovery over perfect cleanup when the native side can hang outside application control.
