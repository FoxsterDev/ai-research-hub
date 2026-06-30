# Provider Registry

The user-local registry lives at:

```text
~/.xuunity/ai-cli-orchestrator/config.json
```

Provider order is controlled by:

```json
"providerPreference": ["claude_cli", "gemini_cli", "antigravity"]
```

The orchestrator chooses the first enabled, ready provider in that list unless a
prompt or command-line override selects a provider.

## Policy Fields

- `providerPreference`: provider selection order.
- `delegationMode`: default task shape, usually `auto_phased`.
- `maxPhaseCount`: maximum worker phases for broad tasks.
- `maxPhaseSeconds`: maximum time budget per worker phase.

## Provider Fields

- `id`: stable provider id.
- `kind`: `subscription_cli` or future `metered_api`.
- `enabled`: whether the provider participates in selection.
- `authMode`: official login or OAuth mode.
- `costMode`: `subscription_quota`, `subscription_or_account_quota`, or future
  `metered_paid`.
- `apiKeyAuthAllowed`: must be `false` for subscription providers.
- `command`: local CLI command name.
- `modelPolicy`: default and fallback model selection.
- `authStatusCommand`: optional command array used by adapters whose official
  login probe varies by installation. If a provider cannot prove login state, it
  must report `degraded` instead of being selected.
- `acceptedSubscriptionTypes`: Claude subscription types accepted as quota-backed
  official login, defaulting to `pro`, `team`, `max`, and `enterprise`.
