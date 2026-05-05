#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOST_WRAPPER_PATH="$REPO_ROOT/AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh"
INSTALL_DIR="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}/xuunity-light-unity-mcp"
SERVER_PATH="${XUUNITY_LIGHT_UNITY_MCP_SERVER:-$INSTALL_DIR/server.py}"

if [[ -x "$HOST_WRAPPER_PATH" ]]; then
  exec "$HOST_WRAPPER_PATH" "$@"
fi

if [[ ! -f "$SERVER_PATH" ]]; then
  echo "xuunity-light-unity-mcp server not found: $SERVER_PATH" >&2
  echo "Install it with AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh" >&2
  exit 1
fi

exec python3 "$SERVER_PATH" "$@"
