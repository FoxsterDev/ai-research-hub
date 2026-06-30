# Security

`XUUnityAiCliOrchestrator` is subscription-first and login-first.

## Do

- Use official provider login or OAuth.
- Keep provider config under `~/.xuunity/ai-cli-orchestrator/`.
- Keep generated run reports in the user-local report directory.
- Use read-only project access by default.
- Enable writes only for trusted repos and explicitly opted-in tasks.

## Do Not

- Do not store OAuth tokens, account cookies, API keys, or secrets in this repo.
- Do not enable API-key fallback for Claude, Gemini, or Antigravity subscription
  adapters.
- Do not run unattended external AI from home-level folders, Desktop,
  Downloads, Documents root, or iCloud roots.
- Do not allow metered API providers without explicit opt-in and budget limits.

## API Keys

The orchestrator intentionally scrubs common model API-key environment variables
from subscription-backed provider subprocesses. If an official-login provider is
not authenticated, it is skipped instead of silently switching to API billing.

