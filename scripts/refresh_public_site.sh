#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIR_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RENDER_SCRIPT="$AIR_ROOT/Operations/CodexMdToHtml/render_md_to_html.sh"
DOCS_DIR="$AIR_ROOT/docs"
ASSETS_DIR="$DOCS_DIR/assets"

if [[ ! -x "$RENDER_SCRIPT" && ! -f "$RENDER_SCRIPT" ]]; then
  echo "Render script not found: $RENDER_SCRIPT" >&2
  exit 1
fi

if [[ ! -d "${HOME}/.codex-tools/md-to-html-cli/node_modules/marked" ]]; then
  echo "Markdown HTML renderer dependencies are missing." >&2
  echo "Run: bash AIRoot/Operations/CodexMdToHtml/init_codex_md_to_html.sh" >&2
  exit 1
fi

mkdir -p "$DOCS_DIR" "$ASSETS_DIR"

render_page() {
  local input_rel="$1"
  local output_rel="$2"
  bash "$RENDER_SCRIPT" "$AIR_ROOT/$input_rel" "$AIR_ROOT/$output_rel"
}

echo "Refreshing derived public pages..."
render_page "Visuals/AI_PROTOCOL_VISUAL_MAP.md" "docs/visual-map.html"
render_page "Operations/AI_PROTOCOL_HANDBOOK.md" "docs/handbook.html"
render_page "Operations/SETUP_INDEX.md" "docs/setup-index.html"
render_page "INTEGRATION.md" "docs/integration.html"
render_page "Operations/AI_PRODUCT_OWNER_QUICKSTART.md" "docs/product-owner-quickstart.html"

if command -v sips >/dev/null 2>&1; then
  SOCIAL_SVG="$ASSETS_DIR/airroot-social-card.svg"
  SOCIAL_PNG="$ASSETS_DIR/airroot-social-card.png"
  SOCIAL_JPG="$ASSETS_DIR/airroot-social-card.jpg"

  if [[ -f "$SOCIAL_SVG" ]]; then
    echo "Refreshing social preview assets..."
    sips -s format png "$SOCIAL_SVG" --out "$SOCIAL_PNG" >/dev/null
    sips -s format jpeg "$SOCIAL_PNG" --out "$SOCIAL_JPG" >/dev/null
  fi
fi

echo
echo "Public site refresh complete."
echo "Updated docs pages:"
echo "  - docs/visual-map.html"
echo "  - docs/handbook.html"
echo "  - docs/setup-index.html"
echo "  - docs/integration.html"
echo "  - docs/product-owner-quickstart.html"
echo
echo "If the social card SVG changed, refreshed assets are:"
echo "  - docs/assets/airroot-social-card.png"
echo "  - docs/assets/airroot-social-card.jpg"
