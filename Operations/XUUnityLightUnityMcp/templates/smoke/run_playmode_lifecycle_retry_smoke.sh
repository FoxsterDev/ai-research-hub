#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
ASSEMBLY_NAME=""
TEST_NAME=""
REQUEST_TIMEOUT_MS="240000"
OPEN_EDITOR="true"
RESTORE_EDITOR_STATE="true"
TMP_DIR=""
LAST_OUTPUT_FILE=""

usage() {
  cat <<'EOF'
Usage:
  run_playmode_lifecycle_retry_smoke.sh \
    --project-root /path/to/UnityProject \
    --assembly-name PlayMode.Tests \
    [--test-name MyPlayModeTest] \
    [--request-timeout-ms 240000] \
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
    --assembly-name)
      shift
      [[ $# -gt 0 ]] || fail_usage "--assembly-name requires a value"
      ASSEMBLY_NAME="$1"
      ;;
    --test-name)
      shift
      [[ $# -gt 0 ]] || fail_usage "--test-name requires a value"
      TEST_NAME="$1"
      ;;
    --request-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--request-timeout-ms requires a value"
      REQUEST_TIMEOUT_MS="$1"
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
[[ -n "$ASSEMBLY_NAME" ]] || fail_usage "missing required argument: --assembly-name"
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
  if ! "$@" >"$LAST_OUTPUT_FILE"; then
    fail_step "$step_name"
  fi
}

echo "[mcp-playmode-churn] project_root=$PROJECT_ROOT"

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 180000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi
run_step ensure_ready "${ensure_ready_cmd[@]}"

run_step enter_playmode \
  "$WRAPPER" request-playmode-set \
  --project-root "$PROJECT_ROOT" \
  --action enter \
  --timeout-ms 180000

first_request_cmd=(
  "$WRAPPER" request-playmode-tests
  --project-root "$PROJECT_ROOT"
  --assembly-name "$ASSEMBLY_NAME"
  --timeout-ms "$REQUEST_TIMEOUT_MS"
)
if [[ -n "$TEST_NAME" ]]; then
  first_request_cmd+=(--test-name "$TEST_NAME")
fi

FIRST_REQUEST_RC=0
LAST_OUTPUT_FILE="$TMP_DIR/first_playmode_request.json"
if ! "${first_request_cmd[@]}" >"$LAST_OUTPUT_FILE"; then
  FIRST_REQUEST_RC=$?
fi

python3 - "$TMP_DIR/first_playmode_request.json" "$TMP_DIR/followup_plan.json" "$FIRST_REQUEST_RC" <<'PY'
import json
import sys
from pathlib import Path

response_path = Path(sys.argv[1])
plan_path = Path(sys.argv[2])
request_rc = int(sys.argv[3])
payload = json.loads(response_path.read_text(encoding="utf-8"))

summary = {
    "first_request_rc": request_rc,
    "first_request_status": "ok",
    "first_error_code": "",
    "first_result_trust_class": "",
    "followup_required": False,
    "request_id": str(payload.get("request_id") or ""),
}

if request_rc == 0:
    decoded = json.loads(payload.get("payload_json") or "{}")
    if not str(decoded.get("status") or "").strip():
        raise SystemExit("direct playmode retry smoke expected a non-empty test status on the happy path")
    test_verdict = str(decoded.get("test_verdict") or "")
    if test_verdict not in {"passed", "failed", "no_tests", "runtime_timeout"}:
        raise SystemExit(f"direct playmode retry smoke expected compact test_verdict, got: {test_verdict or '<empty>'}")
    summary["first_result_trust_class"] = "unity_completed_confirmed"
    summary["test_verdict"] = test_verdict
else:
    error = payload.get("error") or {}
    details = error.get("details") or {}
    final_status = details.get("request_final_status") or {}
    error_code = str(error.get("code") or "")
    trust_class = str(final_status.get("result_trust_class") or details.get("result_trust_class") or "")
    summary["first_request_status"] = "error"
    summary["first_error_code"] = error_code
    summary["first_result_trust_class"] = trust_class
    summary["request_id"] = str(details.get("request_id") or payload.get("request_id") or "")
    if error_code not in {"request_lifecycle_reset", "response_missing_after_lifecycle_reset"}:
        raise SystemExit(f"unexpected first error code: {error_code or '<empty>'}")
    if trust_class not in {"wrapper_failed_unity_unproven", "unity_completed_after_lifecycle_reset", "unity_completed_confirmed"}:
        raise SystemExit(f"unexpected trust class for lifecycle-reset recovery: {trust_class or '<empty>'}")
    test_verdict = str(final_status.get("test_verdict") or "")
    if final_status and test_verdict not in {"passed", "failed", "no_tests", "runtime_timeout", "in_progress", "unity_unproven", "infrastructure_error"}:
        raise SystemExit(f"lifecycle-reset recovery returned final status without compact test_verdict: {test_verdict or '<empty>'}")
    summary["test_verdict"] = test_verdict
    summary["followup_required"] = True

plan_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=True))
PY

FOLLOWUP_REQUIRED="$(python3 - "$TMP_DIR/followup_plan.json" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("true" if payload.get("followup_required") else "false")
PY
)"

if [[ "$FOLLOWUP_REQUIRED" == "true" ]]; then
  REQUEST_ID="$(python3 - "$TMP_DIR/followup_plan.json" <<'PY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("request_id") or "")
PY
)"
  if [[ -n "$REQUEST_ID" ]]; then
    run_step request_final_status \
      "$WRAPPER" request-final-status \
      --project-root "$PROJECT_ROOT" \
      --request-id "$REQUEST_ID"
    python3 - "$TMP_DIR/request_final_status.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
test_verdict = str(payload.get("test_verdict") or "")
if test_verdict not in {"passed", "failed", "no_tests", "runtime_timeout", "in_progress", "unity_unproven", "infrastructure_error"}:
    raise SystemExit(f"request-final-status did not include compact test_verdict: {test_verdict or '<empty>'}")
if payload.get("result_payload_available") and payload.get("result_payload_source") not in {"response_payload", "persisted_test_result"}:
    raise SystemExit("request-final-status reported result payload without a trustworthy source")
print(json.dumps({
    "request_final_status_test_verdict": test_verdict,
    "result_payload_source": payload.get("result_payload_source", ""),
}, ensure_ascii=True))
PY
  fi

  followup_request_cmd=(
    "$WRAPPER" request-playmode-tests
    --project-root "$PROJECT_ROOT"
    --assembly-name "$ASSEMBLY_NAME"
    --timeout-ms "$REQUEST_TIMEOUT_MS"
  )
  if [[ -n "$TEST_NAME" ]]; then
    followup_request_cmd+=(--test-name "$TEST_NAME")
  fi

  FOLLOWUP_RC=0
  LAST_OUTPUT_FILE="$TMP_DIR/followup_playmode_request.json"
  if ! "${followup_request_cmd[@]}" >"$LAST_OUTPUT_FILE"; then
    FOLLOWUP_RC=$?
  fi

  python3 - "$TMP_DIR/followup_playmode_request.json" "$FOLLOWUP_RC" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
request_rc = int(sys.argv[2])
if request_rc == 0:
    print(json.dumps({"followup_status": "ok", "tests_busy_released": True}, ensure_ascii=True))
    raise SystemExit(0)

error = payload.get("error") or {}
error_code = str(error.get("code") or "")
if error_code == "tests_busy":
    raise SystemExit("stale active test ownership was not released after reclassified PlayMode request")

details = error.get("details") or {}
final_status = details.get("request_final_status") or {}
print(json.dumps(
    {
        "followup_status": "error",
        "followup_error_code": error_code,
        "followup_result_trust_class": str(final_status.get("result_trust_class") or details.get("result_trust_class") or ""),
        "tests_busy_released": True,
    },
    ensure_ascii=True,
))
PY
fi

run_step final_status_summary \
  "$WRAPPER" request-status-summary \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000

python3 - "$TMP_DIR/final_status_summary.json" "$TMP_DIR/followup_plan.json" <<'PY'
import json
import sys
from pathlib import Path

status_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
plan_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

if status_payload.get("health_status") != "healthy":
    raise SystemExit("bridge did not return to healthy state")
if status_payload.get("playmode_state") != "edit":
    raise SystemExit("playmode did not settle back to edit")

summary = {
    "first_request_status": plan_payload.get("first_request_status"),
    "first_error_code": plan_payload.get("first_error_code", ""),
    "trust_class": plan_payload.get("first_result_trust_class", ""),
    "test_verdict": plan_payload.get("test_verdict", ""),
    "followup_required": bool(plan_payload.get("followup_required")),
    "final_health": status_payload.get("health_status"),
    "final_playmode_state": status_payload.get("playmode_state"),
}
print(json.dumps(summary, ensure_ascii=True))
PY

echo "[pass] playmode-lifecycle-retry-smoke"
