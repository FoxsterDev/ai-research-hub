# Skill: SDK Callback Safety

## Use For
- async callbacks
- listener-based SDK APIs
- resume and reward flows

## Rules
- Treat SDK callbacks as untrusted input.
- Guard against duplicate, delayed, out-of-order, and cross-scene callbacks.
- Do not assume callback thread affinity without explicit evidence.
- Keep callback thread-affinity policy in one owner only. Prefer a single decorator or equivalent boundary over dispatch logic split across facade, orchestration, and platform layers.
- Keep monetization and attribution callbacks crash-safe and idempotent.
- If callback thread origin is not guaranteed, explicitly return to the Unity main thread before touching Unity APIs, Unity objects, or Unity-bound SDK flows.
- Tie callback registration lifetime to the real external launch or open point. Do not register close or resume callbacks earlier than the moment the external flow is actually attempted.
- Keep callback result handling safe when SDK responses are malformed, missing fields, or semantically inconsistent.
