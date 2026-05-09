#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
TIMEOUT_MS="180000"
TMP_DIR="$(mktemp -d)"
STATE_ROOT=""
HOST_SESSION_PATH=""
BRIDGE_STATE_PATH=""
CONFIG_PATH=""
INITIAL_EDITOR_RUNNING="false"

usage() {
  cat <<'EOF'
Usage:
  run_phase2_divergence_suite.sh \
    --project-root /path/to/UnityProject \
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
    --project-root)
      shift
      [[ $# -gt 0 ]] || fail_usage "--project-root requires a value"
      PROJECT_ROOT="$1"
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

[[ -n "$PROJECT_ROOT" ]] || fail_usage "missing required argument: --project-root"

STATE_ROOT="$PROJECT_ROOT/Library/XUUnityLightMcp"
HOST_SESSION_PATH="$STATE_ROOT/state/host_editor_session.json"
BRIDGE_STATE_PATH="$STATE_ROOT/state/bridge_state.json"
CONFIG_PATH="$STATE_ROOT/config/bridge_config.json"

backup_file() {
  local source_path="$1"
  local backup_name="$2"
  if [[ -f "$source_path" ]]; then
    cp "$source_path" "$TMP_DIR/$backup_name"
  else
    : > "$TMP_DIR/$backup_name.missing"
  fi
}

restore_file() {
  local target_path="$1"
  local backup_name="$2"
  if [[ -f "$TMP_DIR/$backup_name" ]]; then
    mkdir -p "$(dirname "$target_path")"
    cp "$TMP_DIR/$backup_name" "$target_path"
  elif [[ -f "$TMP_DIR/$backup_name.missing" ]]; then
    rm -f "$target_path"
  fi
}

discovery_report() {
  local output_file="$1"
  "$WRAPPER" project-discovery-report --project-root "$PROJECT_ROOT" >"$output_file"
}

status_summary() {
  local output_file="$1"
  "$WRAPPER" request-status-summary --project-root "$PROJECT_ROOT" --timeout-ms 15000 >"$output_file"
}

ensure_ready() {
  "$WRAPPER" ensure-ready --project-root "$PROJECT_ROOT" --open-editor --timeout-ms "$TIMEOUT_MS" >/dev/null
}

live_editor_pids() {
  local input_file="$1"
  python3 - "$input_file" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
print(" ".join(str(pid) for pid in data.get("detected_editor_pids") or []))
PY
}

json_field() {
  local input_file="$1"
  local field_name="$2"
  python3 - "$input_file" "$field_name" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
value = data
for part in sys.argv[2].split("."):
    if isinstance(value, dict):
        value = value.get(part)
    else:
        value = None
        break
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(value)
PY
}

assert_discovery_case() {
  local label="$1"
  local input_file="$2"
  local expected_discovery="$3"
  local expected_reconciliation="$4"

  python3 - "$label" "$input_file" "$expected_discovery" "$expected_reconciliation" <<'PY'
import json
import sys

label, input_file, expected_discovery, expected_reconciliation = sys.argv[1:5]
data = json.load(open(input_file, encoding="utf-8"))
actual_discovery = str(data.get("discovery_classification") or "")
actual_reconciliation = str(data.get("reconciliation_case") or "")
if actual_discovery != expected_discovery or actual_reconciliation != expected_reconciliation:
    raise SystemExit(
        f"{label}: expected ({expected_discovery}, {expected_reconciliation}), "
        f"got ({actual_discovery}, {actual_reconciliation})"
    )
print(
    "[pass] %s discovery=%s reconciliation=%s editors=%s" % (
        label,
        actual_discovery,
        actual_reconciliation,
        data.get("detected_editor_pids") or [],
    )
)
PY
}

mutate_state_files() {
  local mode="$1"
  local live_pid="$2"
  local dead_pid="$3"
  python3 - "$mode" "$PROJECT_ROOT" "$HOST_SESSION_PATH" "$BRIDGE_STATE_PATH" "$CONFIG_PATH" "$live_pid" "$dead_pid" <<'PY'
import json
import sys
from pathlib import Path

mode, project_root, host_session_path, bridge_state_path, config_path, live_pid_raw, dead_pid_raw = sys.argv[1:8]
project_root = str(Path(project_root).expanduser().resolve())
host_session_path = Path(host_session_path)
bridge_state_path = Path(bridge_state_path)
config_path = Path(config_path)
live_pid = int(live_pid_raw)
dead_pid = int(dead_pid_raw)

def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

if mode == "stale_host_session":
    host_session = read_json(host_session_path)
    host_session["project_root"] = project_root
    host_session["editor_pid"] = dead_pid
    host_session["opened_by_host"] = True
    write_json(host_session_path, host_session)
elif mode == "live_process_only":
    host_session = read_json(host_session_path)
    host_session["project_root"] = project_root
    host_session["editor_pid"] = dead_pid
    host_session["opened_by_host"] = True
    write_json(host_session_path, host_session)

    bridge_state = read_json(bridge_state_path)
    bridge_state["project_root"] = project_root
    bridge_state["editor_pid"] = dead_pid
    bridge_state["transport"] = str(bridge_state.get("transport") or "tcp_loopback")
    bridge_state["transport_requested"] = str(bridge_state.get("transport_requested") or bridge_state["transport"])
    write_json(bridge_state_path, bridge_state)
elif mode == "stale_bridge_state":
    host_session = read_json(host_session_path)
    host_session["project_root"] = project_root
    host_session["editor_pid"] = live_pid
    host_session["opened_by_host"] = True
    write_json(host_session_path, host_session)

    bridge_state = read_json(bridge_state_path)
    bridge_state["project_root"] = project_root
    bridge_state["editor_pid"] = dead_pid
    bridge_state["transport"] = str(bridge_state.get("transport") or "tcp_loopback")
    bridge_state["transport_requested"] = str(bridge_state.get("transport_requested") or bridge_state["transport"])
    write_json(bridge_state_path, bridge_state)
elif mode == "bridge_disabled":
    config = read_json(config_path)
    config["enabled"] = False
    write_json(config_path, config)
    if host_session_path.exists():
      host_session_path.unlink()
    if bridge_state_path.exists():
      bridge_state_path.unlink()
else:
    raise SystemExit(f"Unknown mutation mode: {mode}")
PY
}

wait_for_no_editor() {
  local report_file="$1"
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    discovery_report "$report_file"
    if [[ "$(json_field "$report_file" "detected_editor_count")" == "0" ]]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

force_stop_project_editors() {
  local report_file="$1"
  local pids
  pids="$(live_editor_pids "$report_file")"
  [[ -n "$pids" ]] || return 0

  for pid in $pids; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  sleep 2

  discovery_report "$report_file"
  pids="$(live_editor_pids "$report_file")"
  [[ -n "$pids" ]] || return 0
  for pid in $pids; do
    kill -9 "$pid" >/dev/null 2>&1 || true
  done
  sleep 2
}

cleanup() {
  restore_file "$HOST_SESSION_PATH" "host_editor_session.json"
  restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"
  restore_file "$CONFIG_PATH" "bridge_config.json"
  if [[ "$INITIAL_EDITOR_RUNNING" == "true" ]]; then
    "$WRAPPER" ensure-ready --project-root "$PROJECT_ROOT" --open-editor --timeout-ms "$TIMEOUT_MS" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

backup_file "$HOST_SESSION_PATH" "host_editor_session.json"
backup_file "$BRIDGE_STATE_PATH" "bridge_state.json"
backup_file "$CONFIG_PATH" "bridge_config.json"

INITIAL_REPORT="$TMP_DIR/initial_report.json"
discovery_report "$INITIAL_REPORT"
INITIAL_EDITOR_RUNNING="$(json_field "$INITIAL_REPORT" "detected_editor_count")"
if [[ "$INITIAL_EDITOR_RUNNING" != "0" ]]; then
  INITIAL_EDITOR_RUNNING="true"
else
  INITIAL_EDITOR_RUNNING="false"
fi

ensure_ready

BASELINE_REPORT="$TMP_DIR/baseline_report.json"
STATUS_REPORT="$TMP_DIR/status_report.json"
discovery_report "$BASELINE_REPORT"
status_summary "$STATUS_REPORT"
assert_discovery_case "baseline" "$BASELINE_REPORT" "bridge_live" "bridge_state_authoritative"

LIVE_PID="$(json_field "$BASELINE_REPORT" "last_seen_pid")"
if [[ -z "$LIVE_PID" || "$LIVE_PID" == "0" ]]; then
  echo "[fail] baseline did not produce a live editor pid" >&2
  exit 1
fi
DEAD_PID="999999"

STH_REPORT="$TMP_DIR/stale_host_session_report.json"
mutate_state_files "stale_host_session" "$LIVE_PID" "$DEAD_PID"
discovery_report "$STH_REPORT"
assert_discovery_case "stale-host-session" "$STH_REPORT" "bridge_live" "stale_host_session"
restore_file "$HOST_SESSION_PATH" "host_editor_session.json"

LPO_REPORT="$TMP_DIR/live_process_only_report.json"
mutate_state_files "live_process_only" "$LIVE_PID" "$DEAD_PID"
discovery_report "$LPO_REPORT"
assert_discovery_case "live-process-only" "$LPO_REPORT" "editor_process_only" "live_process_only"
restore_file "$HOST_SESSION_PATH" "host_editor_session.json"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

SBR_REPORT="$TMP_DIR/stale_bridge_state_report.json"
mutate_state_files "stale_bridge_state" "$LIVE_PID" "$DEAD_PID"
discovery_report "$SBR_REPORT"
assert_discovery_case "stale-bridge-state" "$SBR_REPORT" "host_session_live" "stale_bridge_state"
restore_file "$HOST_SESSION_PATH" "host_editor_session.json"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

BD_REPORT="$TMP_DIR/bridge_disabled_report.json"
"$WRAPPER" request-editor-quit --project-root "$PROJECT_ROOT" --timeout-ms 30000 >/dev/null 2>&1 || true
if ! wait_for_no_editor "$BD_REPORT"; then
  force_stop_project_editors "$BD_REPORT"
  if ! wait_for_no_editor "$BD_REPORT"; then
    echo "[fail] could not stop editor for bridge-disabled proof" >&2
    exit 1
  fi
fi
mutate_state_files "bridge_disabled" "0" "$DEAD_PID"
discovery_report "$BD_REPORT"
assert_discovery_case "bridge-disabled" "$BD_REPORT" "bridge_disabled" "bridge_disabled"

restore_file "$CONFIG_PATH" "bridge_config.json"
ensure_ready
FINAL_REPORT="$TMP_DIR/final_report.json"
discovery_report "$FINAL_REPORT"
assert_discovery_case "final-healthy" "$FINAL_REPORT" "bridge_live" "bridge_state_authoritative"
