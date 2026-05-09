#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
CONTRACT_SCENARIO=""
FRONTMOST_APP=""
RESTORE_EDITOR_STATE="true"
OPEN_EDITOR="true"
TMP_DIR="$(mktemp -d)"
LAST_OUTPUT_FILE=""
STRESS_SCENARIO_FILE=""
INITIAL_EDITOR_RUNNING="unknown"
SHOULD_RESTORE_EDITOR_STATE="false"

usage() {
  cat <<'EOF'
Usage:
  run_lifecycle_stress_suite.sh \
    --project-root /path/to/UnityProject \
    --contract-scenario /path/to/contract.json \
    [--frontmost-app Finder] \
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
    --contract-scenario)
      shift
      [[ $# -gt 0 ]] || fail_usage "--contract-scenario requires a value"
      CONTRACT_SCENARIO="$1"
      ;;
    --frontmost-app)
      shift
      [[ $# -gt 0 ]] || fail_usage "--frontmost-app requires a value"
      FRONTMOST_APP="$1"
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
[[ -n "$CONTRACT_SCENARIO" ]] || fail_usage "missing required argument: --contract-scenario"

cleanup() {
  if [[ "$SHOULD_RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 30000 >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

capture_initial_editor_state() {
  local status_file="$TMP_DIR/initial_status_summary.json"
  if "$WRAPPER" request-status-summary --project-root "$PROJECT_ROOT" > "$status_file" 2>/dev/null; then
    INITIAL_EDITOR_RUNNING="$(python3 - "$status_file" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
print("true" if bool(data.get("editor_running")) else "false")
PY
)"
  fi

  if [[ "$RESTORE_EDITOR_STATE" == "true" && "$OPEN_EDITOR" == "true" && "$INITIAL_EDITOR_RUNNING" == "false" ]]; then
    SHOULD_RESTORE_EDITOR_STATE="true"
  fi
}

capture_initial_editor_state

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

prepare_stress_scenario() {
  STRESS_SCENARIO_FILE="$TMP_DIR/lifecycle_stress_contract.json"
  python3 - "$CONTRACT_SCENARIO" "$STRESS_SCENARIO_FILE" <<'PY'
import json
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
data = json.loads(source_path.read_text())

for step in data.get("steps") or []:
    if step.get("kind") == "project_refresh":
        timeout_seconds = float(step.get("timeoutSeconds") or 0.0)
        step["timeoutSeconds"] = max(timeout_seconds, 90.0)

target_path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n")
PY
}

activate_app() {
  local app_name="$1"
  if [[ -z "$app_name" ]]; then
    return 0
  fi
  if [[ "$(uname -s)" != "Darwin" ]] || ! command -v osascript >/dev/null 2>&1; then
    return 0
  fi
  osascript -e "tell application \"$app_name\" to activate" >/dev/null
  sleep 1
}

echo "[mcp-stress] project_root=$PROJECT_ROOT"
prepare_stress_scenario

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
  "\"bridge=%s health=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('health_status'))"

activate_app "$FRONTMOST_APP"

run_step background_status \
  "$WRAPPER" request-status \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "background-status" \
  "$TMP_DIR/background_status.json" \
  "\"health=%s playmode=%s\" % ((lambda payload: (payload.get('health_status'), payload.get('playmode_state')))(__import__('json').loads(data['payload_json'])))"

activate_app "$FRONTMOST_APP"

run_step background_refresh \
  "$WRAPPER" request-project-refresh \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 45000
summarize_json \
  "background-refresh" \
  "$TMP_DIR/background_refresh.json" \
  "\"outcome=%s basis=%s\" % ((lambda payload: (payload.get('outcome'), payload.get('completion_basis')))(__import__('json').loads(data['payload_json'])))"

activate_app "$FRONTMOST_APP"

run_step background_contract_scenario \
  "$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$STRESS_SCENARIO_FILE" \
  --timeout-ms 180000 \
  --poll-interval-ms 500
summarize_json \
  "background-contract-scenario" \
  "$TMP_DIR/background_contract_scenario.json" \
  "\"status=%s refresh=%s\" % ((data.get('status') or data.get('terminal_status') or ((data.get('run_start') or {}).get('status'))), next((__import__('json').loads(step.get('payload_json') or '{}').get('outcome') for step in ((data.get('steps') or ((data.get('run_start') or {}).get('steps')) or [])) if step.get('stepId') == 'refresh'), 'unknown'))"

activate_app "$FRONTMOST_APP"

run_step background_playmode_enter \
  "$WRAPPER" request-playmode-set \
  --project-root "$PROJECT_ROOT" \
  --action enter \
  --timeout-ms 90000
summarize_json \
  "background-playmode-enter" \
  "$TMP_DIR/background_playmode_enter.json" \
  "\"state=%s basis=%s\" % ((lambda payload: (payload.get('playmode_state'), payload.get('completion_basis')))(__import__('json').loads(data['payload_json'])))"

activate_app "$FRONTMOST_APP"

run_step background_playmode_exit \
  "$WRAPPER" request-playmode-set \
  --project-root "$PROJECT_ROOT" \
  --action exit \
  --timeout-ms 90000
summarize_json \
  "background-playmode-exit" \
  "$TMP_DIR/background_playmode_exit.json" \
  "\"state=%s basis=%s\" % ((lambda payload: (payload.get('playmode_state'), payload.get('completion_basis')))(__import__('json').loads(data['payload_json'])))"

run_step reconnect_ensure_ready \
  "$WRAPPER" ensure-ready \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 60000
summarize_json \
  "reconnect-ensure-ready" \
  "$TMP_DIR/reconnect_ensure_ready.json" \
  "\"bridge=%s last_processed=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('last_processed_request_id'))"

run_step final_status \
  "$WRAPPER" request-status \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "final-status" \
  "$TMP_DIR/final_status.json" \
  "\"health=%s playmode=%s last_completed=%s/%s\" % ((lambda payload: (payload.get('health_status'), payload.get('playmode_state'), payload.get('last_completed_operation'), payload.get('last_completed_operation_status')))(__import__('json').loads(data['payload_json'])))"

echo "[pass] lifecycle-stress overall"
