# Public Templates

This folder contains reusable public-safe prompt and scaffold templates.

Templates in this folder may describe host-local inputs or outputs, but they
must not commit concrete host-local paths, private project names, logs,
customer details, generated reports, or dated private evidence artifacts.

Use placeholders such as `<host-output-root>`, `<incident-report-path>`, and
`<output-path>` when a workflow needs host-specific evidence.

## Router Scaffolds

- `REPO_AGENTS_ROUTER_TEMPLATE.md` - repository-level router scaffold.
- `PROJECT_AGENTS_ROUTER_TEMPLATE.md` - project-level router scaffold.

## XUUnity

- `XUUNITY_FIX_CONTRACT_FOLLOWUP_PROMPT_TEMPLATE.md` - evidence-based review
  loop for improving the public `xuunity fix` contract from real incidents
  while keeping concrete incident evidence host-local.
- `XUUNITY_FULL_REVIEW_REPORT_TEMPLATE.md` - public-safe full review report
  shape.
- `XUUNITY_GIT_CHANGE_REVIEW_TEMPLATE.md` - public-safe git-change review
  shape.
- `XUUNITY_KNOWLEDGE_EXTRACTION_CASE_TEMPLATE.yaml` - knowledge-extraction
  evaluation case shape.
- `XUUNITY_KNOWLEDGE_EXTRACTION_REPORT_TEMPLATE.md` - knowledge-extraction
  report shape.
- `XUUNITY_REVIEW_REPORT_TEMPLATE.md` - public-safe review report shape.

## Codex Operations

- `CodexMdToPdf/` - reusable prompt templates for local Markdown-to-PDF
  rendering workflows.
- `CodexSlackMcp/` - reusable prompt templates for Slack MCP file-upload
  workflows.
