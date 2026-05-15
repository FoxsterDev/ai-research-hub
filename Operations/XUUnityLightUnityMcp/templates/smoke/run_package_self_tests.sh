#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
OPEN_EDITOR="true"
RUN_MODE="all"
TIMEOUT_MS="240000"
TMP_DIR=""
MANIFEST_BACKUP=""
MANIFEST_WAS_PATCHED="false"

usage() {
  cat <<'EOF'
Usage:
  run_package_self_tests.sh \
    --project-root /path/to/UnityProject \
    [--mode all|editmode|playmode|fast|scene|lifecycle] \
    [--timeout-ms 240000] \
    [--no-open-editor]

Runs the public XUUnity Light MCP package self-tests shipped inside
com.xuunity.light-mcp. These tests are intended to work in an otherwise empty
Unity project after the package is installed.

Unity discovers package test assemblies only when the package name is listed in
the consumer project's Packages/manifest.json testables array. This runner adds
com.xuunity.light-mcp to testables temporarily, refreshes the project, runs the
selected tests, and restores the original manifest on exit.
EOF
}

fail_usage() {
  echo "$1" >&2
  usage >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-root requires a value"
      PROJECT_ROOT="$1"
      ;;
    --mode)
      shift
      [[ $# -gt 0 ]] || fail_usage "--mode requires a value"
      RUN_MODE="$1"
      ;;
    --timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--timeout-ms requires a value"
      TIMEOUT_MS="$1"
      ;;
    --no-open-editor)
      OPEN_EDITOR="false"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail_usage "Unknown argument: $1"
      ;;
  esac
  shift
done

[[ -n "$PROJECT_ROOT" ]] || fail_usage "missing required argument: --project-root"
TMP_DIR="$(mktemp -d)"
MANIFEST_PATH="$PROJECT_ROOT/Packages/manifest.json"
MANIFEST_BACKUP="$TMP_DIR/manifest.json"

cleanup() {
  if [[ "$MANIFEST_WAS_PATCHED" == "true" && -f "$MANIFEST_BACKUP" ]]; then
    cp "$MANIFEST_BACKUP" "$MANIFEST_PATH"
    "$WRAPPER" request-project-refresh --project-root "$PROJECT_ROOT" --timeout-ms 180000 >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

enable_package_tests() {
  [[ -f "$MANIFEST_PATH" ]] || fail_usage "Unity project manifest not found: $MANIFEST_PATH"
  cp "$MANIFEST_PATH" "$MANIFEST_BACKUP"
  python3 - "$MANIFEST_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
testables = data.get("testables")
if not isinstance(testables, list):
    testables = []
if "com.xuunity.light-mcp" not in testables:
    testables.append("com.xuunity.light-mcp")
    data["testables"] = testables
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("patched")
else:
    print("already_enabled")
PY
}

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 180000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi

"${ensure_ready_cmd[@]}" >/dev/null
PATCH_RESULT="$(enable_package_tests)"
if [[ "$PATCH_RESULT" == "patched" ]]; then
  MANIFEST_WAS_PATCHED="true"
fi
"$WRAPPER" request-project-refresh --project-root "$PROJECT_ROOT" --timeout-ms 180000 >/dev/null

run_editmode() {
  local category="$1"
  "$WRAPPER" request-editmode-tests \
    --project-root "$PROJECT_ROOT" \
    --assembly-name com.xuunity.light-mcp.Editor.Tests \
    --category-name "$category" \
    --timeout-ms "$TIMEOUT_MS"
}

run_playmode() {
  local category="$1"
  "$WRAPPER" request-playmode-tests \
    --project-root "$PROJECT_ROOT" \
    --assembly-name com.xuunity.light-mcp.PlayMode.Tests \
    --category-name "$category" \
    --timeout-ms "$TIMEOUT_MS"
}

case "$RUN_MODE" in
  all)
    run_editmode XUUnity.MCP.SelfTest
    run_playmode XUUnity.MCP.SelfTest
    ;;
  editmode)
    run_editmode XUUnity.MCP.EditMode
    ;;
  playmode)
    run_playmode XUUnity.MCP.PlayMode
    ;;
  fast)
    run_editmode XUUnity.MCP.Fast
    run_playmode XUUnity.MCP.Fast
    ;;
  scene)
    run_editmode XUUnity.MCP.Scene
    run_playmode XUUnity.MCP.Scene
    ;;
  lifecycle)
    run_playmode XUUnity.MCP.Lifecycle
    ;;
  *)
    fail_usage "Unsupported --mode: $RUN_MODE"
    ;;
esac
