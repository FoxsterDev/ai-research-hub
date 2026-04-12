# Skill: SDK Callback Safety

## Use For
- async callbacks
- listener-based SDK APIs
- resume and reward flows

## Rules
- Treat SDK callbacks as untrusted input.
- Guard against duplicate, delayed, out-of-order, and cross-scene callbacks.
- Do not assume callback thread affinity without explicit evidence.
- Keep monetization and attribution callbacks crash-safe and idempotent.
- If callback thread origin is not guaranteed, explicitly return to the Unity main thread before touching Unity APIs, Unity objects, or Unity-bound SDK flows.
- Keep callback result handling safe when SDK responses are malformed, missing fields, or semantically inconsistent.
