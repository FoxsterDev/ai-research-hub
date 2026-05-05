#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
ACCEPTANCE_SCENARIO=""
CONTRACT_SCENARIO=""
COMPILE_MODE="build-config-matrix"
RESTORE_EDITOR_STATE="true"
OPEN_EDITOR="true"

usage() {
  cat <<'EOF'
Usage:
  run_smoke_suite.sh \
    --project-root /path/to/UnityProject \
    --acceptance-scenario /path/to/acceptance.json \
    --contract-scenario /path/to/contract.json \
    [--compile-mode build-config-matrix|none] \
    [--no-open-editor] \
    [--no-restore-editor-state]
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
    --acceptance-scenario)
      shift
      [[ $# -gt 0 ]] || fail_usage "--acceptance-scenario requires a value"
      ACCEPTANCE_SCENARIO="$1"
      ;;
    --contract-scenario)
      shift
      [[ $# -gt 0 ]] || fail_usage "--contract-scenario requires a value"
      CONTRACT_SCENARIO="$1"
      ;;
    --compile-mode)
      shift
      [[ $# -gt 0 ]] || fail_usage "--compile-mode requires a value"
      COMPILE_MODE="$1"
      ;;
    --no-open-editor)
      OPEN_EDITOR="false"
      ;;
    --no-restore-editor-state)
      RESTORE_EDITOR_STATE="false"
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
[[ -n "$ACCEPTANCE_SCENARIO" ]] || fail_usage "missing required argument: --acceptance-scenario"
[[ -n "$CONTRACT_SCENARIO" ]] || fail_usage "missing required argument: --contract-scenario"

case "$COMPILE_MODE" in
  build-config-matrix|none)
    ;;
  *)
    fail_usage "unsupported --compile-mode value: $COMPILE_MODE"
    ;;
esac

cleanup() {
  if [[ "$RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 30000 >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "[mcp-smoke] project_root=$PROJECT_ROOT"

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 180000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi

"${ensure_ready_cmd[@]}"

"$WRAPPER" request-status \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000

"$WRAPPER" request-health-probe \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000

"$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$ACCEPTANCE_SCENARIO" \
  --timeout-ms 120000 \
  --poll-interval-ms 500

"$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$CONTRACT_SCENARIO" \
  --timeout-ms 90000 \
  --poll-interval-ms 500

if [[ "$COMPILE_MODE" == "build-config-matrix" ]]; then
  "$WRAPPER" request-build-config-compile-matrix \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 300000
fi

echo "[mcp-smoke] suite passed"
