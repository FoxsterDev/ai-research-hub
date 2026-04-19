#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash AIRoot/Operations/CodexMdToPdf/render_md_to_pdf.sh <input.md> [output.pdf]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_HOME="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
MD_TO_PDF_BIN="${CODEX_MD_TO_PDF_BIN:-$TOOLS_HOME/md-to-pdf-cli/node_modules/.bin/md-to-pdf}"
INPUT_MD_DIR="$(cd "$(dirname "$1")" && pwd)"
INPUT_MD="$INPUT_MD_DIR/$(basename "$1")"

if [[ ! -f "$INPUT_MD" ]]; then
  echo "Input markdown file not found: $INPUT_MD" >&2
  exit 1
fi

INPUT_DIR="$(dirname "$INPUT_MD")"
INPUT_BASENAME="$(basename "$INPUT_MD" .md)"
DEFAULT_OUTPUT="$INPUT_DIR/$INPUT_BASENAME.pdf"
OUTPUT_PDF="${2:-$DEFAULT_OUTPUT}"

if [[ ! -x "$MD_TO_PDF_BIN" ]]; then
  echo "Dependencies are missing. Run: bash AIRoot/Operations/CodexMdToPdf/init_codex_md_to_pdf.sh" >&2
  exit 1
fi

"$MD_TO_PDF_BIN" \
  "$INPUT_MD" \
  --basedir "$INPUT_DIR" \
  --config-file "$SCRIPT_DIR/templates/md-to-pdf.config.js" \
  --stylesheet "$SCRIPT_DIR/templates/default.css"

if [[ "$OUTPUT_PDF" != "$DEFAULT_OUTPUT" ]]; then
  mkdir -p "$(dirname "$OUTPUT_PDF")"
  mv "$DEFAULT_OUTPUT" "$OUTPUT_PDF"
fi

echo "Generated PDF: $OUTPUT_PDF"
