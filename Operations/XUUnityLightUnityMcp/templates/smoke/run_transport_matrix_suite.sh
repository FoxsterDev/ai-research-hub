#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
ACCEPTANCE_SCENARIO=""
CONTRACT_SCENARIO=""
COMPILE_MODE="none"
PLAYMODE_REGRESSION_ASSEMBLY_NAME=""
PLAYMODE_REGRESSION_TEST_NAME=""
PROBE_RELATIVE_PATH="Assets/Editor/XUUnityLightMcpTransportMatrixProbe.cs"
TMP_DIR="$(mktemp -d)"
LAST_OUTPUT_FILE=""
CONFIG_PATH=""
PROBE_PATH=""
ORIGINAL_CONFIG_FILE="$TMP_DIR/original_bridge_config.json"
DEFAULT_TRANSPORTS=("file_ipc" "tcp_loopback")

usage() {
  cat <<'EOF'
Usage:
  run_transport_matrix_suite.sh \
    --project-root /path/to/UnityProject \
    --acceptance-scenario /path/to/acceptance.json \
    --contract-scenario /path/to/contract.json \
    [--compile-mode build-config-matrix|none] \
    [--playmode-regression-assembly-name PlayMode.Tests] \
    [--playmode-regression-test-name MyPlayModeTest] \
    [--probe-relative-path Assets/Editor/XUUnityLightMcpTransportMatrixProbe.cs] \
    [--transports file_ipc,tcp_loopback]
EOF
}

fail_usage() {
  echo "$1" >&2
  usage >&2
  exit 1
}

TRANSPORTS_CSV=""
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
    --playmode-regression-assembly-name)
      shift
      [[ $# -gt 0 ]] || fail_usage "--playmode-regression-assembly-name requires a value"
      PLAYMODE_REGRESSION_ASSEMBLY_NAME="$1"
      ;;
    --playmode-regression-test-name)
      shift
      [[ $# -gt 0 ]] || fail_usage "--playmode-regression-test-name requires a value"
      PLAYMODE_REGRESSION_TEST_NAME="$1"
      ;;
    --probe-relative-path)
      shift
      [[ $# -gt 0 ]] || fail_usage "--probe-relative-path requires a value"
      PROBE_RELATIVE_PATH="$1"
      ;;
    --transports)
      shift
      [[ $# -gt 0 ]] || fail_usage "--transports requires a value"
      TRANSPORTS_CSV="$1"
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

if [[ -n "$PLAYMODE_REGRESSION_ASSEMBLY_NAME" || -n "$PLAYMODE_REGRESSION_TEST_NAME" ]]; then
  [[ -n "$PLAYMODE_REGRESSION_ASSEMBLY_NAME" ]] || fail_usage "--playmode-regression-test-name requires --playmode-regression-assembly-name"
  [[ -n "$PLAYMODE_REGRESSION_TEST_NAME" ]] || fail_usage "--playmode-regression-assembly-name requires --playmode-regression-test-name"
fi

CONFIG_PATH="$PROJECT_ROOT/Library/XUUnityLightMcp/config/bridge_config.json"
PROBE_PATH="$PROJECT_ROOT/$PROBE_RELATIVE_PATH"
STATE_ROOT="$PROJECT_ROOT/Library/XUUnityLightMcp"
INBOX_DIR="$STATE_ROOT/inbox"

cleanup() {
  if [[ -f "$ORIGINAL_CONFIG_FILE" ]]; then
    cp "$ORIGINAL_CONFIG_FILE" "$CONFIG_PATH"
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

write_transport_config() {
  local transport="$1"
  python3 - "$CONFIG_PATH" "$transport" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
transport = sys.argv[2]
data = json.loads(config_path.read_text()) if config_path.exists() else {}
data["enabled"] = True
data["heartbeat_interval_ms"] = int(data.get("heartbeat_interval_ms") or 2000)
data["pump_interval_ms"] = int(data.get("pump_interval_ms") or 500)
data["transport"] = transport
data["loopback_host"] = "127.0.0.1"
data["loopback_port"] = 0
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n")
PY
}

touch_reload_probe() {
  local transport="$1"
  mkdir -p "$(dirname "$PROBE_PATH")"
  cat > "$PROBE_PATH" <<EOF
namespace XUUnity.LightMcp.Editor.TransportMatrix
{
    internal static class XUUnityLightMcpTransportMatrixProbe
    {
        internal const string Marker = "${transport}_$(date -u +%Y%m%dT%H%M%SZ)";
    }
}
EOF
}

run_raw_file_ipc_refresh() {
  local output_file="$1"

  if ! python3 - "$PROJECT_ROOT" "$INBOX_DIR" "$STATE_ROOT/outbox" "$output_file" <<'PY'; then
import json
import sys
import time
import uuid
from pathlib import Path

project_root = sys.argv[1]
inbox_dir = Path(sys.argv[2])
outbox_dir = Path(sys.argv[3])
output_path = Path(sys.argv[4])
request_timeout_ms = 180000
request_id = str(uuid.uuid4())
request = {
    "request_id": request_id,
    "operation": "unity.project.refresh",
    "project_root": project_root,
    "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "timeout_ms": request_timeout_ms,
    "args_json": json.dumps({
        "forceAssetRefresh": True,
        "resolvePackages": True,
        "rerunHealthProbe": True,
    }, ensure_ascii=True, separators=(",", ":")),
}
inbox_dir.mkdir(parents=True, exist_ok=True)
outbox_dir.mkdir(parents=True, exist_ok=True)
request_path = inbox_dir / f"{request_id}.json"
response_path = outbox_dir / f"{request_id}.json"
request_path.write_text(json.dumps(request, ensure_ascii=True, indent=2) + "\n")
deadline = time.time() + 240
while time.time() < deadline:
    if response_path.exists():
        payload = json.loads(response_path.read_text())
        output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
        try:
            response_path.unlink()
        except OSError:
            pass
        raise SystemExit(0)
    time.sleep(0.5)
raise SystemExit(1)
PY
    return 1
  fi

  return 0
}

editor_process_running() {
  "$WRAPPER" request-status-summary \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 5000 >"$TMP_DIR/status_summary_transport_preflight.json" 2>/dev/null || return 1

  python3 - "$TMP_DIR/status_summary_transport_preflight.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if data.get("editor_running") else 1)
PY
}

ensure_editor_open_for_file_ipc_refresh() {
  local transport="$1"

  if editor_process_running; then
    return 0
  fi

  run_step "${transport}_ensure_ready_preflight" \
    "$WRAPPER" ensure-ready \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 180000 \
    --open-editor
  summarize_json \
    "${transport}-ensure-ready-preflight" \
    "$TMP_DIR/${transport}_ensure_ready_preflight.json" \
    "\"bridge=%s health=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('health_status'))"
}

run_transport_cycle() {
  local transport="$1"

  echo "[transport] switching to $transport"
  write_transport_config "$transport"
  touch_reload_probe "$transport"

  if [[ "$transport" == "file_ipc" ]]; then
    ensure_editor_open_for_file_ipc_refresh "$transport"
    LAST_OUTPUT_FILE="$TMP_DIR/${transport}_refresh.json"
    if ! run_raw_file_ipc_refresh "$LAST_OUTPUT_FILE"; then
      fail_step "${transport}_refresh"
    fi
  else
    run_step "${transport}_refresh" \
      "$WRAPPER" request-project-refresh \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 180000
  fi
  summarize_json \
    "${transport}-refresh" \
    "$TMP_DIR/${transport}_refresh.json" \
    "\"outcome=%s basis=%s\" % ((lambda payload: (payload.get('outcome'), payload.get('completion_basis')))(__import__('json').loads(data['payload_json'])))"

  run_step "${transport}_ensure_ready" \
    "$WRAPPER" ensure-ready \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 180000
  summarize_json \
    "${transport}-ensure-ready" \
    "$TMP_DIR/${transport}_ensure_ready.json" \
    "\"bridge=%s health=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('health_status'))"

  run_step "${transport}_status" \
    "$WRAPPER" request-status \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms 15000
  summarize_json \
    "${transport}-status" \
    "$TMP_DIR/${transport}_status.json" \
    "\"requested=%s active=%s listener=%s\" % ((lambda payload: (payload.get('transport_requested'), payload.get('transport'), payload.get('transport_listener_state')))(__import__('json').loads(data['payload_json'])))"

  post_change_cmd=(
    "$SCRIPT_DIR/run_post_change_validation.sh"
    --project-root "$PROJECT_ROOT"
    --acceptance-scenario "$ACCEPTANCE_SCENARIO"
    --contract-scenario "$CONTRACT_SCENARIO"
    --compile-mode "$COMPILE_MODE"
    --no-restore-editor-state
  )
  if [[ -n "$PLAYMODE_REGRESSION_ASSEMBLY_NAME" ]]; then
    post_change_cmd+=(
      --playmode-regression-assembly-name "$PLAYMODE_REGRESSION_ASSEMBLY_NAME"
      --playmode-regression-test-name "$PLAYMODE_REGRESSION_TEST_NAME"
    )
  fi

  run_step "${transport}_post_change" "${post_change_cmd[@]}"
  cp "$TMP_DIR/${transport}_post_change.json" "$TMP_DIR/${transport}_post_change.stdout"
  echo "[pass] ${transport}-post-change runner=run_post_change_validation.sh"
}

echo "[mcp-transport-matrix] project_root=$PROJECT_ROOT"

mkdir -p "$(dirname "$CONFIG_PATH")"
if [[ -f "$CONFIG_PATH" ]]; then
  cp "$CONFIG_PATH" "$ORIGINAL_CONFIG_FILE"
fi

transports=("${DEFAULT_TRANSPORTS[@]}")
if [[ -n "$TRANSPORTS_CSV" ]]; then
  IFS=',' read -r -a transports <<< "$TRANSPORTS_CSV"
fi

for transport in "${transports[@]}"; do
  case "$transport" in
    file_ipc|tcp_loopback)
      ;;
    *)
      echo "[fail] unsupported transport in matrix: $transport"
      exit 1
      ;;
  esac
  run_transport_cycle "$transport"
done

run_step final_status \
  "$WRAPPER" request-status \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "final-status" \
  "$TMP_DIR/final_status.json" \
  "\"transport=%s health=%s playmode=%s\" % ((lambda payload: (payload.get('transport'), payload.get('health_status'), payload.get('playmode_state')))(__import__('json').loads(data['payload_json'])))"

echo "[pass] transport-matrix overall"
