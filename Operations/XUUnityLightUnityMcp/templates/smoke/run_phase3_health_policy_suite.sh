#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATES_DIR="$OPS_ROOT/templates"
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
  run_phase3_health_policy_suite.sh \
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

assert_health_case() {
  local label="$1"
  local input_file="$2"
  local expected_health="$3"
  local expected_policy="$4"
  local expected_anr="$5"

  python3 - "$label" "$input_file" "$expected_health" "$expected_policy" "$expected_anr" <<'PY'
import json
import sys

label, input_file, expected_health, expected_policy, expected_anr = sys.argv[1:6]
data = json.load(open(input_file, encoding="utf-8"))
actual_health = str(data.get("host_health_classification") or "")
actual_policy = str(data.get("host_health_termination_policy") or "")
actual_anr = str(data.get("anr_classification") or "")
if (
    actual_health != expected_health
    or actual_policy != expected_policy
    or actual_anr != expected_anr
):
    raise SystemExit(
        f"{label}: expected ({expected_health}, {expected_policy}, {expected_anr}), "
        f"got ({actual_health}, {actual_policy}, {actual_anr})"
    )
print(
    "[pass] %s host_health=%s termination_policy=%s anr=%s" % (
        label,
        actual_health,
        actual_policy,
        actual_anr,
    )
)
PY
}

mutate_bridge_state_profile() {
  local mode="$1"
  local live_pid="$2"
  python3 - "$mode" "$PROJECT_ROOT" "$BRIDGE_STATE_PATH" "$HOST_SESSION_PATH" "$live_pid" <<'PY'
import json
import sys
import time
from pathlib import Path

mode, project_root, bridge_state_path, host_session_path, live_pid_raw = sys.argv[1:6]
project_root = str(Path(project_root).expanduser().resolve())
bridge_state_path = Path(bridge_state_path)
host_session_path = Path(host_session_path)
live_pid = int(live_pid_raw)

def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

def heartbeat_utc(seconds_ago: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))

bridge_state = read_json(bridge_state_path)
bridge_state["project_root"] = project_root
bridge_state["editor_pid"] = live_pid
bridge_state["health_status"] = "healthy"
bridge_state["transport"] = str(bridge_state.get("transport") or "tcp_loopback")
bridge_state["transport_requested"] = str(bridge_state.get("transport_requested") or bridge_state["transport"])
bridge_state["busy_reason"] = "idle"
bridge_state["busy_reason_detail"] = ""
bridge_state["active_operation"] = ""
bridge_state["pending_request_count"] = 0
bridge_state["last_processed_request_id"] = ""
bridge_state["request_journal_head"] = ""
bridge_state["domain_reload_in_progress"] = False
bridge_state["package_operation_in_progress"] = False
bridge_state["refresh_settle_pending"] = False
bridge_state["compile_settle_pending"] = False
bridge_state["playmode_transition_pending"] = False
bridge_state["script_reload_pending"] = False
bridge_state["asset_import_in_progress"] = False
bridge_state["is_compiling"] = False
bridge_state["is_updating"] = False

host_session = read_json(host_session_path)
host_session["project_root"] = project_root
host_session["editor_pid"] = live_pid
host_session["opened_by_host"] = True
write_json(host_session_path, host_session)

if mode == "stale":
    bridge_state["heartbeat_utc"] = heartbeat_utc(8)
elif mode == "anr_suspected":
    bridge_state["heartbeat_utc"] = heartbeat_utc(20)
elif mode == "anr":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
elif mode == "normal_churn":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
    bridge_state["busy_reason"] = "updating"
    bridge_state["busy_reason_detail"] = "Simulated lifecycle churn"
    bridge_state["active_operation"] = "unity.project.refresh"
    bridge_state["pending_request_count"] = 1
    bridge_state["refresh_settle_pending"] = True
    bridge_state["is_updating"] = True
else:
    raise SystemExit(f"Unknown mode: {mode}")

write_json(bridge_state_path, bridge_state)
PY
}

internal_discovery_report_with_profile() {
  local output_file="$1"
  local mode="$2"
  local live_pid="$3"
  PYTHONPATH="$TEMPLATES_DIR" python3 - "$PROJECT_ROOT" "$BRIDGE_STATE_PATH" "$HOST_SESSION_PATH" "$mode" "$live_pid" <<'PY' >"$output_file"
import json
import sys
import time
from pathlib import Path

import server
from server_discovery import discover_project_context_state
from server_health import classify_project_health

project_root = Path(sys.argv[1]).expanduser().resolve()
bridge_state_path = Path(sys.argv[2])
host_session_path = Path(sys.argv[3])
mode = sys.argv[4]
live_pid = int(sys.argv[5])

def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

def heartbeat_utc(seconds_ago: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))

bridge_state = read_json(bridge_state_path)
bridge_state["project_root"] = str(project_root)
bridge_state["editor_pid"] = live_pid
bridge_state["health_status"] = "healthy"
bridge_state["transport"] = str(bridge_state.get("transport") or "tcp_loopback")
bridge_state["transport_requested"] = str(bridge_state.get("transport_requested") or bridge_state["transport"])
bridge_state["busy_reason"] = "idle"
bridge_state["busy_reason_detail"] = ""
bridge_state["active_operation"] = ""
bridge_state["pending_request_count"] = 0
bridge_state["last_processed_request_id"] = ""
bridge_state["request_journal_head"] = ""
bridge_state["domain_reload_in_progress"] = False
bridge_state["package_operation_in_progress"] = False
bridge_state["refresh_settle_pending"] = False
bridge_state["compile_settle_pending"] = False
bridge_state["playmode_transition_pending"] = False
bridge_state["script_reload_pending"] = False
bridge_state["asset_import_in_progress"] = False
bridge_state["is_compiling"] = False
bridge_state["is_updating"] = False

host_session = read_json(host_session_path)
host_session["project_root"] = str(project_root)
host_session["editor_pid"] = live_pid
host_session["opened_by_host"] = True
write_json(host_session_path, host_session)

if mode == "stale":
    bridge_state["heartbeat_utc"] = heartbeat_utc(8)
elif mode == "anr_suspected":
    bridge_state["heartbeat_utc"] = heartbeat_utc(20)
elif mode == "anr":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
elif mode == "normal_churn":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
    bridge_state["busy_reason"] = "updating"
    bridge_state["busy_reason_detail"] = "Simulated lifecycle churn"
    bridge_state["active_operation"] = "unity.project.refresh"
    bridge_state["pending_request_count"] = 1
    bridge_state["refresh_settle_pending"] = True
    bridge_state["is_updating"] = True
else:
    raise SystemExit(f"Unknown mode: {mode}")

write_json(bridge_state_path, bridge_state)

def build_project_health(*, project_root, bridge_state, host_editor_session_state, discovery):
    return classify_project_health(
        bridge_state=bridge_state,
        discovery=discovery,
        editor_log_diagnosis={},
        heartbeat_age_seconds=server.heartbeat_age_seconds,
        derive_busy_reason=server.derive_busy_reason,
    )

platform_adapter = server.current_host_platform_adapter()
discovery = discover_project_context_state(
    project_root,
    try_read_bridge_state=server.try_read_bridge_state,
    try_read_host_editor_session_state=server.try_read_host_editor_session_state,
    find_running_unity_editors_for_project=server.find_running_unity_editors_for_project,
    pid_is_alive=platform_adapter.pid_is_alive,
    bridge_enabled=server.bridge_enabled,
    build_project_health=build_project_health,
)
print(json.dumps(discovery, ensure_ascii=True, indent=2))
PY
}

invoke_internal_policy() {
  local output_file="$1"
  local allow_open="$2"
  PYTHONPATH="$TEMPLATES_DIR" python3 - "$PROJECT_ROOT" "$allow_open" <<'PY' >"$output_file"
import json
import sys
from pathlib import Path

import server

project_root = Path(sys.argv[1]).expanduser().resolve()
allow_open = sys.argv[2] == "true"
payload = server.execute_host_health_recovery_policy(
    project_root,
    timeout_ms=5000,
    startup_policy="fail_fast_on_interactive_compile_block",
    allow_open_editor=allow_open,
)
print(json.dumps(payload, ensure_ascii=True, indent=2))
PY
}

invoke_internal_policy_with_profile() {
  local output_file="$1"
  local mode="$2"
  local live_pid="$3"
  local allow_open="$4"
  PYTHONPATH="$TEMPLATES_DIR" python3 - "$PROJECT_ROOT" "$BRIDGE_STATE_PATH" "$HOST_SESSION_PATH" "$mode" "$live_pid" "$allow_open" <<'PY' >"$output_file"
import json
import sys
import time
from pathlib import Path
from unittest import mock

import server
from server_discovery import discover_project_context_state
from server_health import classify_project_health

project_root = Path(sys.argv[1]).expanduser().resolve()
bridge_state_path = Path(sys.argv[2])
host_session_path = Path(sys.argv[3])
mode = sys.argv[4]
live_pid = int(sys.argv[5])
allow_open = sys.argv[6] == "true"

def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

def heartbeat_utc(seconds_ago: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds_ago))

bridge_state = read_json(bridge_state_path)
bridge_state["project_root"] = str(project_root)
bridge_state["editor_pid"] = live_pid
bridge_state["health_status"] = "healthy"
bridge_state["transport"] = str(bridge_state.get("transport") or "tcp_loopback")
bridge_state["transport_requested"] = str(bridge_state.get("transport_requested") or bridge_state["transport"])
bridge_state["busy_reason"] = "idle"
bridge_state["busy_reason_detail"] = ""
bridge_state["active_operation"] = ""
bridge_state["pending_request_count"] = 0
bridge_state["last_processed_request_id"] = ""
bridge_state["request_journal_head"] = ""
bridge_state["domain_reload_in_progress"] = False
bridge_state["package_operation_in_progress"] = False
bridge_state["refresh_settle_pending"] = False
bridge_state["compile_settle_pending"] = False
bridge_state["playmode_transition_pending"] = False
bridge_state["script_reload_pending"] = False
bridge_state["asset_import_in_progress"] = False
bridge_state["is_compiling"] = False
bridge_state["is_updating"] = False

host_session = read_json(host_session_path)
host_session["project_root"] = str(project_root)
host_session["editor_pid"] = live_pid
host_session["opened_by_host"] = True
write_json(host_session_path, host_session)

if mode == "anr":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
elif mode == "normal_churn":
    bridge_state["heartbeat_utc"] = heartbeat_utc(40)
    bridge_state["busy_reason"] = "updating"
    bridge_state["busy_reason_detail"] = "Simulated lifecycle churn"
    bridge_state["active_operation"] = "unity.project.refresh"
    bridge_state["pending_request_count"] = 1
    bridge_state["refresh_settle_pending"] = True
    bridge_state["is_updating"] = True
else:
    raise SystemExit(f"Unknown mode: {mode}")

write_json(bridge_state_path, bridge_state)

def build_project_health(*, project_root, bridge_state, host_editor_session_state, discovery):
    return classify_project_health(
        bridge_state=bridge_state,
        discovery=discovery,
        editor_log_diagnosis={},
        heartbeat_age_seconds=server.heartbeat_age_seconds,
        derive_busy_reason=server.derive_busy_reason,
    )

platform_adapter = server.current_host_platform_adapter()
discovery = discover_project_context_state(
    project_root,
    try_read_bridge_state=server.try_read_bridge_state,
    try_read_host_editor_session_state=server.try_read_host_editor_session_state,
    find_running_unity_editors_for_project=server.find_running_unity_editors_for_project,
    pid_is_alive=platform_adapter.pid_is_alive,
    bridge_enabled=server.bridge_enabled,
    build_project_health=build_project_health,
)
with mock.patch.object(server, "current_project_context_discovery_details", return_value=discovery):
    payload = server.execute_host_health_recovery_policy(
        project_root,
        timeout_ms=5000,
        startup_policy="fail_fast_on_interactive_compile_block",
        allow_open_editor=allow_open,
    )
print(json.dumps(payload, ensure_ascii=True, indent=2))
PY
}

assert_policy_action() {
  local label="$1"
  local input_file="$2"
  local expected_action="$3"
  python3 - "$label" "$input_file" "$expected_action" <<'PY'
import json
import sys

label, input_file, expected_action = sys.argv[1:4]
data = json.load(open(input_file, encoding="utf-8"))
actual_action = str(data.get("action") or "")
if actual_action != expected_action:
    raise SystemExit(f"{label}: expected action {expected_action}, got {actual_action}")
print(f"[pass] {label} action={actual_action}")
PY
}

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
status_summary "$BASELINE_REPORT"
assert_health_case "baseline" "$BASELINE_REPORT" "fresh" "observe_only" "none"

LIVE_PID="$(json_field "$BASELINE_REPORT" "editor_pid")"
if [[ -z "$LIVE_PID" || "$LIVE_PID" == "0" ]]; then
  echo "[fail] baseline did not produce a live editor pid" >&2
  exit 1
fi

STALE_REPORT="$TMP_DIR/stale_report.json"
internal_discovery_report_with_profile "$STALE_REPORT" "stale" "$LIVE_PID"
assert_health_case "stale" "$STALE_REPORT" "stale" "observe_only" "none"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

ANR_SUSPECTED_REPORT="$TMP_DIR/anr_suspected_report.json"
internal_discovery_report_with_profile "$ANR_SUSPECTED_REPORT" "anr_suspected" "$LIVE_PID"
assert_health_case "anr-suspected" "$ANR_SUSPECTED_REPORT" "anr_suspected" "observe_only" "anr_suspected"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

ANR_REPORT="$TMP_DIR/anr_report.json"
internal_discovery_report_with_profile "$ANR_REPORT" "anr" "$LIVE_PID"
assert_health_case "anr" "$ANR_REPORT" "anr" "graceful_terminate" "anr"

ANR_POLICY_REPORT="$TMP_DIR/anr_policy_report.json"
invoke_internal_policy_with_profile "$ANR_POLICY_REPORT" "anr" "$LIVE_PID" "false"
assert_policy_action "anr-policy-deferred" "$ANR_POLICY_REPORT" "termination_deferred_no_open"
ANR_POST_POLICY_REPORT="$TMP_DIR/anr_post_policy_report.json"
internal_discovery_report_with_profile "$ANR_POST_POLICY_REPORT" "anr" "$LIVE_PID"
assert_health_case "anr-post-policy" "$ANR_POST_POLICY_REPORT" "anr" "graceful_terminate" "anr"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

NORMAL_CHURN_REPORT="$TMP_DIR/normal_churn_report.json"
internal_discovery_report_with_profile "$NORMAL_CHURN_REPORT" "normal_churn" "$LIVE_PID"
assert_health_case "normal-churn" "$NORMAL_CHURN_REPORT" "stale" "observe_only" "none"

NORMAL_CHURN_POLICY_REPORT="$TMP_DIR/normal_churn_policy_report.json"
invoke_internal_policy_with_profile "$NORMAL_CHURN_POLICY_REPORT" "normal_churn" "$LIVE_PID" "true"
assert_policy_action "normal-churn-policy" "$NORMAL_CHURN_POLICY_REPORT" "none"
NORMAL_CHURN_POST_POLICY_REPORT="$TMP_DIR/normal_churn_post_policy_report.json"
internal_discovery_report_with_profile "$NORMAL_CHURN_POST_POLICY_REPORT" "normal_churn" "$LIVE_PID"
assert_health_case "normal-churn-post-policy" "$NORMAL_CHURN_POST_POLICY_REPORT" "stale" "observe_only" "none"
restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"

FINAL_REPORT="$TMP_DIR/final_report.json"
ensure_ready
status_summary "$FINAL_REPORT"
assert_health_case "final-healthy" "$FINAL_REPORT" "fresh" "observe_only" "none"
