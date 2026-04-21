# Skill: Startup Bridge Narrowing

## Derived From
- reviewed startup permission-bridge refactor artifact

## Use For
- startup consent or permission bridge refactors
- native plugin boundary cleanup on critical startup paths
- ownership cleanup around startup-time SDK or platform wrappers

## Rules
- Narrow startup wrappers to one responsibility so consent, attribution, analytics, and other startup domains do not compete for ownership.
- If a platform prompt or startup action depends on app-active state, make that lifecycle gate explicit before the native call.
- Protect direct public request entrypoints against duplicate in-flight calls when the bridge is request-shaped.
- Hand async completion back to the documented Unity-safe thread before finishing the public contract.
- Add behavior-locking tests for delayed completion, concurrent callers, and startup timing edges before deleting the legacy path.
