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
- If the public wrapper also promises any-thread entry, keep ingress normalization owned separately and explicitly. A stable default is:
  - facade owns ingress normalization
  - one dispatching layer owns egress normalization
- When a strategy or orchestration layer exists, let it own public callback adaptation. Platform adapters should report sync failure or native completion, not directly own user callback policy.
- If an SDK asynchronously generates or returns a destination URL for an external launch, let the adapter request or report that destination, but keep navigation policy, validation, and fallback ownership at a higher orchestration layer.
- Do not bury external-open policy inside the raw SDK callback when the caller needs product control over fallback order, attribution preservation, or installed-versus-store routing.
- If ingress normalization already exists above the platform adapter, prefer deleting redundant platform-thread posting rather than keeping a second hidden normalization layer.
- Keep monetization and attribution callbacks crash-safe and idempotent.
- If callback thread origin is not guaranteed, explicitly return to the Unity main thread before touching Unity APIs, Unity objects, or Unity-bound SDK flows.
- If platform work is posted and can fail later on a platform thread, verify that those failure callbacks still honor the documented success-and-failure thread contract.
- Tie callback registration lifetime to the real external launch or open point. Do not register close or resume callbacks earlier than the moment the external flow is actually attempted.
- Keep callback result handling safe when SDK responses are malformed, missing fields, or semantically inconsistent.
