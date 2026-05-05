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
TMP_DIR=""
LAST_OUTPUT_FILE=""

usage() {
  cat <<'EOF'
Usage:
  run_post_change_validation.sh \
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

TMP_DIR="$(mktemp -d)"

cleanup() {
  if [[ "$RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 30000 >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail_step() {
  local step_name="$1"
  echo "[fail] $step_name"
  if [[ -n "$LAST_OUTPUT_FILE" && -f "$LAST_OUTPUT_FILE" ]]; then
    echo "[fail] output follows:"
    cat "$LAST_OUTPUT_FILE"
  fi
  exit 1
}

run_step() {
  local step_name="$1"
  shift
  LAST_OUTPUT_FILE="$TMP_DIR/${step_name}.json"
  if ! "$@" > "$LAST_OUTPUT_FILE"; then
    fail_step "$step_name"
  fi
}

summarize_json() {
  local label="$1"
  local file_path="$2"
  local python_code="$3"

  if ! python3 - "$label" "$file_path" "$python_code" <<'PY'; then
import json
import sys
from pathlib import Path

label = sys.argv[1]
file_path = Path(sys.argv[2])
python_code = sys.argv[3]

data = json.loads(file_path.read_text())
namespace = {"data": data}
summary = eval(python_code, {}, namespace)
print(f"[pass] {label} {summary}".rstrip())
PY
    fail_step "$label"
  fi
}

echo "[mcp-validate] project_root=$PROJECT_ROOT"

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 180000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi

run_step ensure_ready "${ensure_ready_cmd[@]}"
summarize_json \
  "ensure-ready" \
  "$TMP_DIR/ensure_ready.json" \
  "\"bridge=%s health=%s playmode=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('health_status'), data['bridge_state'].get('playmode_state'))"

run_step status \
  "$WRAPPER" request-status \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "status" \
  "$TMP_DIR/status.json" \
  "\"health=%s playmode=%s last_completed=%s/%s\" % ((lambda payload: (payload.get('health_status'), payload.get('playmode_state'), payload.get('last_completed_operation'), payload.get('last_completed_operation_status')))(__import__('json').loads(data['payload_json'])))"

run_step health_probe \
  "$WRAPPER" request-health-probe \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "health-probe" \
  "$TMP_DIR/health_probe.json" \
  "\"status=%s supported_ops=%s\" % ((lambda report: (report.get('status'), len(report.get('supported_operations') or [])))(__import__('json').loads(data['payload_json']).get('report') or {}))"

run_step acceptance_scenario \
  "$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$ACCEPTANCE_SCENARIO" \
  --timeout-ms 120000 \
  --poll-interval-ms 500
summarize_json \
  "acceptance-scenario" \
  "$TMP_DIR/acceptance_scenario.json" \
  "\"status=%s steps=%s/%s duration=%.3fs\" % ((lambda payload, steps: (payload.get('status') or payload.get('terminal_status') or ((payload.get('run_start') or {}).get('status')), payload.get('passed_steps') if payload.get('passed_steps') is not None else sum(1 for step in steps if step.get('status') == 'passed'), payload.get('total_steps') if payload.get('total_steps') is not None else len(steps), float(payload.get('duration_seconds') or 0.0)))(data, (data.get('steps') or ((data.get('run_start') or {}).get('steps')) or [])))"

run_step contract_scenario \
  "$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$CONTRACT_SCENARIO" \
  --timeout-ms 90000 \
  --poll-interval-ms 500
summarize_json \
  "contract-scenario" \
  "$TMP_DIR/contract_scenario.json" \
  "\"status=%s refresh=%s compile=%s duration=%.3fs\" % ((data.get('status') or data.get('terminal_status') or ((data.get('run_start') or {}).get('status'))), next((__import__('json').loads(step.get('payload_json') or '{}').get('outcome') for step in ((data.get('steps') or ((data.get('run_start') or {}).get('steps')) or [])) if step.get('stepId') == 'refresh'), 'unknown'), next((__import__('json').loads(step.get('payload_json') or '{}').get('completion_basis') for step in ((data.get('steps') or ((data.get('run_start') or {}).get('steps')) or [])) if step.get('stepId') == 'compile'), 'unknown'), float(data.get('duration_seconds') or 0.0))"

if [[ "$COMPILE_MODE" == "build-config-matrix" ]]; then
  run_step compile_matrix \
    "$WRAPPER" request-build-config-compile-matrix \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 300000
  summarize_json \
    "compile-matrix" \
    "$TMP_DIR/compile_matrix.json" \
    "\"status=%s passed=%s/%s basis=%s duration=%.3fs\" % ((lambda matrix: (matrix.get('status'), matrix.get('passed'), matrix.get('total'), matrix.get('completion_basis'), float(matrix.get('duration_seconds') or 0.0)))(__import__('json').loads(data['bridge_response']['payload_json'])))"
else
  echo "[skip] compile-matrix compile_mode=none"
fi

echo "[pass] suite overall"
