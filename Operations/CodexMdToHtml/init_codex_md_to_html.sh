#!/usr/bin/env bash
set -euo pipefail

TOOLS_HOME="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
INSTALL_ROOT="$TOOLS_HOME/md-to-html-cli"
MARKED_VERSION="16.4.1"
MERMAID_VERSION="11.12.1"

mkdir -p "$INSTALL_ROOT"

npm install --prefix "$INSTALL_ROOT" \
  "marked@$MARKED_VERSION" \
  "mermaid@$MERMAID_VERSION"

echo "CodexMdToHtml dependencies are installed in: $INSTALL_ROOT"
