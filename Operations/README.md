# Operations

This folder contains public operational surfaces for `AIRoot`.

Use a strict split:
- host bootstrap and onboarding -> `Operations/Setup/`
- reusable handbooks and operator guides -> `Operations/*.md`
- public tool-specific or surface-specific operation packages ->
  `Operations/<ToolOrSurface>/`

## Start Here

For new host setup:
- `Setup/AI_ASSISTED_SETUP_PROMPT.md`
- `Setup/AI_EASY_SETUP.md`
- `Setup/SETUP_INDEX.md`

For normal operator usage after setup:
- `AI_PROTOCOL_HANDBOOK.md`
- `AI_PRODUCT_FACING_GUIDE.md`

## Tool And Surface Packages

These are not part of the host bootstrap path.

- `CodexSlackMcp/`
  Fixed-surface Slack delivery setup and usage.
- `XUUnityLightUnityMcp/`
  Public lightweight Unity MCP surface for `xuunity`.
- `XUUnityAiCliOrchestrator/`
  Public subscription-first AI CLI orchestration surface for opt-in XUUnity
  external AI runs.
- `XUUNITY_TASK_REGISTRY_PUBLIC_REPORT.md`
  Public-safe report for the `xuunity` task registry surface.

Rule:
- keep `Setup/` focused on making the host repo ready
- keep optional tool installers and tool-specific operation docs in their own
  operation folders
