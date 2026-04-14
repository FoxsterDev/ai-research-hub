# Codex Slack MCP

This folder contains a public-safe setup for a single-channel Slack MCP server
that works with Codex clients which do not expose `/apps` connector UI.

Canonical location:

- `AIRoot/Operations/` because this package contains no secrets
- reusable setup, templates, and installation workflow that can be shared across hosts

Host-local mutable values remain outside the repo:

- `CODEX_HOME/config.toml`
- `CODEX_HOME/slack-single-channel.env`
- local Slack tokens and channel ids

## Goal

Provide a Slack MCP path for Rider/Codex that:

- does not depend on the Slack connector UI
- stores no secrets in the repo
- restricts Codex to exactly one configured Slack channel

## Files

- `init_codex_slack_mcp.sh`
- `templates/server.mjs`
- `templates/run.sh`
- `templates/slack-single-channel.env.template`
- `templates/config.toml.snippet`

Reusable prompt templates:

- `AIRoot/Templates/CodexSlackMcp/`

## Install

From the repo root:

```bash
bash AIRoot/Operations/CodexSlackMcp/init_codex_slack_mcp.sh
```

Dry-run first if you want to inspect changes:

```bash
bash AIRoot/Operations/CodexSlackMcp/init_codex_slack_mcp.sh --dry-run
```

## What It Installs

The script copies files into the local Codex home:

- `~/.codex-tools/slack-single-channel-mcp/server.mjs`
- `~/.codex-tools/slack-single-channel-mcp/run.sh`
- `~/.codex/slack-single-channel.env`
- `~/.codex/config.toml` MCP block when missing

The installed config also pins `slack_post_message` to explicit Codex approval:

- `[mcp_servers.slack_single_channel.tools.slack_post_message]`
- `approval_mode = "prompt"`

If you enable Slack file uploads, the installed config should also pin:

- `[mcp_servers.slack_single_channel.tools.slack_upload_file]`
- `approval_mode = "prompt"`

`CODEX_HOME` is respected. When `CODEX_HOME` is set, the env file is created in
that Codex home. The tools directory still defaults to `~/.codex-tools` unless
`CODEX_TOOLS_HOME` is set.

## Required Secrets

Put these values in `~/.codex/slack-single-channel.env` or the file created
under your `CODEX_HOME`:

- `SLACK_BOT_TOKEN=xoxb-...`
- `SLACK_ALLOWED_CHANNEL_ID=C...` for public channels or `G...` for private channels

Leave this empty unless you explicitly accept broader read access:

- `SLACK_READ_TOKEN=`

## Slack UI Setup

Use this flow to create the Slack app and retrieve the values needed by the
local MCP setup.

### 1. Recommended: create the Slack app from a manifest

This is the preferred path because it reduces manual mistakes and gives the
team a reproducible setup.

Public-channel manifest:

```yaml
display_information:
  name: Apperfun Codex Slack MCP
  description: Single-channel Slack bot for Codex MCP
  background_color: "#1D9BD1"

features:
  bot_user:
    display_name: Apperfun Codex Slack MCP
    always_online: false

oauth_config:
  scopes:
    bot:
      - chat:write
      - channels:history

settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  is_hosted: false
  token_rotation_enabled: false
```

Private-channel manifest:

```yaml
display_information:
  name: Apperfun Codex Slack MCP
  description: Single-channel Slack bot for Codex MCP
  background_color: "#1D9BD1"

features:
  bot_user:
    display_name: Apperfun Codex Slack MCP
    always_online: false

oauth_config:
  scopes:
    bot:
      - chat:write
      - groups:history

settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  is_hosted: false
  token_rotation_enabled: false
```

Manifest import flow:

1. Open `https://api.slack.com/apps`
2. Select `Create New App`
3. Choose `From an app manifest`
4. Select the target workspace
5. Paste the manifest YAML
6. Review and create the app

### 2. Fallback: create the Slack app from scratch

Use this only if manifest import is unavailable or you intentionally want to
configure the app manually.

1. Open `https://api.slack.com/apps`
2. Select `Create New App`
3. Choose `From scratch`
4. Set the app name
   Example: `Apperfun Codex Slack MCP`
5. Select the target workspace
6. Finish app creation

### 3. Configure bot scopes

1. Open the app in the Slack developer portal
2. Go to `OAuth & Permissions`
3. Scroll to `Scopes`
4. Under `Bot Token Scopes`, add:
   - `chat:write`
   - `channels:history` for a public channel
   - `groups:history` for a private channel

Add this only if you want Codex to upload local files into Slack:

- `files:write`

Avoid granting these unless there is a clear operational reason:

- `chat:write.public`
- `chat:write.customize`
- `users:read`
- `channels:read`
- `groups:read`

For first-time diagnostics, temporarily adding `channels:read` for a public
channel can make channel visibility debugging easier. Remove it again after the
setup is stable if you want a tighter permission set.

### 4. Install or reinstall the app

1. Stay on `OAuth & Permissions`
2. Click `Install to Workspace` or `Reinstall to Workspace`
3. Approve the authorization screen

### 5. Copy the bot token

After install, still on `OAuth & Permissions`, copy:

- `Bot User OAuth Token`

Expected format:

- `xoxb-...`

Use that value for:

- `SLACK_BOT_TOKEN`

Do not use these for this MCP setup:

- `App-Level Tokens`
- `Client Secret`
- `Signing Secret`

### 6. Invite the bot to the target channel

Open the target Slack channel and run:

```text
/invite @Apperfun Codex Slack MCP
```

For the safest setup, invite the bot only to the single channel that Codex is
supposed to use.

### 7. Find the channel id

There are two different identifiers you may see in Slack UI. The most reliable
method for this setup is:

1. Open the target channel in Slack
2. Inspect the channel URL
3. Copy the final segment from:
   - `.../client/T.../C...` for public channels
   - `.../client/T.../G...` for private channels

Put that value into:

- `SLACK_ALLOWED_CHANNEL_ID`

If Slack API still rejects the copied id, do one test post by channel name using
the bot token and use the returned `channel` field as the canonical API channel
id. This can happen because some Slack UI surfaces expose identifiers that are
not the same as the conversation id returned by Web API methods.

### 8. Fill the local env file

Open the local file created by the init script and populate it:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_ALLOWED_CHANNEL_ID=C...
SLACK_READ_TOKEN=
```

Leave `SLACK_READ_TOKEN` empty unless you explicitly want broader read access
for thread-reading workflows.

### 9. Restart the Codex client

After updating the env file:

1. Restart Rider or the Codex client
2. Ask Codex to check Slack status
3. Ask Codex to send a small test message

## Recommended Slack App Permissions

Default safe setup:

- `chat:write`
- `channels:history` for a public channel
- `groups:history` for a private channel

Optional only when local file upload is required:

- `files:write`

Do not grant unless you explicitly need them:

- `chat:write.public`
- `chat:write.customize`
- `users:read`
- `channels:read`
- `groups:read`

Operational constraints:

- create one Slack app per project or per workspace
- install the app only into the target workspace
- invite the bot only into the single allowed channel
- do not reuse one broad Slack app across unrelated projects

## Safety Model

The MCP server does not expose a `channel` argument. All reads and writes are
hard-wired to `SLACK_ALLOWED_CHANNEL_ID`.

Available tools:

- `slack_channel_status`
- `slack_read_recent`
- `slack_post_message`
- `slack_upload_file`

`slack_post_message` should require an explicit Codex approval prompt via the
installed config block:

```toml
[mcp_servers.slack_single_channel.tools.slack_post_message]
approval_mode = "prompt"
```

`slack_upload_file` should also require explicit Codex approval:

```toml
[mcp_servers.slack_single_channel.tools.slack_upload_file]
approval_mode = "prompt"
```

`slack_upload_file` is intentionally narrow:

- uploads only to `SLACK_ALLOWED_CHANNEL_ID`
- accepts only local `.md`, `.markdown`, and `.txt` files
- defaults to a 1 MiB maximum file size
- uses Slack's current external upload flow:
  - `files.getUploadURLExternal`
  - `files.completeUploadExternal`

## Prompt Templates

Public reusable prompt templates live in:

- `AIRoot/Templates/CodexSlackMcp/README.md`
- `AIRoot/Templates/CodexSlackMcp/upload_local_file.md`
- `AIRoot/Templates/CodexSlackMcp/upload_local_file_with_comment.md`
- `AIRoot/Templates/CodexSlackMcp/upload_local_file_to_thread.md`

Repo-scoped prompt packs may add ready-to-run prompts with real local paths for a
specific project or workflow.

`slack_read_thread` is intentionally not enabled by default because Slack thread
reads in channels often require broader access than the default safe bot-token
setup.

## Recommended Verification Flow

When onboarding a new teammate or workspace, validate in this order:

1. `auth.test` with the bot token
2. `conversations.history` against the configured channel id
3. `chat.postMessage` with a short test payload

If step 3 succeeds, treat the returned `channel` value as the canonical API
channel id for the env file.
