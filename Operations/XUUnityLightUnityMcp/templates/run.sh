#!/bin/zsh
set -euo pipefail

# Self-resolving install root. Works for any host install path (codex-tools,
# claude-tools, agent-agnostic, custom). Honors XUUNITY_LIGHT_UNITY_MCP_SERVER
# for explicit overrides.
script_dir="${0:A:h}"
server_file="${XUUNITY_LIGHT_UNITY_MCP_SERVER:-$script_dir/server.py}"

exec python3 "$server_file" "$@"
