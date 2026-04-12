# Skill: SDK Initialization

## Use For
- ad, analytics, attribution, push, and monetization SDK startup

## Rules
- Initialize SDKs in a controlled order based on critical-path requirements.
- Do not block the first interactive user flow on optional SDK readiness.
- Make init completion, timeout, and fallback behavior explicit.
- Contain initialization failures without crashing the app.
- Protect initialization from concurrent double execution when multiple callers can race to initialize the same SDK.
- Prefer explicit initialization state management when retries after failure must remain safe.
- If external SDK init may hang, require a bounded timeout or equivalent recovery strategy.
- Before changing SDK versions, map the exact wrapper version to bundled native SDK and connector versions instead of trusting the top-level package tag alone.
- Treat compatibility-sensitive integrations as versioned startup contracts, not interchangeable package upgrades.
