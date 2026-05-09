#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
ASSEMBLY_NAME=""
TEST_NAME=""
SCENARIO_TIMEOUT_MS="240000"
DIRECT_TIMEOUT_MS="240000"
POLL_INTERVAL_MS="500"
OPEN_EDITOR="true"
RESTORE_EDITOR_STATE="true"
TMP_DIR=""
SCENARIO_FILE=""

usage() {
  cat <<'EOF'
Usage:
  run_playmode_settled_state_regression.sh \
    --project-root /path/to/UnityProject \
    --assembly-name PlayMode.Tests \
    --test-name MyPlayModeTest \
    [--scenario-timeout-ms 240000] \
    [--direct-timeout-ms 240000] \
    [--poll-interval-ms 500] \
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
    --scenario-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--scenario-timeout-ms requires a value"
      SCENARIO_TIMEOUT_MS="$1"
      ;;
    --direct-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--direct-timeout-ms requires a value"
      DIRECT_TIMEOUT_MS="$1"
      ;;
    --poll-interval-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--poll-interval-ms requires a value"
      POLL_INTERVAL_MS="$1"
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
[[ -n "$TEST_NAME" ]] || fail_usage "missing required argument: --test-name"

TMP_DIR="$(mktemp -d)"
SCENARIO_FILE="$TMP_DIR/playmode_settled_state_regression.json"

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
  shift || true
  if [[ $# -gt 0 ]]; then
    echo "$1"
  fi
  exit 1
}

echo "[mcp-regression] project_root=$PROJECT_ROOT"

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 180000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi

"${ensure_ready_cmd[@]}" >"$TMP_DIR/ensure_ready.json" || fail_step "ensure_ready"

python3 - "$SCENARIO_FILE" "$ASSEMBLY_NAME" "$TEST_NAME" <<'PY'
import json
import sys
from pathlib import Path

scenario_path = Path(sys.argv[1])
assembly_name = sys.argv[2]
test_name = sys.argv[3]
scenario = {
    "name": "playmode_settled_state_regression",
    "description": "Verify direct and scenario PlayMode test payloads agree on final settled state.",
    "stopOnFirstFailure": True,
    "steps": [
        {
            "stepId": "playmode_test",
            "kind": "tests_run_playmode",
            "assemblyNames": [assembly_name],
            "testNames": [test_name],
            "timeoutSeconds": 120.0,
        }
    ],
}
scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
PY

"$WRAPPER" request-playmode-tests \
  --project-root "$PROJECT_ROOT" \
  --assembly-name "$ASSEMBLY_NAME" \
  --test-name "$TEST_NAME" \
  --timeout-ms "$DIRECT_TIMEOUT_MS" >"$TMP_DIR/direct.json" || fail_step "direct_playmode_request"

"$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$SCENARIO_FILE" \
  --timeout-ms "$SCENARIO_TIMEOUT_MS" \
  --poll-interval-ms "$POLL_INTERVAL_MS" >"$TMP_DIR/scenario.json" || fail_step "scenario_playmode_request"

python3 - "$TMP_DIR/direct.json" "$TMP_DIR/scenario.json" <<'PY'
import json
import sys
from pathlib import Path

direct = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
scenario = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

if direct.get("status") != "ok":
    raise SystemExit("direct request did not complete with status=ok")

direct_payload = json.loads(direct.get("payload_json") or "{}")
direct_state = str(direct_payload.get("playmode_state_after_settle") or "")

if str(scenario.get("status") or scenario.get("terminal_status") or "") != "passed":
    raise SystemExit("scenario run did not finish with status=passed")

steps = scenario.get("steps") or ((scenario.get("run_start") or {}).get("steps")) or []
playmode_step = next((step for step in steps if step.get("stepId") == "playmode_test"), None)
if not isinstance(playmode_step, dict):
    raise SystemExit("scenario result is missing playmode_test step")
if str(playmode_step.get("status") or "") != "passed":
    raise SystemExit("scenario playmode_test step did not pass")

scenario_payload = json.loads(playmode_step.get("payload_json") or "{}")
scenario_state = str(scenario_payload.get("playmode_state_after_settle") or "")

if direct_state != "edit":
    raise SystemExit(f"direct settled state mismatch: expected 'edit', got '{direct_state or '<empty>'}'")
if scenario_state != "edit":
    raise SystemExit(f"scenario settled state mismatch: expected 'edit', got '{scenario_state or '<empty>'}'")
if direct_state != scenario_state:
    raise SystemExit(f"settled state mismatch between direct and scenario responses: direct='{direct_state}', scenario='{scenario_state}'")

summary = {
    "direct_status": direct_payload.get("status"),
    "direct_settled_state": direct_state,
    "scenario_status": scenario.get("status"),
    "scenario_step_status": playmode_step.get("status"),
    "scenario_settled_state": scenario_state,
}
print(json.dumps(summary, ensure_ascii=True))
PY

"$WRAPPER" request-status-summary \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000 >"$TMP_DIR/final_status.json" || fail_step "final_status"

echo "[pass] playmode-settled-state direct=scenario=edit"
