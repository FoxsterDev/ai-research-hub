#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_HOME="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
INSTALL_ROOT="$TOOLS_HOME/md-to-pdf-cli"
PACKAGE_VERSION="5.2.5"

mkdir -p "$INSTALL_ROOT"

npm install --prefix "$INSTALL_ROOT" "md-to-pdf@$PACKAGE_VERSION"

echo "CodexMdToPdf dependencies are installed in: $INSTALL_ROOT"
