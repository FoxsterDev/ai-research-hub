#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
TIMEOUT_MS="180000"
TMP_DIR="$(mktemp -d)"
STATE_ROOT=""
BRIDGE_STATE_PATH=""
HOST_SESSION_PATH=""

usage() {
  cat <<'EOF'
Usage:
  run_recovery_compile_gate_suite.sh \
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

STATE_ROOT="$PROJECT_ROOT/Library/XUUnityLightMcp/state"
BRIDGE_STATE_PATH="$STATE_ROOT/bridge_state.json"
HOST_SESSION_PATH="$STATE_ROOT/host_editor_session.json"

backup_file() {
  local source_path="$1"
  local backup_name="$2"
  if [[ -f "$source_path" ]]; then
    cp "$source_path" "$TMP_DIR/$backup_name"
  else
    : >"$TMP_DIR/$backup_name.missing"
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
  restore_file "$BRIDGE_STATE_PATH" "bridge_state.json"
  restore_file "$HOST_SESSION_PATH" "host_editor_session.json"
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

backup_file "$BRIDGE_STATE_PATH" "bridge_state.json"
backup_file "$HOST_SESSION_PATH" "host_editor_session.json"

status_file="$TMP_DIR/status_before.json"
if "$WRAPPER" request-status-summary --project-root "$PROJECT_ROOT" --timeout-ms 5000 >"$status_file" 2>/dev/null; then
  if python3 - "$status_file" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if bool(data.get("editor_running")) else 1)
PY
  then
    echo "[fail] recovery-compile-gate-suite requires the project editor to be closed first" >&2
    exit 1
  fi
fi

mkdir -p "$STATE_ROOT"
python3 - "$PROJECT_ROOT" "$BRIDGE_STATE_PATH" <<'PY'
import json
import sys
import time
from pathlib import Path

project_root, bridge_state_path = sys.argv[1:3]
payload = {
    "bridge_version": 9,
    "project_root": str(Path(project_root).resolve()),
    "editor_pid": 999999,
    "unity_version": "",
    "transport_requested": "tcp_loopback",
    "transport": "tcp_loopback",
    "transport_listener_state": "listening",
    "transport_host": "127.0.0.1",
    "transport_port": 59999,
    "bridge_session_id": "recovery-compile-gate-suite",
    "bridge_generation": 1,
    "bridge_bootstrap_attached": True,
    "heartbeat_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 300)),
    "health_status": "healthy",
    "pending_request_count": 0,
    "playmode_state": "edit",
    "busy_reason": "",
    "busy_reason_detail": "",
    "request_journal_head": "",
}
path = Path(bridge_state_path)
path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
PY

output_file="$TMP_DIR/recover_editor_session.json"
if ! "$WRAPPER" recover-editor-session \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms "$TIMEOUT_MS" \
  --force-compile-probe >"$output_file"; then
  echo "[fail] recover-editor-session" >&2
  cat "$output_file" >&2
  exit 1
fi

python3 - "$output_file" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))

if str(data.get("recovery_classification") or "") != "recovered":
    raise SystemExit(f"expected recovery_classification=recovered, got {data.get('recovery_classification')!r}")
if not bool(data.get("compile_probe_attempted")):
    raise SystemExit("expected compile_probe_attempted=true")
if not bool(data.get("stale_bridge_state_cleared")):
    raise SystemExit("expected stale_bridge_state_cleared=true")

compile_probe = data.get("compile_probe") or {}
if not bool(compile_probe.get("succeeded")):
    raise SystemExit("expected compile_probe.succeeded=true")

after = data.get("discovery_after_recovery") or {}
if str(after.get("reconciliation_case") or "") != "host_launchable_not_active":
    raise SystemExit(
        "expected discovery_after_recovery.reconciliation_case=host_launchable_not_active, "
        f"got {after.get('reconciliation_case')!r}"
    )

summary = compile_probe.get("compile_gate_summary") or {}
matrix = summary.get("matrix") or {}
print(
    "[pass] recovery-compile-gate-suite recovery=%s compile_gate=%s matrix=%s/%s stale_bridge_state_cleared=%s" % (
        data.get("recovery_classification"),
        "passed" if compile_probe.get("succeeded") else "failed",
        matrix.get("passed", 0),
        matrix.get("total", 0),
        str(bool(data.get("stale_bridge_state_cleared"))).lower(),
    )
)
PY
