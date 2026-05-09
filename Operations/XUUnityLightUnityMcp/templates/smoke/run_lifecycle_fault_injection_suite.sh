#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
PROBE_RELATIVE_DIR="Assets/Editor/XUUnityLightMcpFaultInjection"
RESTORE_EDITOR_STATE="true"
OPEN_EDITOR="true"
REFRESH_TIMEOUT_MS=""
TMP_DIR=""
LAST_OUTPUT_FILE=""
PROBE_DIR_PREEXISTED="false"
RUNTIME_CONFIG_FILE=""
INITIAL_EDITOR_RUNNING="unknown"
SHOULD_RESTORE_EDITOR_STATE="false"
REFRESH_PID=""

usage() {
  cat <<'EOF'
Usage:
  run_lifecycle_fault_injection_suite.sh \
    --project-root /path/to/UnityProject \
    [--probe-relative-dir Assets/Editor/XUUnityLightMcpFaultInjection] \
    [--refresh-timeout-ms 120000] \
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
    --probe-relative-dir)
      shift
      [[ $# -gt 0 ]] || fail_usage "--probe-relative-dir requires a value"
      PROBE_RELATIVE_DIR="$1"
      ;;
    --refresh-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--refresh-timeout-ms requires a value"
      REFRESH_TIMEOUT_MS="$1"
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

STATE_ROOT="$PROJECT_ROOT/Library/XUUnityLightMcp"
INBOX_DIR="$STATE_ROOT/inbox"
PROBE_DIR="$PROJECT_ROOT/$PROBE_RELATIVE_DIR"
PROBE_SCRIPT="$PROBE_DIR/XUUnityLightMcpFaultInjectionProbe.cs"
TMP_DIR="$(mktemp -d)"
RUNTIME_CONFIG_FILE="$TMP_DIR/runtime_config.json"
[[ -d "$PROBE_DIR" ]] && PROBE_DIR_PREEXISTED="true"

cleanup() {
  if [[ -n "$REFRESH_PID" ]] && kill -0 "$REFRESH_PID" >/dev/null 2>&1; then
    kill "$REFRESH_PID" >/dev/null 2>&1 || true
  fi
  if [[ "$SHOULD_RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 30000 >/dev/null 2>&1 || true
  fi
  rm -f "$PROBE_SCRIPT" "$PROBE_SCRIPT.meta"
  if [[ "$PROBE_DIR_PREEXISTED" != "true" ]]; then
    rm -f "$PROBE_DIR.meta"
    rmdir "$PROBE_DIR" 2>/dev/null || true
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

resolve_runtime_setting() {
  local fallback="$1"
  shift
  python3 - "$RUNTIME_CONFIG_FILE" "$fallback" "$@" <<'PY'
import json
import sys
from pathlib import Path

config_file = Path(sys.argv[1])
fallback = sys.argv[2]
keys = sys.argv[3:]

try:
    payload = json.loads(config_file.read_text())
except Exception:
    print(fallback)
    raise SystemExit(0)

value = payload.get("config") or {}
for key in keys:
    if not isinstance(value, dict):
        value = None
        break
    value = value.get(key)

print(fallback if value is None else value)
PY
}

wait_for_journal_event() {
  local request_id="$1"
  local event_type="$2"
  local timeout_seconds="$3"
  local output_file="$4"

  if ! python3 - "$PROJECT_ROOT/Library/XUUnityLightMcp/journal/requests" "$request_id" "$event_type" "$timeout_seconds" "$output_file" <<'PY'; then
import json
import sys
import time
from pathlib import Path

journal_dir = Path(sys.argv[1])
request_id = sys.argv[2]
event_type = sys.argv[3]
deadline = time.time() + float(sys.argv[4])
output_path = Path(sys.argv[5])

while time.time() < deadline:
    for path in sorted(journal_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        if payload.get("request_id") == request_id and payload.get("event_type") == event_type:
            output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
            print(path)
            raise SystemExit(0)
    time.sleep(0.5)

raise SystemExit(1)
PY
    return 1
  fi

  return 0
}

run_raw_file_ipc_refresh() {
  local output_file="$1"

  if ! python3 - "$PROJECT_ROOT" "$INBOX_DIR" "$STATE_ROOT/outbox" "$output_file" "$REFRESH_TIMEOUT_MS" <<'PY'; then
import json
import sys
import time
import uuid
from pathlib import Path

project_root = sys.argv[1]
inbox_dir = Path(sys.argv[2])
outbox_dir = Path(sys.argv[3])
output_path = Path(sys.argv[4])
request_timeout_ms = int(sys.argv[5])
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

start_host_refresh_wait() {
  local output_file="$1"
  "$WRAPPER" request-project-refresh \
    --project-root "$PROJECT_ROOT" \
    --timeout-ms "$REFRESH_TIMEOUT_MS" > "$output_file" &
  REFRESH_PID="$!"
}

wait_for_new_started_event() {
  local operation="$1"
  local baseline_file="$2"
  local timeout_seconds="$3"
  local output_file="$4"

  if ! python3 - "$PROJECT_ROOT/Library/XUUnityLightMcp/journal/requests" "$operation" "$baseline_file" "$timeout_seconds" "$output_file" <<'PY'; then
import json
import sys
import time
from pathlib import Path

journal_dir = Path(sys.argv[1])
operation = sys.argv[2]
baseline_file = Path(sys.argv[3])
deadline = time.time() + float(sys.argv[4])
output_path = Path(sys.argv[5])

known = set()
if baseline_file.is_file():
    known = {line.strip() for line in baseline_file.read_text().splitlines() if line.strip()}

while time.time() < deadline:
    for path in sorted(journal_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        if str(path) in known:
            continue
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        if payload.get("event_type") == "request_started" and payload.get("operation") == operation:
            output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
            print(path)
            raise SystemExit(0)
    time.sleep(0.5)

raise SystemExit(1)
PY
    return 1
  fi

  return 0
}

wait_for_generation_change() {
  local previous_generation="$1"
  local timeout_seconds="$2"
  local output_file="$3"

  if ! python3 - "$PROJECT_ROOT/Library/XUUnityLightMcp/state/bridge_state.json" "$previous_generation" "$timeout_seconds" "$output_file" <<'PY'; then
import json
import sys
import time
from pathlib import Path

state_path = Path(sys.argv[1])
previous_generation = int(sys.argv[2])
deadline = time.time() + float(sys.argv[3])
output_path = Path(sys.argv[4])

while time.time() < deadline:
    if state_path.is_file():
        try:
            payload = json.loads(state_path.read_text())
        except Exception:
            payload = None
        if isinstance(payload, dict):
            current_generation = int(payload.get("bridge_generation") or 0)
            if current_generation > previous_generation:
                output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
                raise SystemExit(0)
    time.sleep(0.5)

raise SystemExit(1)
PY
    return 1
  fi

  return 0
}

echo "[mcp-fault] project_root=$PROJECT_ROOT"

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
  "\"bridge=%s generation=%s health=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('bridge_generation'), data['bridge_state'].get('health_status'))"
INITIAL_BRIDGE_GENERATION="$(python3 - "$TMP_DIR/ensure_ready.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
print(int((data.get("bridge_state") or {}).get("bridge_generation") or 0))
PY
)"

run_step runtime_config \
  "$WRAPPER" runtime-config-show \
  --project-root "$PROJECT_ROOT"
REFRESH_TIMEOUT_MS="${REFRESH_TIMEOUT_MS:-$(resolve_runtime_setting 180000 smoke lifecycle_fault_injection refresh_timeout_ms)}"

mkdir -p "$PROBE_DIR"
find "$PROJECT_ROOT/Library/XUUnityLightMcp/journal/requests" -maxdepth 1 -type f -name '*.json' -print > "$TMP_DIR/journal_baseline.txt"
LAST_OUTPUT_FILE="$TMP_DIR/fault_refresh.json"
start_host_refresh_wait "$LAST_OUTPUT_FILE"

if ! wait_for_new_started_event "unity.project.refresh" "$TMP_DIR/journal_baseline.txt" 60 "$TMP_DIR/request_started.json"; then
  LAST_OUTPUT_FILE="$TMP_DIR/request_started.json"
  fail_step "request-started"
fi
REQUEST_ID="$(python3 - "$TMP_DIR/request_started.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
print(str(data.get("request_id") or "").strip())
PY
)"
if [[ -z "$REQUEST_ID" ]]; then
  LAST_OUTPUT_FILE="$TMP_DIR/request_started.json"
  fail_step "request-id-missing"
fi
echo "[pass] injected-refresh-request request_id=$REQUEST_ID"
summarize_json \
  "request-started" \
  "$TMP_DIR/request_started.json" \
  "\"operation=%s started_at=%s\" % (data.get('operation'), data.get('started_at_utc'))"

cat > "$PROBE_SCRIPT" <<EOF
using UnityEditor;

namespace XUUnity.LightMcp.Editor.FaultInjection
{
    [InitializeOnLoad]
    internal static class XUUnityLightMcpFaultInjectionProbe
    {
        const string Marker = "$(date -u +%Y%m%dT%H%M%SZ)";

        static XUUnityLightMcpFaultInjectionProbe()
        {
            _ = Marker;
        }
    }
}
EOF
activate_app "Unity"

if ! wait_for_generation_change "$INITIAL_BRIDGE_GENERATION" 120 "$TMP_DIR/bridge_generation_change.json"; then
  LAST_OUTPUT_FILE="$TMP_DIR/bridge_generation_change.json"
  fail_step "bridge-generation-change"
fi
summarize_json \
  "bridge-generation-change" \
  "$TMP_DIR/bridge_generation_change.json" \
  "\"prev_gen=%s curr_gen=%s session=%s\" % ($INITIAL_BRIDGE_GENERATION, data.get('bridge_generation'), data.get('bridge_session_id'))"

if ! wait "$REFRESH_PID"; then
  fail_step "fault_refresh"
fi
REFRESH_PID=""

summarize_json \
  "fault-refresh" \
  "$TMP_DIR/fault_refresh.json" \
  "\"outcome=%s prev_gen=%s curr_gen=%s status=%s\" % ((lambda payload, lifecycle, response: (payload.get('outcome'), (lifecycle.get('bridge_identity_transition') or {}).get('previous_bridge_generation'), (lifecycle.get('bridge_identity_transition') or {}).get('current_bridge_generation'), response.get('status')))(__import__('json').loads(data.get('payload_json') or '{}'), data.get('_xuunity_lifecycle') or {}, data))"

if ! python3 - "$TMP_DIR/bridge_generation_change.json" "$TMP_DIR/fault_refresh.json" "$INITIAL_BRIDGE_GENERATION" <<'PY'; then
import json
import sys
from pathlib import Path

bridge_state = json.loads(Path(sys.argv[1]).read_text())
response = json.loads(Path(sys.argv[2]).read_text())
initial_generation = int(sys.argv[3])
if int(bridge_state.get("bridge_generation") or 0) <= initial_generation:
    raise SystemExit(1)
if str(response.get("status") or "") != "ok":
    raise SystemExit(1)
lifecycle = response.get("_xuunity_lifecycle") or {}
transition = lifecycle.get("bridge_identity_transition") or {}
if int(transition.get("current_bridge_generation") or 0) <= int(transition.get("previous_bridge_generation") or 0):
    raise SystemExit(1)
if not str(transition.get("journal_event_path") or "").strip():
    raise SystemExit(1)
print(f"[pass] generation-transition prev={initial_generation} curr={bridge_state.get('bridge_generation')} journal={transition.get('journal_event_path')}")
PY
  fail_step "transition-journal"
fi

rm -f "$PROBE_SCRIPT" "$PROBE_SCRIPT.meta"
if [[ "$PROBE_DIR_PREEXISTED" != "true" ]]; then
  rm -f "$PROBE_DIR.meta"
  rmdir "$PROBE_DIR" 2>/dev/null || true
fi

LAST_OUTPUT_FILE="$TMP_DIR/cleanup_refresh.json"
if ! run_raw_file_ipc_refresh "$LAST_OUTPUT_FILE"; then
  fail_step "cleanup_refresh"
fi
summarize_json \
  "cleanup-refresh" \
  "$TMP_DIR/cleanup_refresh.json" \
  "\"outcome=%s\" % (__import__('json').loads(data['payload_json']).get('outcome'))"

run_step final_status \
  "$WRAPPER" request-status-summary \
  --project-root "$PROJECT_ROOT"
summarize_json \
  "final-status" \
  "$TMP_DIR/final_status.json" \
  "\"generation=%s health=%s playmode=%s\" % (data.get('bridge_generation'), data.get('health_status'), data.get('playmode_state'))"

echo "[pass] lifecycle-fault overall"
