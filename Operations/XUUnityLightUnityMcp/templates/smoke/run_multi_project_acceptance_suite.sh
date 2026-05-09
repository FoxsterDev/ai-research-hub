#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_A_ROOT=""
PROJECT_B_ROOT=""
PROJECT_A_TRANSPORT="tcp_loopback"
PROJECT_B_TRANSPORT="file_ipc"
TIMEOUT_MS="180000"
TMP_DIR="$(mktemp -d)"

usage() {
  cat <<'EOF'
Usage:
  run_multi_project_acceptance_suite.sh \
    --project-a-root /path/to/ProjectA \
    --project-b-root /path/to/ProjectB \
    [--project-a-transport tcp_loopback] \
    [--project-b-transport file_ipc] \
    [--timeout-ms 180000]
EOF
}

fail_usage() {
  echo "$1" >&2
  usage >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-a-root)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-a-root requires a value"
      PROJECT_A_ROOT="$1"
      ;;
    --project-b-root)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-b-root requires a value"
      PROJECT_B_ROOT="$1"
      ;;
    --project-a-transport)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-a-transport requires a value"
      PROJECT_A_TRANSPORT="$1"
      ;;
    --project-b-transport)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-b-transport requires a value"
      PROJECT_B_TRANSPORT="$1"
      ;;
    --timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--timeout-ms requires a value"
      TIMEOUT_MS="$1"
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

[[ -n "$PROJECT_A_ROOT" ]] || fail_usage "missing required argument: --project-a-root"
[[ -n "$PROJECT_B_ROOT" ]] || fail_usage "missing required argument: --project-b-root"
[[ "$PROJECT_A_ROOT" != "$PROJECT_B_ROOT" ]] || fail_usage "project roots must be different"

case "$PROJECT_A_TRANSPORT" in
  file_ipc|tcp_loopback) ;;
  *) fail_usage "unsupported project A transport: $PROJECT_A_TRANSPORT" ;;
esac

case "$PROJECT_B_TRANSPORT" in
  file_ipc|tcp_loopback) ;;
  *) fail_usage "unsupported project B transport: $PROJECT_B_TRANSPORT" ;;
esac

PROJECT_A_NAME="$(basename "$PROJECT_A_ROOT")"
PROJECT_B_NAME="$(basename "$PROJECT_B_ROOT")"

PROJECT_A_CONFIG="$PROJECT_A_ROOT/Library/XUUnityLightMcp/config/bridge_config.json"
PROJECT_B_CONFIG="$PROJECT_B_ROOT/Library/XUUnityLightMcp/config/bridge_config.json"
PROJECT_A_CONFIG_BACKUP="$TMP_DIR/project_a_bridge_config.json"
PROJECT_B_CONFIG_BACKUP="$TMP_DIR/project_b_bridge_config.json"
PROJECT_A_CONFIG_MISSING="$TMP_DIR/project_a_bridge_config.missing"
PROJECT_B_CONFIG_MISSING="$TMP_DIR/project_b_bridge_config.missing"

backup_config() {
  local config_path="$1"
  local backup_path="$2"
  local missing_marker="$3"

  mkdir -p "$(dirname "$config_path")"
  if [[ -f "$config_path" ]]; then
    cp "$config_path" "$backup_path"
  else
    : > "$missing_marker"
  fi
}

restore_config() {
  local config_path="$1"
  local backup_path="$2"
  local missing_marker="$3"

  if [[ -f "$backup_path" ]]; then
    cp "$backup_path" "$config_path"
  elif [[ -f "$missing_marker" ]]; then
    rm -f "$config_path"
  fi
}

cleanup() {
  "$WRAPPER" restore-editor-state --project-root "$PROJECT_A_ROOT" --timeout-ms 30000 >/dev/null 2>&1 || true
  "$WRAPPER" restore-editor-state --project-root "$PROJECT_B_ROOT" --timeout-ms 30000 >/dev/null 2>&1 || true
  restore_config "$PROJECT_A_CONFIG" "$PROJECT_A_CONFIG_BACKUP" "$PROJECT_A_CONFIG_MISSING"
  restore_config "$PROJECT_B_CONFIG" "$PROJECT_B_CONFIG_BACKUP" "$PROJECT_B_CONFIG_MISSING"
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

backup_config "$PROJECT_A_CONFIG" "$PROJECT_A_CONFIG_BACKUP" "$PROJECT_A_CONFIG_MISSING"
backup_config "$PROJECT_B_CONFIG" "$PROJECT_B_CONFIG_BACKUP" "$PROJECT_B_CONFIG_MISSING"

write_transport_config() {
  local config_path="$1"
  local transport="$2"

  python3 - "$config_path" "$transport" <<'PY'
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

run_json() {
  local output_file="$1"
  shift
  "$@" > "$output_file"
}

status_summary() {
  local project_root="$1"
  local output_file="$2"

  run_json \
    "$output_file" \
    "$WRAPPER" request-status-summary \
    --project-root "$project_root" \
    --timeout-ms 15000
}

status_summary_or_failure() {
  local project_root="$1"
  local output_file="$2"

  "$WRAPPER" request-status-summary \
    --project-root "$project_root" \
    --timeout-ms 15000 >"$output_file" 2>&1
}

summarize_status() {
  local label="$1"
  local file_path="$2"

  python3 - "$label" "$file_path" <<'PY'
import json
import sys

label = sys.argv[1]
data = json.load(open(sys.argv[2], encoding="utf-8"))
print(
    "[pass] %s health=%s transport=%s editor=%s reachable=%s" % (
        label,
        data.get("health_status"),
        data.get("transport"),
        data.get("editor_running"),
        data.get("mcp_reachable"),
    )
)
PY
}

assert_healthy_status() {
  local file_path="$1"
  local expected_transport="$2"

  python3 - "$file_path" "$expected_transport" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
expected_transport = sys.argv[2]
ready = (
    bool(data.get("editor_running")) and
    bool(data.get("mcp_reachable")) and
    data.get("health_status") == "healthy" and
    data.get("transport") == expected_transport and
    int(data.get("pending_request_count") or 0) == 0 and
    data.get("playmode_state") == "edit"
)
sys.exit(0 if ready else 1)
PY
}

assert_offline_or_unreachable_status() {
  local file_path="$1"

  python3 - "$file_path" <<'PY'
import json
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text(encoding="utf-8")

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    accepted_failure = (
        "request_failure code=editor_not_running" in raw or
        "stale bridge state" in raw
    )
    sys.exit(0 if accepted_failure else 1)

offline = (
    not bool(data.get("editor_running")) or
    not bool(data.get("mcp_reachable")) or
    data.get("health_status") in {"offline", "stale", "unreachable"}
)
sys.exit(0 if offline else 1)
PY
}

summarize_offline_status() {
  local label="$1"
  local file_path="$2"

  python3 - "$label" "$file_path" <<'PY'
import json
import sys
from pathlib import Path

label = sys.argv[1]
raw = Path(sys.argv[2]).read_text(encoding="utf-8")

try:
    data = json.loads(raw)
except json.JSONDecodeError:
    if "request_failure code=editor_not_running" in raw:
      print("[pass] %s offline_result=editor_not_running" % label)
      raise SystemExit(0)
    print("[pass] %s offline_result=stale_bridge_state" % label)
    raise SystemExit(0)

print(
    "[pass] %s health=%s transport=%s editor=%s reachable=%s" % (
        label,
        data.get("health_status"),
        data.get("transport"),
        data.get("editor_running"),
        data.get("mcp_reachable"),
    )
)
PY
}

ensure_ready_with_transport() {
  local project_root="$1"
  local transport="$2"
  local label="$3"
  local config_path="$4"
  local ensure_file="$TMP_DIR/${label}_ensure_ready.json"
  local status_file="$TMP_DIR/${label}_status.json"

  write_transport_config "$config_path" "$transport"
  run_json \
    "$ensure_file" \
    "$WRAPPER" ensure-ready \
    --project-root "$project_root" \
    --timeout-ms "$TIMEOUT_MS" \
    --open-editor

  python3 - "$label" "$ensure_file" <<'PY'
import json
import sys

label = sys.argv[1]
data = json.load(open(sys.argv[2], encoding="utf-8"))
print(
    "[pass] %s-ensure-ready bridge=%s health=%s playmode=%s" % (
        label,
        data["bridge_state"].get("bridge_version"),
        data["bridge_state"].get("health_status"),
        data["bridge_state"].get("playmode_state"),
    )
)
PY

  status_summary "$project_root" "$status_file"
  assert_healthy_status "$status_file" "$transport"
  summarize_status "$label-status" "$status_file"
}

summarize_refresh() {
  local label="$1"
  local file_path="$2"

  python3 - "$label" "$file_path" <<'PY'
import json
import sys

label = sys.argv[1]
data = json.load(open(sys.argv[2], encoding="utf-8"))
payload = json.loads(data["payload_json"])
print(
    "[pass] %s outcome=%s basis=%s" % (
        label,
        payload.get("outcome"),
        payload.get("completion_basis"),
    )
)
PY
}

echo "[multi-project-acceptance] project_a=$PROJECT_A_ROOT transport_a=$PROJECT_A_TRANSPORT"
echo "[multi-project-acceptance] project_b=$PROJECT_B_ROOT transport_b=$PROJECT_B_TRANSPORT"

ensure_ready_with_transport "$PROJECT_A_ROOT" "$PROJECT_A_TRANSPORT" "$PROJECT_A_NAME" "$PROJECT_A_CONFIG"
ensure_ready_with_transport "$PROJECT_B_ROOT" "$PROJECT_B_TRANSPORT" "$PROJECT_B_NAME" "$PROJECT_B_CONFIG"

echo "[scenario] MP-1 healthy routing and MP-5 transport-local binding"

PROJECT_A_REFRESH_FILE="$TMP_DIR/${PROJECT_A_NAME}_refresh.json"
PROJECT_B_REFRESH_FILE="$TMP_DIR/${PROJECT_B_NAME}_refresh.json"

echo "[scenario] MP-3 parallel mutation across different projects"
run_json \
  "$PROJECT_A_REFRESH_FILE" \
  "$WRAPPER" request-project-refresh \
  --project-root "$PROJECT_A_ROOT" \
  --timeout-ms "$TIMEOUT_MS" &
PID_A=$!
run_json \
  "$PROJECT_B_REFRESH_FILE" \
  "$WRAPPER" request-project-refresh \
  --project-root "$PROJECT_B_ROOT" \
  --timeout-ms "$TIMEOUT_MS" &
PID_B=$!

wait "$PID_A"
wait "$PID_B"

summarize_refresh "$PROJECT_A_NAME-refresh" "$PROJECT_A_REFRESH_FILE"
summarize_refresh "$PROJECT_B_NAME-refresh" "$PROJECT_B_REFRESH_FILE"

status_summary "$PROJECT_A_ROOT" "$TMP_DIR/${PROJECT_A_NAME}_post_refresh_status.json"
status_summary "$PROJECT_B_ROOT" "$TMP_DIR/${PROJECT_B_NAME}_post_refresh_status.json"
assert_healthy_status "$TMP_DIR/${PROJECT_A_NAME}_post_refresh_status.json" "$PROJECT_A_TRANSPORT"
assert_healthy_status "$TMP_DIR/${PROJECT_B_NAME}_post_refresh_status.json" "$PROJECT_B_TRANSPORT"
summarize_status "$PROJECT_A_NAME-post-refresh-status" "$TMP_DIR/${PROJECT_A_NAME}_post_refresh_status.json"
summarize_status "$PROJECT_B_NAME-post-refresh-status" "$TMP_DIR/${PROJECT_B_NAME}_post_refresh_status.json"

echo "[scenario] MP-4 one stale project, one healthy project"
"$WRAPPER" restore-editor-state --project-root "$PROJECT_A_ROOT" --timeout-ms 30000 >/dev/null
status_summary_or_failure "$PROJECT_A_ROOT" "$TMP_DIR/${PROJECT_A_NAME}_stale_status.json" || true
status_summary "$PROJECT_B_ROOT" "$TMP_DIR/${PROJECT_B_NAME}_healthy_status_after_a_restore.json"
assert_offline_or_unreachable_status "$TMP_DIR/${PROJECT_A_NAME}_stale_status.json"
assert_healthy_status "$TMP_DIR/${PROJECT_B_NAME}_healthy_status_after_a_restore.json" "$PROJECT_B_TRANSPORT"
summarize_offline_status "$PROJECT_A_NAME-stale-status" "$TMP_DIR/${PROJECT_A_NAME}_stale_status.json"
summarize_status "$PROJECT_B_NAME-healthy-status-after-$PROJECT_A_NAME-restore" "$TMP_DIR/${PROJECT_B_NAME}_healthy_status_after_a_restore.json"

echo "[pass] multi-project acceptance overall"
