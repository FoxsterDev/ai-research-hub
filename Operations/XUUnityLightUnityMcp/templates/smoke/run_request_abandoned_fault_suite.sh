#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
FAULT_RELATIVE_DIR="Assets/Editor/XUUnityLightMcpFaultInjection"
TEST_RELATIVE_DIR=""
RESTORE_EDITOR_STATE="true"
OPEN_EDITOR="true"
PROJECT_REFRESH_TIMEOUT_MS=""
REQUEST_TIMEOUT_MS=""
TMP_DIR=""
LAST_OUTPUT_FILE=""
FAULT_DIR_PREEXISTED="false"
TEST_DIR_PREEXISTED="false"
RUNTIME_CONFIG_FILE=""
INITIAL_EDITOR_RUNNING="unknown"
SHOULD_RESTORE_EDITOR_STATE="false"
RETAIN_FIXTURES="false"

usage() {
  cat <<'EOF'
Usage:
  run_request_abandoned_fault_suite.sh \
    --project-root /path/to/UnityProject \
    [--fault-relative-dir Assets/Editor/XUUnityLightMcpFaultInjection] \
    [--test-relative-dir Assets/Tests/EditMode/XUUnityLightMcpFaultInjection] \
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
    --fault-relative-dir)
      shift
      [[ $# -gt 0 ]] || fail_usage "--fault-relative-dir requires a value"
      FAULT_RELATIVE_DIR="$1"
      ;;
    --test-relative-dir)
      shift
      [[ $# -gt 0 ]] || fail_usage "--test-relative-dir requires a value"
      TEST_RELATIVE_DIR="$1"
      ;;
    --no-open-editor)
      OPEN_EDITOR="false"
      ;;
    --retain-fixtures)
      RETAIN_FIXTURES="true"
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
if [[ -z "$TEST_RELATIVE_DIR" ]]; then
  TEST_RELATIVE_DIR="$FAULT_RELATIVE_DIR"
fi

STATE_ROOT="$PROJECT_ROOT/Library/XUUnityLightMcp"
LIBRARY_ROOT="$PROJECT_ROOT/Library"
INBOX_DIR="$STATE_ROOT/inbox"
JOURNAL_DIR="$STATE_ROOT/journal/requests"
FAULT_DIR="$PROJECT_ROOT/$FAULT_RELATIVE_DIR"
TEST_DIR="$PROJECT_ROOT/$TEST_RELATIVE_DIR"
TEST_FILE="$TEST_DIR/XUUnityLightMcpRequestAbandonedEditModeTest.cs"
FULL_TEST_NAME="XUUnity.LightMcp.Editor.FaultInjection.XUUnityLightMcpRequestAbandonedEditModeTest.RequestRemainsActiveLongEnoughForReload"
PROBE_SCRIPT="$FAULT_DIR/XUUnityLightMcpRequestAbandonedProbe.cs"
TMP_DIR="$(mktemp -d)"
RUNTIME_CONFIG_FILE="$TMP_DIR/runtime_config.json"
[[ -d "$FAULT_DIR" ]] && FAULT_DIR_PREEXISTED="true"
[[ -d "$TEST_DIR" ]] && TEST_DIR_PREEXISTED="true"

cleanup() {
  if [[ "$SHOULD_RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 30000 >/dev/null 2>&1 || true
  fi
  if [[ "$RETAIN_FIXTURES" != "true" ]]; then
    rm -f "$TEST_FILE" "$TEST_FILE.meta"
    rm -f "$PROBE_SCRIPT" "$PROBE_SCRIPT.meta"
    if [[ "$TEST_DIR_PREEXISTED" != "true" ]]; then
      rm -f "$TEST_DIR.meta"
      rmdir "$TEST_DIR" 2>/dev/null || true
    fi
    if [[ "$FAULT_DIR_PREEXISTED" != "true" ]]; then
      rm -f "$FAULT_DIR.meta"
      rmdir "$FAULT_DIR" 2>/dev/null || true
    fi
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

purge_generated_compilation_artifacts() {
  rm -rf "$LIBRARY_ROOT/Bee/artifacts"
}

run_raw_file_ipc_refresh() {
  local output_file="$1"

  if ! python3 - "$PROJECT_ROOT" "$INBOX_DIR" "$STATE_ROOT/outbox" "$output_file" "$PROJECT_REFRESH_TIMEOUT_MS" <<'PY'; then
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

wait_for_journal_event() {
  local request_id="$1"
  local event_type="$2"
  local timeout_seconds="$3"
  local output_file="$4"

  if ! python3 - "$JOURNAL_DIR" "$request_id" "$event_type" "$timeout_seconds" "$output_file" <<'PY'; then
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

echo "[mcp-abandoned] project_root=$PROJECT_ROOT"

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

run_step runtime_config \
  "$WRAPPER" runtime-config-show \
  --project-root "$PROJECT_ROOT"
PROJECT_REFRESH_TIMEOUT_MS="${PROJECT_REFRESH_TIMEOUT_MS:-$(resolve_runtime_setting 180000 smoke request_abandoned project_refresh_timeout_ms)}"
REQUEST_TIMEOUT_MS="${REQUEST_TIMEOUT_MS:-$(resolve_runtime_setting 300000 smoke request_abandoned request_timeout_ms)}"

mkdir -p "$TEST_DIR"
mkdir -p "$FAULT_DIR"
cat > "$TEST_FILE" <<'EOF'
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace XUUnity.LightMcp.Editor.FaultInjection
{
    public sealed class XUUnityLightMcpRequestAbandonedEditModeTest
    {
        [UnityTest]
        public IEnumerator RequestRemainsActiveLongEnoughForReload()
        {
            yield return new WaitForSecondsRealtime(120f);
            Assert.Pass();
        }
    }
}
EOF
cat > "$PROBE_SCRIPT" <<EOF
using UnityEditor;

namespace XUUnity.LightMcp.Editor.FaultInjection
{
    [InitializeOnLoad]
    internal static class XUUnityLightMcpRequestAbandonedProbe
    {
        const string Marker = "$(date -u +%Y%m%dT%H%M%SZ)_bootstrap";

        static XUUnityLightMcpRequestAbandonedProbe()
        {
            _ = Marker;
        }
    }
}
EOF

LAST_OUTPUT_FILE="$TMP_DIR/compile_test_fixture.json"
if ! run_raw_file_ipc_refresh "$LAST_OUTPUT_FILE"; then
  fail_step "compile_test_fixture"
fi
summarize_json \
  "compile-test-fixture" \
  "$TMP_DIR/compile_test_fixture.json" \
  "\"outcome=%s\" % (__import__('json').loads(data['payload_json']).get('outcome'))"

REQUEST_ID="$(python3 - "$PROJECT_ROOT" "$INBOX_DIR" "$FULL_TEST_NAME" "$REQUEST_TIMEOUT_MS" <<'PY'
import json
import sys
import time
import uuid
from pathlib import Path

project_root = sys.argv[1]
inbox_dir = Path(sys.argv[2])
full_test_name = sys.argv[3]
request_timeout_ms = int(sys.argv[4])
request_id = str(uuid.uuid4())
request = {
    "request_id": request_id,
    "operation": "unity.tests.run_editmode",
    "project_root": project_root,
    "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "timeout_ms": request_timeout_ms,
    "args_json": json.dumps({
        "testNames": [full_test_name],
    }, ensure_ascii=True, separators=(",", ":")),
}
inbox_dir.mkdir(parents=True, exist_ok=True)
(inbox_dir / f"{request_id}.json").write_text(json.dumps(request, ensure_ascii=True, indent=2))
print(request_id)
PY
)"
echo "[pass] injected-request request_id=$REQUEST_ID test_name=$FULL_TEST_NAME"

STARTED_EVENT_FILE="$TMP_DIR/request_started.json"
ABANDONED_EVENT_FILE="$TMP_DIR/request_abandoned.json"

if ! wait_for_journal_event "$REQUEST_ID" "request_started" 30 "$STARTED_EVENT_FILE"; then
  LAST_OUTPUT_FILE="$STARTED_EVENT_FILE"
  fail_step "request-started"
fi
summarize_json \
  "request-started" \
  "$STARTED_EVENT_FILE" \
  "\"operation=%s started_at=%s\" % (data.get('operation'), data.get('started_at_utc'))"

sleep 2
mkdir -p "$FAULT_DIR"
cat > "$PROBE_SCRIPT" <<EOF
using UnityEditor;

namespace XUUnity.LightMcp.Editor.FaultInjection
{
    [InitializeOnLoad]
    internal static class XUUnityLightMcpRequestAbandonedProbe
    {
        const string Marker = "$(date -u +%Y%m%dT%H%M%SZ)";

        static XUUnityLightMcpRequestAbandonedProbe()
        {
            _ = Marker;
        }
    }
}
EOF
echo "[pass] injected-reload-probe path=$PROBE_SCRIPT"
activate_app "Unity"

if ! wait_for_journal_event "$REQUEST_ID" "request_abandoned" 240 "$ABANDONED_EVENT_FILE"; then
  LAST_OUTPUT_FILE="$ABANDONED_EVENT_FILE"
  fail_step "request-abandoned"
fi
summarize_json \
  "request-abandoned" \
  "$ABANDONED_EVENT_FILE" \
  "\"operation=%s reason=%s retryable=%s status=%s\" % (data.get('operation'), data.get('reason'), data.get('retryable'), data.get('reclassified_status'))"

run_step final_status_before_cleanup \
  "$WRAPPER" request-final-status \
  --project-root "$PROJECT_ROOT" \
  --request-id "$REQUEST_ID" \
  --operation unity.tests.run_editmode \
  --timeout-ms 0
summarize_json \
  "final-status-before-cleanup" \
  "$TMP_DIR/final_status_before_cleanup.json" \
  "\"completed=%s reclassified=%s retryable=%s action=%s\" % (data.get('request_completed'), data.get('reclassified'), data.get('retryable'), data.get('recommended_next_action'))"
python3 - "$TMP_DIR/final_status_before_cleanup.json" <<'PY' || fail_step "final-status-before-cleanup"
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
if bool(data.get("request_completed")):
    raise SystemExit(0)

if bool(data.get("reclassified")) and bool(data.get("retryable")):
    reason = str(data.get("reclassified_reason") or "")
    if reason == "domain_reload_before_request_completion":
        raise SystemExit(0)

raise SystemExit(1)
PY

run_step ensure_ready_after_abandon \
  "$WRAPPER" ensure-ready \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms "$PROJECT_REFRESH_TIMEOUT_MS"
summarize_json \
  "ensure-ready-after-abandon" \
  "$TMP_DIR/ensure_ready_after_abandon.json" \
  "\"bridge=%s generation=%s health=%s\" % (data['bridge_state'].get('bridge_version'), data['bridge_state'].get('bridge_generation'), data['bridge_state'].get('health_status'))"

run_step retry_editmode_after_abandon \
  "$WRAPPER" request-editmode-tests \
  --project-root "$PROJECT_ROOT" \
  --test-name XUUnity.LightMcp.Editor.FaultInjection.DoesNotExist \
  --timeout-ms 30000
summarize_json \
  "retry-editmode-after-abandon" \
  "$TMP_DIR/retry_editmode_after_abandon.json" \
  "\"status=%s payload_type=%s\" % (data.get('status'), data.get('payload_type'))"
python3 - "$TMP_DIR/retry_editmode_after_abandon.json" <<'PY' || fail_step "retry-editmode-after-abandon"
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
error = data.get("error") or {}
if str(error.get("code") or "") == "tests_busy":
    raise SystemExit(1)
if str(data.get("status") or "") != "ok":
    raise SystemExit(1)
raise SystemExit(0)
PY

rm -f "$PROBE_SCRIPT" "$PROBE_SCRIPT.meta"
rm -f "$TEST_FILE" "$TEST_FILE.meta"
if [[ "$RETAIN_FIXTURES" == "true" ]]; then
  echo "[pass] retained-fixtures test=$TEST_FILE probe=$PROBE_SCRIPT"
else
  if [[ "$TEST_DIR_PREEXISTED" != "true" ]]; then
    rm -f "$TEST_DIR.meta"
    rmdir "$TEST_DIR" 2>/dev/null || true
  fi
  if [[ "$FAULT_DIR_PREEXISTED" != "true" ]]; then
    rm -f "$FAULT_DIR.meta"
    rmdir "$FAULT_DIR" 2>/dev/null || true
  fi
  purge_generated_compilation_artifacts

  LAST_OUTPUT_FILE="$TMP_DIR/cleanup_refresh.json"
  if ! run_raw_file_ipc_refresh "$LAST_OUTPUT_FILE"; then
    fail_step "cleanup_refresh"
  fi
  summarize_json \
    "cleanup-refresh" \
    "$TMP_DIR/cleanup_refresh.json" \
    "\"outcome=%s\" % (__import__('json').loads(data['payload_json']).get('outcome'))"
fi

run_step final_status \
  "$WRAPPER" request-status-summary \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000
summarize_json \
  "final-status" \
  "$TMP_DIR/final_status.json" \
  "\"generation=%s health=%s playmode=%s\" % (data.get('bridge_generation'), data.get('health_status'), data.get('playmode_state'))"

echo "[pass] request-abandoned-fault overall"
