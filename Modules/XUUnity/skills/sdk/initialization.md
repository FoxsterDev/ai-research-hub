# Skill: SDK Initialization

## Use For
- ad, analytics, attribution, push, and monetization SDK startup

## Rules
- Initialize SDKs in a controlled order based on critical-path requirements.
- Do not block the first interactive user flow on optional SDK readiness.
- Make init completion, timeout, and fallback behavior explicit.
- Contain initialization failures without crashing the app.
- Expected native or plugin init failure must resolve to explicit non-operational state with actionable error information; do not let recoverable init failure look like successful startup.
- If callback or listener registration fails during init, fail initialization deterministically instead of only logging and continuing.
- Do not collapse `failed to initialize`, `not initialized yet`, and `initialized but no data yet` into the same public wrapper state.
- Protect initialization from concurrent double execution when multiple callers can race to initialize the same SDK.
- Prefer explicit initialization state management when retries after failure must remain safe.
- If external SDK init may hang, require a bounded timeout or equivalent recovery strategy.
- Before changing SDK versions, map the exact wrapper version to bundled native SDK and connector versions instead of trusting the top-level package tag alone.
- Treat compatibility-sensitive integrations as versioned startup contracts, not interchangeable package upgrades.
