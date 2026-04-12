# Skill: Bridge Contracts

## Use For
- JNI bridges
- Objective-C, Objective-C++, Swift bridges
- Unity-to-native contracts

## Rules
- Keep bridge payloads explicit, versionable, and minimal.
- Validate nullability, optional values, and failure cases across the boundary.
- Prefer one clear ownership model per bridge API.
- Keep Unity-facing wrappers stable even if native details change.
- Prefer direct, typed bridge contracts over stringly-typed fallback channels on critical paths.
- For high-frequency callbacks, use bridge shapes that preserve thread ownership and reduce marshaling overhead.
- If a native bridge call can wait on non-cooperative lower layers, design a bounded recovery path instead of trusting caller cancellation alone.
- Prefer ANR prevention and flow recovery over perfect cleanup when the native side can hang outside application control.
