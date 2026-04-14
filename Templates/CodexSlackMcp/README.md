# Codex Slack MCP Prompt Templates

Reusable prompt templates for Slack MCP workflows.

These templates are public-safe and intentionally generic:

- they assume the Slack MCP is already installed
- they assume the target channel is fixed by `SLACK_ALLOWED_CHANNEL_ID`
- they do not mention project-private paths or repo-specific reports

Use repo-local prompt packs when you want ready-to-run prompts with real paths for
a specific project or repo.

Templates in this folder:

- `upload_local_file.md`
- `upload_local_file_with_comment.md`
- `upload_local_file_to_thread.md`
