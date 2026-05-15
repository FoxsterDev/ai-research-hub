#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WRAPPER="$OPS_ROOT/xuunity_light_unity_mcp.sh"

PROJECT_ROOT=""
OPEN_EDITOR="true"
RESTORE_EDITOR_STATE="true"
REQUEST_TIMEOUT_MS="30000"
PASS_TIMEOUT_MS="240000"
SCENARIO_TIMEOUT_MS="3000"
POLL_INTERVAL_MS="5000"
TMP_DIR=""
LAST_OUTPUT_FILE=""
GENERATED_ROOT=""
GENERATED_DIR=""

ASSEMBLY_NAME="XUUnity.LightMcp.Generated.PlayModeVerdictRecoveryProof.Tests"
PASS_CATEGORY="XUUnity.MCP.VerdictProof.Pass"
TIMEOUT_CATEGORY="XUUnity.MCP.VerdictProof.Timeout"

usage() {
  cat <<'EOF'
Usage:
  run_playmode_verdict_recovery_proof_suite.sh \
    --project-root /path/to/UnityProject \
    [--request-timeout-ms 30000] \
    [--pass-timeout-ms 240000] \
    [--scenario-timeout-ms 3000] \
    [--poll-interval-ms 5000] \
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
    --request-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--request-timeout-ms requires a value"
      REQUEST_TIMEOUT_MS="$1"
      ;;
    --pass-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--pass-timeout-ms requires a value"
      PASS_TIMEOUT_MS="$1"
      ;;
    --scenario-timeout-ms)
      shift
      [[ $# -gt 0 ]] || fail_usage "--scenario-timeout-ms requires a value"
      SCENARIO_TIMEOUT_MS="$1"
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
TMP_DIR="$(mktemp -d)"

cleanup() {
  if [[ -n "$GENERATED_DIR" && -d "$GENERATED_DIR" ]]; then
    rm -rf "$GENERATED_DIR"
  fi
  if [[ -n "$GENERATED_DIR" && -f "$GENERATED_DIR.meta" ]]; then
    rm -f "$GENERATED_DIR.meta"
  fi
  if [[ -n "$GENERATED_ROOT" && -d "$GENERATED_ROOT" ]] && [[ -z "$(find "$GENERATED_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    rmdir "$GENERATED_ROOT" || true
  fi
  if [[ -n "$GENERATED_ROOT" && ! -d "$GENERATED_ROOT" && -f "$GENERATED_ROOT.meta" ]]; then
    rm -f "$GENERATED_ROOT.meta"
  fi
  if [[ -n "$GENERATED_ROOT" || -n "$GENERATED_DIR" ]]; then
    "$WRAPPER" request-project-refresh \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 180000 >/dev/null 2>&1 || true
  fi
  if [[ "$RESTORE_EDITOR_STATE" == "true" ]]; then
    "$WRAPPER" restore-editor-state \
      --project-root "$PROJECT_ROOT" \
      --timeout-ms 60000 >/dev/null 2>&1 || true
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

run_capture_allow_error() {
  local output_file="$1"
  shift
  "$@" >"$output_file" 2>&1
  return $?
}

echo "[mcp-verdict-proof] project_root=$PROJECT_ROOT"
GENERATED_ROOT="$PROJECT_ROOT/Assets/XUUnityLightMcpGenerated"
GENERATED_DIR="$GENERATED_ROOT/PlayModeVerdictRecoveryProof"

ensure_ready_cmd=(
  "$WRAPPER" ensure-ready
  --project-root "$PROJECT_ROOT"
  --timeout-ms 300000
)
if [[ "$OPEN_EDITOR" == "true" ]]; then
  ensure_ready_cmd+=(--open-editor)
fi
"${ensure_ready_cmd[@]}" >"$TMP_DIR/ensure_ready.json" || fail_step "ensure_ready"

rm -rf "$GENERATED_DIR"
mkdir -p "$GENERATED_DIR"
cat >"$GENERATED_DIR/XUUnityLightMcpGeneratedPlayModeVerdictRecoveryProof.Tests.asmdef" <<'EOF'
{
  "name": "XUUnity.LightMcp.Generated.PlayModeVerdictRecoveryProof.Tests",
  "rootNamespace": "XUUnity.LightMcp.Generated.PlayModeVerdictRecoveryProof",
  "references": [
    "UnityEngine.TestRunner",
    "UnityEditor.TestRunner"
  ],
  "includePlatforms": [],
  "excludePlatforms": [],
  "allowUnsafeCode": false,
  "overrideReferences": false,
  "precompiledReferences": [],
  "autoReferenced": false,
  "defineConstraints": [
    "UNITY_INCLUDE_TESTS"
  ],
  "versionDefines": [],
  "noEngineReferences": false
}
EOF

cat >"$GENERATED_DIR/XUUnityLightMcpGeneratedPlayModeVerdictRecoveryProofTests.cs" <<'EOF'
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace XUUnity.LightMcp.Generated.PlayModeVerdictRecoveryProof
{
    [Category("XUUnity.MCP.VerdictProof")]
    public sealed class XUUnityLightMcpGeneratedPlayModeVerdictRecoveryProofTests
    {
        [UnityTest]
        [Category("XUUnity.MCP.VerdictProof.Pass")]
        public IEnumerator PassingCoroutine_ProducesCompactVerdictEvidence()
        {
            yield return null;

            Assert.That(Time.frameCount, Is.GreaterThanOrEqualTo(0));
        }

        [UnityTest]
        [Category("XUUnity.MCP.VerdictProof.Timeout")]
        public IEnumerator StartedCoroutine_RunsLongEnoughForRuntimeTimeoutProof()
        {
            yield return null;

            var deadline = Time.realtimeSinceStartup + 90.0f;
            while (Time.realtimeSinceStartup < deadline)
            {
                yield return null;
            }

            Assert.Pass();
        }
    }
}
EOF

"$WRAPPER" request-project-refresh \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 180000 >"$TMP_DIR/project_refresh.json" || fail_step "project_refresh"

LAST_OUTPUT_FILE="$TMP_DIR/pass_playmode.json"
"$WRAPPER" request-playmode-tests \
  --project-root "$PROJECT_ROOT" \
  --assembly-name "$ASSEMBLY_NAME" \
  --category-name "$PASS_CATEGORY" \
  --timeout-ms "$PASS_TIMEOUT_MS" >"$LAST_OUTPUT_FILE" 2>&1 || fail_step "pass_playmode"

python3 - "$LAST_OUTPUT_FILE" <<'PY' || fail_step "pass_playmode_parse"
import json
import sys
from pathlib import Path

def load_json_candidates(path: Path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise SystemExit(f"No JSON object found in {path}")
    return candidates

candidates = load_json_candidates(Path(sys.argv[1]))
payload = next((item for item in reversed(candidates) if item.get("payload_json") and item.get("payload_type") == "unity.tests.run_playmode"), None)
if payload is None:
    raise SystemExit("passing PlayMode request did not expose a top-level test response")
if payload.get("status") != "ok":
    raise SystemExit("passing PlayMode request did not return status=ok")
decoded = json.loads(payload.get("payload_json") or "{}")
if decoded.get("test_verdict") != "passed":
    raise SystemExit(f"expected test_verdict=passed, got {decoded.get('test_verdict')!r}")
if int(decoded.get("total") or 0) < 1:
    raise SystemExit("passing PlayMode request did not include test counts")
if not bool(decoded.get("result_payload_available")):
    raise SystemExit("passing PlayMode request did not report result_payload_available=true")
if decoded.get("result_payload_source") not in {"response_payload", "persisted_test_result"}:
    raise SystemExit(f"unexpected result_payload_source={decoded.get('result_payload_source')!r}")
print(json.dumps({
    "pass_request_id": payload.get("request_id", ""),
    "test_verdict": decoded.get("test_verdict", ""),
    "total": decoded.get("total", 0),
    "result_payload_source": decoded.get("result_payload_source", ""),
}, ensure_ascii=True))
PY

SCENARIO_FILE="$TMP_DIR/verdict_proof_scenario.json"
python3 - "$SCENARIO_FILE" "$ASSEMBLY_NAME" "$PASS_CATEGORY" <<'PY'
import json
import sys
from pathlib import Path

scenario_path = Path(sys.argv[1])
assembly_name = sys.argv[2]
category_name = sys.argv[3]
scenario = {
    "name": "playmode_verdict_recovery_proof_scenario",
    "description": "Force scenario polling to reconcile a terminal persisted result after timeout.",
    "stopOnFirstFailure": True,
    "steps": [
        {
            "stepId": "proof_pass_playmode",
            "kind": "tests_run_playmode",
            "assemblyNames": [assembly_name],
            "categoryNames": [category_name],
            "timeoutSeconds": 60.0,
        }
    ],
}
scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
PY

LAST_OUTPUT_FILE="$TMP_DIR/scenario_reconciliation.json"
"$WRAPPER" request-scenario-run-and-wait \
  --project-root "$PROJECT_ROOT" \
  --scenario-file "$SCENARIO_FILE" \
  --timeout-ms "$SCENARIO_TIMEOUT_MS" \
  --poll-interval-ms "$POLL_INTERVAL_MS" >"$LAST_OUTPUT_FILE" 2>&1 || fail_step "scenario_reconciliation"

python3 - "$LAST_OUTPUT_FILE" <<'PY' || fail_step "scenario_reconciliation_parse"
import json
import sys
from pathlib import Path

def load_json_candidates(path: Path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise SystemExit(f"No JSON object found in {path}")
    return candidates

candidates = load_json_candidates(Path(sys.argv[1]))
payload = next((item for item in reversed(candidates) if item.get("scenario_result_reconciled_from_persisted")), None)
if payload is None:
    raise SystemExit("scenario reconciliation did not expose a persisted terminal reconciliation payload")
if payload.get("status") != "passed":
    raise SystemExit(f"expected scenario status=passed, got {payload.get('status')!r}")
if not bool(payload.get("scenario_result_reconciled_from_persisted")):
    raise SystemExit("scenario did not report persisted-result reconciliation")
if payload.get("scenario_result_reconciliation_reason") != "terminal_persisted_result_after_poll_timeout":
    raise SystemExit(
        "unexpected scenario reconciliation reason: "
        f"{payload.get('scenario_result_reconciliation_reason')!r}"
    )
if not payload.get("result_path"):
    raise SystemExit("scenario reconciliation did not include result_path")
print(json.dumps({
    "scenario_status": payload.get("status", ""),
    "result_path": payload.get("result_path", ""),
    "reconciliation_reason": payload.get("scenario_result_reconciliation_reason", ""),
}, ensure_ascii=True))
PY

TIMEOUT_OUTPUT="$TMP_DIR/runtime_timeout_request.json"
LAST_OUTPUT_FILE="$TIMEOUT_OUTPUT"
echo "[mcp-verdict-proof] starting runtime-timeout request"
set +e
run_capture_allow_error "$TIMEOUT_OUTPUT" \
  "$WRAPPER" request-playmode-tests \
    --project-root "$PROJECT_ROOT" \
    --assembly-name "$ASSEMBLY_NAME" \
    --category-name "$TIMEOUT_CATEGORY" \
    --timeout-ms "$REQUEST_TIMEOUT_MS"
TIMEOUT_RC=$?
set -e
echo "[mcp-verdict-proof] runtime-timeout request rc=$TIMEOUT_RC"

python3 - "$TIMEOUT_OUTPUT" "$TIMEOUT_RC" "$TMP_DIR/runtime_timeout_plan.json" <<'PY' || fail_step "runtime_timeout_request_parse"
import json
import sys
from pathlib import Path

def load_json_candidates(path: Path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise SystemExit(f"No JSON object found in {path}")
    return candidates

candidates = load_json_candidates(Path(sys.argv[1]))
payload = next((item for item in reversed(candidates) if item.get("request_id") and (item.get("payload_json") or item.get("error"))), None)
if payload is None:
    raise SystemExit("runtime timeout request did not expose a top-level response")
rc = int(sys.argv[2])
plan_path = Path(sys.argv[3])
request_id = str(payload.get("request_id") or "")
error = payload.get("error") or {}
details = error.get("details") or {}
final_status = details.get("request_final_status") or {}
request_id = request_id or str(details.get("request_id") or final_status.get("request_id") or "")
if not request_id:
    raise SystemExit("runtime timeout request did not expose a request_id")
if rc == 0:
    decoded = json.loads(payload.get("payload_json") or "{}")
    if decoded.get("test_verdict") != "runtime_timeout":
        raise SystemExit("runtime timeout proof unexpectedly completed without runtime_timeout")
plan_path.write_text(json.dumps({"request_id": request_id}, indent=2), encoding="utf-8")
print(json.dumps({"timeout_request_id": request_id, "request_rc": rc}, ensure_ascii=True))
PY

TIMEOUT_REQUEST_ID="$(python3 - "$TMP_DIR/runtime_timeout_plan.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("request_id", ""))
PY
)" || fail_step "runtime_timeout_plan_read"
echo "[mcp-verdict-proof] runtime-timeout request_id=$TIMEOUT_REQUEST_ID"

LAST_OUTPUT_FILE="$TMP_DIR/runtime_timeout_final_status.json"
"$WRAPPER" request-final-status \
  --project-root "$PROJECT_ROOT" \
  --request-id "$TIMEOUT_REQUEST_ID" \
  --timeout-ms 15000 >"$LAST_OUTPUT_FILE" 2>&1 || fail_step "runtime_timeout_final_status"

python3 - "$LAST_OUTPUT_FILE" <<'PY' || fail_step "runtime_timeout_final_status_parse"
import json
import sys
from pathlib import Path

def load_json_candidates(path: Path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise SystemExit(f"No JSON object found in {path}")
    return candidates

candidates = load_json_candidates(Path(sys.argv[1]))
payload = next((item for item in reversed(candidates) if item.get("test_verdict") or item.get("result_trust_class")), None)
if payload is None:
    raise SystemExit("request-final-status did not expose a final status payload")
if payload.get("test_verdict") != "runtime_timeout":
    raise SystemExit(f"expected test_verdict=runtime_timeout, got {payload.get('test_verdict')!r}")
if payload.get("timeout_classification") != "runtime_timeout_after_test_start":
    raise SystemExit(
        "expected timeout_classification=runtime_timeout_after_test_start, "
        f"got {payload.get('timeout_classification')!r}"
    )
if not (payload.get("last_started_test") or payload.get("last_progress_at_utc")):
    raise SystemExit("runtime timeout proof did not include started/progress evidence")
if int(payload.get("runtime_timeout_ms") or 0) <= 0:
    raise SystemExit("runtime timeout proof did not include runtime_timeout_ms")
if not bool(payload.get("editor_cleanup_recommended")):
    raise SystemExit("runtime timeout proof did not recommend editor cleanup")
if "request-playmode-set" not in str(payload.get("cleanup_command") or ""):
    raise SystemExit("runtime timeout proof did not include request-playmode-set cleanup command")
if "--action exit" not in str(payload.get("cleanup_command") or ""):
    raise SystemExit("runtime timeout proof cleanup command did not request playmode exit")
print(json.dumps({
    "test_verdict": payload.get("test_verdict", ""),
    "timeout_classification": payload.get("timeout_classification", ""),
    "last_started_test": payload.get("last_started_test", ""),
    "last_progress_at_utc": payload.get("last_progress_at_utc", ""),
    "runtime_timeout_ms": payload.get("runtime_timeout_ms", 0),
    "editor_cleanup_recommended": payload.get("editor_cleanup_recommended", False),
    "cleanup_command": payload.get("cleanup_command", ""),
}, ensure_ascii=True))
PY

"$WRAPPER" request-playmode-set \
  --project-root "$PROJECT_ROOT" \
  --action exit \
  --timeout-ms 60000 >"$TMP_DIR/restore_after_timeout.json" || fail_step "restore_after_timeout"

LAST_OUTPUT_FILE="$TMP_DIR/final_status_summary.json"
"$WRAPPER" request-status-summary \
  --project-root "$PROJECT_ROOT" \
  --timeout-ms 15000 >"$LAST_OUTPUT_FILE" 2>&1 || fail_step "final_status_summary"

python3 - "$LAST_OUTPUT_FILE" <<'PY' || fail_step "final_status_summary_parse"
import json
import sys
from pathlib import Path

def load_json_candidates(path: Path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise SystemExit(f"No JSON object found in {path}")
    return candidates

candidates = load_json_candidates(Path(sys.argv[1]))
payload = next((item for item in reversed(candidates) if item.get("action") == "unity_status_summary"), None)
if payload is None:
    raise SystemExit("status-summary did not expose a top-level summary payload")
if payload.get("health_status") != "healthy":
    raise SystemExit(f"expected final health_status=healthy, got {payload.get('health_status')!r}")
if payload.get("playmode_state") != "edit":
    raise SystemExit(f"expected final playmode_state=edit, got {payload.get('playmode_state')!r}")
print(json.dumps({
    "final_health_status": payload.get("health_status", ""),
    "final_playmode_state": payload.get("playmode_state", ""),
    "transport": payload.get("transport", ""),
}, ensure_ascii=True))
PY

echo "[pass] playmode-verdict-recovery-proof-suite"
