# Future API Providers

API providers are extension points, not v1 defaults.

Future provider shape:

```json
{
  "id": "bedrock",
  "kind": "metered_api",
  "enabled": false,
  "costMode": "metered_paid",
  "requiresExplicitOptIn": true,
  "budgetPolicy": {
    "required": true,
    "maxRunUsd": 1.0
  }
}
```

Rules:

- Disabled by default.
- Explicit config opt-in required.
- Explicit task opt-in required.
- Budget cap required.
- Never used as fallback for missing Claude, Gemini, or Antigravity login.

