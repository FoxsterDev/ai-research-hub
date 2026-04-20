#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash AIRoot/Operations/CodexMdToHtml/render_md_to_html.sh <input.md> [output.html]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_HOME="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
INSTALL_ROOT="${CODEX_MD_TO_HTML_INSTALL_ROOT:-$TOOLS_HOME/md-to-html-cli}"
INPUT_MD_DIR="$(cd "$(dirname "$1")" && pwd)"
INPUT_MD="$INPUT_MD_DIR/$(basename "$1")"

if [[ ! -f "$INPUT_MD" ]]; then
  echo "Input markdown file not found: $INPUT_MD" >&2
  exit 1
fi

INPUT_DIR="$(dirname "$INPUT_MD")"
INPUT_BASENAME="$(basename "$INPUT_MD" .md)"
DEFAULT_OUTPUT="$INPUT_DIR/$INPUT_BASENAME.html"
OUTPUT_HTML="${2:-$DEFAULT_OUTPUT}"

if [[ ! -d "$INSTALL_ROOT/node_modules/marked" || ! -d "$INSTALL_ROOT/node_modules/mermaid" ]]; then
  echo "Dependencies are missing. Run: bash AIRoot/Operations/CodexMdToHtml/init_codex_md_to_html.sh" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_HTML")"

node "$SCRIPT_DIR/templates/render_md_to_html.mjs" \
  "$INSTALL_ROOT" \
  "$SCRIPT_DIR/templates/default.css" \
  "$INPUT_MD" \
  "$OUTPUT_HTML"

echo "Generated HTML: $OUTPUT_HTML"
