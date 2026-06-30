# Auth Policy

The v1 policy is `official_login_only`.

## Subscription Providers

Claude CLI, Gemini CLI, and Antigravity must use official account login or OAuth
state owned by the installed provider tool.

The orchestrator must not:

- accept API-key-only auth for subscription providers
- pass model API-key environment variables into subscription-provider runs
- silently switch from account quota to API billing when login is missing

If a subscription provider is not logged in, it is skipped.

For Claude CLI, `doctor` must prove:

- `loggedIn: true`
- `authMethod: claude.ai`
- `apiProvider: firstParty`
- an accepted subscription type such as `pro`, `team`, `max`, or `enterprise`

Any other successful status output is treated as degraded, not ready.

## Metered Providers

Metered API providers are reserved for future extension. They must be disabled
by default, explicitly opted in, and budget-capped before any run.
