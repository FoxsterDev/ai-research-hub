#!/bin/zsh
set -euo pipefail

tools_home="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
server_file="$tools_home/xuunity-light-unity-mcp/server.py"

exec python3 "$server_file" "$@"
