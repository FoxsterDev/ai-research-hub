# Model Selection

Default model policy:

```text
best_available
```

Each adapter maps that policy to the best model it can safely request from its
official-login CLI. For Claude CLI, the default fallback alias is `opus` because
it is a stable top-model alias in the current local research.

Rules:

- Use the best available model unless the prompt or command line overrides it.
- Prefer stable provider aliases over fragile exact model ids.
- If a model override is unavailable, the provider should fail visibly rather
  than silently downgrade to API billing.
- Model selection must not change auth policy.
- Pass `--effort` only when the selected adapter supports it. Claude currently
  accepts `low`, `medium`, `high`, `xhigh`, and `max`; invalid values fail before
  launch and the selected effort is recorded in the normalized result.
