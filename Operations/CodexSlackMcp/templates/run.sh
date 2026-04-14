#!/bin/zsh
set -euo pipefail

codex_home="${CODEX_HOME:-$HOME/.codex}"
tools_home="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
env_file="${SLACK_SINGLE_CHANNEL_ENV_FILE:-$codex_home/slack-single-channel.env}"
server_file="$tools_home/slack-single-channel-mcp/server.mjs"
original_slack_bot_token="${SLACK_BOT_TOKEN-}"
original_slack_allowed_channel_id="${SLACK_ALLOWED_CHANNEL_ID-}"
original_slack_read_token="${SLACK_READ_TOKEN-}"

if [[ -f "$env_file" ]]; then
  set -a
  source "$env_file"
  set +a
fi

if [[ -n "$original_slack_bot_token" ]]; then
  export SLACK_BOT_TOKEN="$original_slack_bot_token"
fi

if [[ -n "$original_slack_allowed_channel_id" ]]; then
  export SLACK_ALLOWED_CHANNEL_ID="$original_slack_allowed_channel_id"
fi

if [[ -n "$original_slack_read_token" ]]; then
  export SLACK_READ_TOKEN="$original_slack_read_token"
fi

exec node "$server_file"
