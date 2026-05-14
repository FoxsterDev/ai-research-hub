#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AIROOT_PATH="${XUUNITY_LIGHT_UNITY_MCP_AIRROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
if [[ -n "${XUUNITY_LIGHT_UNITY_MCP_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "$XUUNITY_LIGHT_UNITY_MCP_REPO_ROOT" && pwd)"
elif [[ -d "$AIROOT_PATH/../AIOutput" || -d "$AIROOT_PATH/../AIModules" ]]; then
  REPO_ROOT="$(cd "$AIROOT_PATH/.." && pwd)"
else
  REPO_ROOT="$(pwd)"
fi
WRAPPER_PATH="${XUUNITY_LIGHT_UNITY_MCP_WRAPPER:-$SCRIPT_DIR/xuunity_light_unity_mcp.sh}"
ARRANGE_SCRIPT_PATH="${XUUNITY_LIGHT_UNITY_MCP_ARRANGE_SCRIPT:-$AIROOT_PATH/Operations/XUUnityLightUnityMcp/arrange_unity_windows.py}"

PARALLELISM=3
STARTUP_POLICY="fail_fast_on_interactive_compile_block"
BATCH_RESULTS_DIR=""
KEEP_RESULTS="true"
RESULTS_DIR=""
PROJECT_ROOTS=()
WINDOW_ARRANGEMENT="auto"

usage() {
  cat <<'EOF'
Usage:
  run_multi_project_gui_test_subset.sh [options]

Options:
  --from-batch-results DIR  Read *_status.json files from a previous batch runner results dir and select only green projects.
  --repo-root PATH          Root containing Unity project directories. Defaults to env or current repo layout.
  --project-root PATH       Include one explicit Unity project root. Repeatable.
  --parallelism N           Number of concurrent GUI workers. Default: 3
  --startup-policy VALUE    ensure-ready startup policy. Default: fail_fast_on_interactive_compile_block
  --window-arrangement MODE Unity window arrangement policy: auto, off, required. Default: auto
  --results-dir DIR         Write status artifacts to a persistent directory.
  --cleanup-results         Remove the results dir on exit instead of keeping it.
  --help                    Show this message.

Behavior:
  - selects a GUI-test subset from explicit project roots, a prior batch results dir, or auto-discovery
  - runs recover -> ensure-ready -> editmode -> playmode -> restore for each project
  - keeps editmode and playmode strictly sequential inside each project
  - emits one compact per-project summary plus a final aggregate summary
  - keeps results_dir by default for follow-up inspection
EOF
}

resolve_project_root() {
  local candidate="$1"
  if [[ ! -d "$candidate" ]]; then
    candidate="$REPO_ROOT/$candidate"
  fi
  if [[ ! -d "$candidate" ]]; then
    echo "Project root not found: $1" >&2
    exit 1
  fi
  python3 - "$candidate" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
}

warn_ripgrep_fallback_once() {
  if [[ "${XUUNITY_LIGHT_UNITY_MCP_RG_FALLBACK_WARNED:-false}" == "true" ]]; then
    return 0
  fi
  echo "optional command not found: rg; using grep fallback. Install ripgrep for faster local checks: brew install ripgrep" >&2
  XUUNITY_LIGHT_UNITY_MCP_RG_FALLBACK_WARNED="true"
}

manifest_declares_light_mcp() {
  local manifest_path="$1"
  if command -v rg >/dev/null 2>&1; then
    rg -q '"com\.xuunity\.light-mcp"' "$manifest_path"
  else
    warn_ripgrep_fallback_once
    grep -Eq '"com\.xuunity\.light-mcp"' "$manifest_path"
  fi
}

discover_project_roots() {
  local child_dir=""
  for child_dir in "$REPO_ROOT"/*; do
    [[ -d "$child_dir" ]] || continue
    [[ -f "$child_dir/Packages/manifest.json" ]] || continue
    [[ -f "$child_dir/ProjectSettings/ProjectVersion.txt" ]] || continue
    if manifest_declares_light_mcp "$child_dir/Packages/manifest.json"; then
      printf '%s\n' "$child_dir"
    fi
  done | sort
}

collect_green_projects_from_batch_results() {
  local results_dir="$1"
  python3 - "$results_dir" <<'PY'
import json
import sys
from pathlib import Path

results_dir = Path(sys.argv[1])
if not results_dir.is_dir():
    raise SystemExit(f"Batch results dir not found: {results_dir}")

for status_path in sorted(results_dir.glob("*_status.json")):
    try:
        item = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    ok = (
        item.get("recover_rc", 0) == 0
        and item.get("batch_rc", 0) == 0
        and item.get("succeeded") is True
        and item.get("matrix_status") == "passed"
        and int(item.get("failed", 0)) == 0
    )
    if ok and item.get("project_root"):
        print(item["project_root"])
PY
}

run_json_command() {
  local stdout_file="$1"
  local stderr_file="$2"
  shift 2
  local cmd_rc=0
  if "$@" >"$stdout_file" 2>"$stderr_file"; then
    cmd_rc=0
  else
    cmd_rc=$?
  fi

  if [[ "$cmd_rc" -eq 0 ]]; then
    if ! python3 - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

error = payload.get("error") or {}
status = str(payload.get("status") or "")
code = str(error.get("code") or "")
raise SystemExit(70 if code or status == "error" else 0)
PY
    then
      cmd_rc=$?
    fi
  fi

  return "$cmd_rc"
}

should_retry_after_lifecycle_reset() {
  local stdout_file="$1"
  python3 - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(1)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

error = payload.get("error") or {}
details = error.get("details") or {}
if str(error.get("code") or "") != "request_lifecycle_reset":
    raise SystemExit(1)

final_status = details.get("request_final_status") or {}
bridge_stabilization = details.get("bridge_stabilization") or final_status.get("bridge_stabilization") or {}
retryable = bool(details.get("retryable"))
recommended_next_action = str(final_status.get("recommended_next_action") or details.get("recommended_next_action") or "")
safe_to_retry = bool(bridge_stabilization.get("safe_to_retry"))

raise SystemExit(0 if retryable and safe_to_retry and recommended_next_action == "retry_request" else 1)
PY
}

should_retry_after_tests_busy() {
  local stdout_file="$1"
  python3 - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(1)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

error = payload.get("error") or {}
raise SystemExit(0 if str(error.get("code") or "") == "tests_busy" else 1)
PY
}

extract_error_code() {
  local stdout_file="$1"
  python3 - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    print("")
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

error = payload.get("error") or {}
print(str(error.get("code") or ""))
PY
}

extract_result_trust_class() {
  local stdout_file="$1"
  python3 - "$stdout_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    print("")
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

error = payload.get("error") or {}
details = error.get("details") or {}
final_status = details.get("request_final_status") or {}
if payload.get("result_trust_class"):
    print(str(payload.get("result_trust_class") or ""))
elif details.get("result_trust_class"):
    print(str(details.get("result_trust_class") or ""))
elif final_status.get("result_trust_class"):
    print(str(final_status.get("result_trust_class") or ""))
else:
    print("")
PY
}

run_json_command_with_lifecycle_retry() {
  local stdout_file="$1"
  local stderr_file="$2"
  shift 2
  local cmd_rc=0

  run_json_command "$stdout_file" "$stderr_file" "$@" || cmd_rc=$?
  if should_retry_after_lifecycle_reset "$stdout_file"; then
    printf '\n[xuunity-multi-project-gui] retrying after lifecycle reset attempt=1/1 trust_class=%s\n' \
      "$(extract_result_trust_class "$stdout_file")" >>"$stderr_file"
    sleep 2
    cmd_rc=0
    run_json_command "$stdout_file" "$stderr_file" "$@" || cmd_rc=$?
    if [[ "$cmd_rc" -ne 0 ]]; then
      printf '[xuunity-multi-project-gui] retry budget exhausted retry_kind=lifecycle_reset final_code=%s trust_class=%s\n' \
        "$(extract_error_code "$stdout_file")" "$(extract_result_trust_class "$stdout_file")" >>"$stderr_file"
    fi
  elif should_retry_after_tests_busy "$stdout_file"; then
    printf '\n[xuunity-multi-project-gui] retrying after tests_busy attempt=1/1\n' >>"$stderr_file"
    sleep 3
    cmd_rc=0
    run_json_command "$stdout_file" "$stderr_file" "$@" || cmd_rc=$?
    if [[ "$cmd_rc" -ne 0 ]]; then
      printf '[xuunity-multi-project-gui] retry budget exhausted retry_kind=tests_busy final_code=%s trust_class=%s\n' \
        "$(extract_error_code "$stdout_file")" "$(extract_result_trust_class "$stdout_file")" >>"$stderr_file"
    fi
  fi

  return "$cmd_rc"
}

arrange_windows_best_effort() {
  local stdout_file="$1"
  local stderr_file="$2"
  local editor_pid="$3"
  local mode="$4"
  local cmd_rc=0

  if [[ "$mode" == "off" ]]; then
    printf '{\n  "applied": false,\n  "reason": "window_arrangement_off"\n}\n' >"$stdout_file"
    : >"$stderr_file"
    return 0
  fi

  if [[ "$mode" == "required" ]]; then
    if ! python3 "$ARRANGE_SCRIPT_PATH" \
      --include-all-running \
      --focus-pid "$editor_pid" \
      --required >"$stdout_file" 2>"$stderr_file"; then
      cmd_rc=$?
    fi
  else
    if ! python3 "$ARRANGE_SCRIPT_PATH" \
      --include-all-running \
      --focus-pid "$editor_pid" >"$stdout_file" 2>"$stderr_file"; then
      cmd_rc=$?
    fi
  fi
  return "$cmd_rc"
}

run_worker() {
  local results_dir="$1"
  local startup_policy="$2"
  local window_arrangement="$3"
  local project_root="$4"
  local project_name
  project_name="$(basename "$project_root")"
  local worker_prefix="$results_dir/$project_name"

  local recover_stdout="${worker_prefix}_recover_stdout.json"
  local recover_stderr="${worker_prefix}_recover_stderr.log"
  local ensure_stdout="${worker_prefix}_ensure_stdout.json"
  local ensure_stderr="${worker_prefix}_ensure_stderr.log"
  local edit_stdout="${worker_prefix}_edit_stdout.json"
  local edit_stderr="${worker_prefix}_edit_stderr.log"
  local play_stdout="${worker_prefix}_play_stdout.json"
  local play_stderr="${worker_prefix}_play_stderr.log"
  local arrange_stdout="${worker_prefix}_arrange_stdout.json"
  local arrange_stderr="${worker_prefix}_arrange_stderr.log"
  local restore_stdout="${worker_prefix}_restore_stdout.json"
  local restore_stderr="${worker_prefix}_restore_stderr.log"
  local status_file="${worker_prefix}_status.json"

  local recover_rc=0
  local ensure_rc=0
  local edit_rc=0
  local play_rc=0
  local arrange_rc=0
  local restore_rc=0
  local edit_retry_attempted="false"
  local play_retry_attempted="false"

  run_json_command "$recover_stdout" "$recover_stderr" \
    "$WRAPPER_PATH" recover-editor-session --project-root "$project_root" || recover_rc=$?

  run_json_command "$ensure_stdout" "$ensure_stderr" \
    "$WRAPPER_PATH" ensure-ready --project-root "$project_root" --open-editor --background-open --startup-policy "$startup_policy" || ensure_rc=$?

  local ensure_editor_pid=0
  if [[ "$ensure_rc" -eq 0 ]]; then
    ensure_editor_pid="$(python3 - "$ensure_stdout" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.is_file():
    print(0)
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit(0)
print(int((payload.get("launch") or {}).get("editor_pid") or 0))
PY
)"
    arrange_windows_best_effort "$arrange_stdout" "$arrange_stderr" "$ensure_editor_pid" "$window_arrangement" || arrange_rc=$?
  fi

  if [[ "$ensure_rc" -eq 0 ]]; then
    run_json_command_with_lifecycle_retry "$edit_stdout" "$edit_stderr" \
      "$WRAPPER_PATH" request-editmode-tests --project-root "$project_root" || edit_rc=$?
    if grep -q 'retrying after lifecycle reset' "$edit_stderr" 2>/dev/null; then
      edit_retry_attempted="true"
    fi
  fi

  if [[ "$ensure_rc" -eq 0 && "$edit_rc" -eq 0 ]]; then
    run_json_command_with_lifecycle_retry "$play_stdout" "$play_stderr" \
      "$WRAPPER_PATH" request-playmode-tests --project-root "$project_root" || play_rc=$?
    if grep -q 'retrying after lifecycle reset' "$play_stderr" 2>/dev/null; then
      play_retry_attempted="true"
    fi
  fi

  run_json_command "$restore_stdout" "$restore_stderr" \
    "$WRAPPER_PATH" restore-editor-state --project-root "$project_root" || restore_rc=$?

  python3 - \
    "$project_name" "$project_root" "$status_file" \
    "$recover_stdout" "$recover_stderr" "$recover_rc" \
    "$ensure_stdout" "$ensure_stderr" "$ensure_rc" \
    "$edit_stdout" "$edit_stderr" "$edit_rc" \
    "$play_stdout" "$play_stderr" "$play_rc" \
    "$arrange_stdout" "$arrange_stderr" "$arrange_rc" \
    "$restore_stdout" "$restore_stderr" "$restore_rc" \
    "$edit_retry_attempted" "$play_retry_attempted" <<'PY'
import json
import sys
from pathlib import Path

project_name = sys.argv[1]
project_root = sys.argv[2]
status_file = Path(sys.argv[3])

recover_stdout = Path(sys.argv[4]); recover_stderr = Path(sys.argv[5]); recover_rc = int(sys.argv[6])
ensure_stdout = Path(sys.argv[7]); ensure_stderr = Path(sys.argv[8]); ensure_rc = int(sys.argv[9])
edit_stdout = Path(sys.argv[10]); edit_stderr = Path(sys.argv[11]); edit_rc = int(sys.argv[12])
play_stdout = Path(sys.argv[13]); play_stderr = Path(sys.argv[14]); play_rc = int(sys.argv[15])
arrange_stdout = Path(sys.argv[16]); arrange_stderr = Path(sys.argv[17]); arrange_rc = int(sys.argv[18])
restore_stdout = Path(sys.argv[19]); restore_stderr = Path(sys.argv[20]); restore_rc = int(sys.argv[21])
edit_retry_attempted = str(sys.argv[22]).lower() == "true"
play_retry_attempted = str(sys.argv[23]).lower() == "true"

def load_json(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        return {}, ""
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except Exception as exc:
        return {}, str(exc)

def stderr_tail(path: Path) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-20:])

recover_payload, recover_parse_error = load_json(recover_stdout)
ensure_payload, ensure_parse_error = load_json(ensure_stdout)
edit_payload, edit_parse_error = load_json(edit_stdout)
play_payload, play_parse_error = load_json(play_stdout)
restore_payload, restore_parse_error = load_json(restore_stdout)
arrange_payload, arrange_parse_error = load_json(arrange_stdout)

def decode_embedded_json(payload: dict) -> dict:
    raw = payload.get("payload_json")
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}

edit_decoded = decode_embedded_json(edit_payload)
play_decoded = decode_embedded_json(play_payload)

acceptable_test_statuses = {"passed", "no_tests"}
edit_status = str(edit_decoded.get("status", ""))
play_status = str(play_decoded.get("status", ""))

ok = (
    recover_rc == 0
    and ensure_rc == 0
    and edit_rc == 0
    and play_rc == 0
    and restore_rc == 0
    and arrange_rc == 0
    and edit_status in acceptable_test_statuses
    and play_status in acceptable_test_statuses
    and bool(restore_payload.get("closeout_verified")) is True
)

status = {
    "project": project_name,
    "project_root": project_root,
    "recover_rc": recover_rc,
    "recover_parse_error": recover_parse_error,
    "recover_recommended_next_action": recover_payload.get("recommended_next_action", ""),
    "ensure_rc": ensure_rc,
    "ensure_parse_error": ensure_parse_error,
    "ensure_health": ensure_payload.get("bridge_state", {}).get("health_status", ""),
    "ensure_editor_pid": int(ensure_payload.get("launch", {}).get("editor_pid", 0) or 0),
    "edit_rc": edit_rc,
    "edit_parse_error": edit_parse_error,
    "edit_status": edit_status,
    "edit_total": int(edit_decoded.get("total", 0) or 0),
    "edit_passed": int(edit_decoded.get("passed", 0) or 0),
    "edit_failed": int(edit_decoded.get("failed", 0) or 0),
    "edit_retry_attempted": edit_retry_attempted,
    "edit_error_code": str((edit_payload.get("error") or {}).get("code") or ""),
    "edit_result_trust_class": (
        str((edit_payload.get("error") or {}).get("details", {}).get("request_final_status", {}).get("result_trust_class") or "")
        or str((edit_payload.get("error") or {}).get("details", {}).get("result_trust_class") or "")
        or ("unity_completed_confirmed" if edit_status in acceptable_test_statuses else "")
    ),
    "edit_retry_budget_total": 1,
    "edit_retry_budget_consumed": 1 if edit_retry_attempted else 0,
    "edit_retry_budget_exhausted": bool(edit_retry_attempted and edit_rc != 0),
    "play_rc": play_rc,
    "play_parse_error": play_parse_error,
    "play_status": play_status,
    "play_total": int(play_decoded.get("total", 0) or 0),
    "play_passed": int(play_decoded.get("passed", 0) or 0),
    "play_failed": int(play_decoded.get("failed", 0) or 0),
    "play_retry_attempted": play_retry_attempted,
    "play_error_code": str((play_payload.get("error") or {}).get("code") or ""),
    "play_result_trust_class": (
        str((play_payload.get("error") or {}).get("details", {}).get("request_final_status", {}).get("result_trust_class") or "")
        or str((play_payload.get("error") or {}).get("details", {}).get("result_trust_class") or "")
        or ("unity_completed_confirmed" if play_status in acceptable_test_statuses else "")
    ),
    "play_retry_budget_total": 1,
    "play_retry_budget_consumed": 1 if play_retry_attempted else 0,
    "play_retry_budget_exhausted": bool(play_retry_attempted and play_rc != 0),
    "arrange_rc": arrange_rc,
    "arrange_parse_error": arrange_parse_error,
    "arrange_applied": bool(arrange_payload.get("applied")),
    "arrange_reason": arrange_payload.get("reason", ""),
    "restore_rc": restore_rc,
    "restore_parse_error": restore_parse_error,
    "closeout_verified": bool(restore_payload.get("closeout_verified")),
    "closeout_classification": restore_payload.get("closeout_classification", ""),
    "live_project_editor_pids": restore_payload.get("live_project_editor_pids", []),
    "succeeded": ok,
    "stderr_tails": {
        "recover": stderr_tail(recover_stderr),
        "ensure": stderr_tail(ensure_stderr),
        "edit": stderr_tail(edit_stderr),
        "play": stderr_tail(play_stderr),
        "arrange": stderr_tail(arrange_stderr),
        "restore": stderr_tail(restore_stderr),
    },
}

status_file.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
PY
}

emit_final_summary() {
  local results_dir="$1"
  python3 - "$results_dir" <<'PY'
import json
import sys
from pathlib import Path

results_dir = Path(sys.argv[1])
status_files = sorted(results_dir.glob("*_status.json"))
statuses = [json.loads(path.read_text(encoding="utf-8")) for path in status_files]

print("MULTI_PROJECT_GUI_TEST_SUBSET_SUMMARY_BEGIN")
overall_failed = 0
for item in statuses:
    ok = bool(item.get("succeeded"))
    if not ok:
        overall_failed += 1
    fields = [
        item.get("project", ""),
        f"recover_rc={item.get('recover_rc', 0)}",
        f"ensure_rc={item.get('ensure_rc', 0)}",
        f"ensure_health={item.get('ensure_health', '')}",
        f"edit_rc={item.get('edit_rc', 0)}",
        f"edit_status={item.get('edit_status', '')}",
        f"edit_trust={item.get('edit_result_trust_class', '')}",
        f"edit_retry_exhausted={str(bool(item.get('edit_retry_budget_exhausted'))).lower()}",
        f"edit_total={item.get('edit_total', 0)}",
        f"play_rc={item.get('play_rc', 0)}",
        f"play_status={item.get('play_status', '')}",
        f"play_trust={item.get('play_result_trust_class', '')}",
        f"play_retry_exhausted={str(bool(item.get('play_retry_budget_exhausted'))).lower()}",
        f"play_total={item.get('play_total', 0)}",
        f"arrange_rc={item.get('arrange_rc', 0)}",
        f"arrange_applied={str(bool(item.get('arrange_applied'))).lower()}",
        f"restore_rc={item.get('restore_rc', 0)}",
        f"closeout_verified={str(bool(item.get('closeout_verified'))).lower()}",
        f"succeeded={str(ok).lower()}",
    ]
    print("|".join(fields))
print("MULTI_PROJECT_GUI_TEST_SUBSET_SUMMARY_END")

aggregate = {
    "projects_total": len(statuses),
    "projects_failed": overall_failed,
    "results_dir": str(results_dir),
}
print(json.dumps(aggregate, indent=2))
if overall_failed:
    raise SystemExit(1)
PY
}

if [[ "${1:-}" == "__worker__" ]]; then
  run_worker "$2" "$3" "$4" "$5"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-batch-results)
      BATCH_RESULTS_DIR="$2"
      shift 2
      ;;
    --repo-root)
      REPO_ROOT="$(cd "${2:-}" && pwd)"
      shift 2
      ;;
    --project-root)
      PROJECT_ROOTS+=("$(resolve_project_root "${2:-}")")
      shift 2
      ;;
    --parallelism)
      PARALLELISM="${2:-}"
      shift 2
      ;;
    --startup-policy)
      STARTUP_POLICY="${2:-}"
      shift 2
      ;;
    --window-arrangement)
      WINDOW_ARRANGEMENT="${2:-}"
      shift 2
      ;;
    --results-dir)
      RESULTS_DIR="$2"
      shift 2
      ;;
    --cleanup-results)
      KEEP_RESULTS="false"
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! "$PARALLELISM" =~ ^[0-9]+$ ]] || [[ "$PARALLELISM" -lt 1 ]]; then
  echo "parallelism must be a positive integer" >&2
  exit 1
fi

case "$WINDOW_ARRANGEMENT" in
  auto|off|required)
    ;;
  *)
    echo "window arrangement must be one of: auto, off, required" >&2
    exit 1
    ;;
esac

if [[ ! -x "$WRAPPER_PATH" ]]; then
  echo "Wrapper not found or not executable: $WRAPPER_PATH" >&2
  exit 1
fi

if [[ -n "$BATCH_RESULTS_DIR" && ${#PROJECT_ROOTS[@]} -eq 0 ]]; then
  while IFS= read -r project_root; do
    [[ -n "$project_root" ]] || continue
    PROJECT_ROOTS+=("$project_root")
  done < <(collect_green_projects_from_batch_results "$BATCH_RESULTS_DIR")
fi

if [[ ${#PROJECT_ROOTS[@]} -eq 0 ]]; then
  while IFS= read -r project_root; do
    [[ -n "$project_root" ]] || continue
    PROJECT_ROOTS+=("$project_root")
  done < <(discover_project_roots)
fi

if [[ ${#PROJECT_ROOTS[@]} -eq 0 ]]; then
  echo "No Unity projects selected for GUI test subset run." >&2
  exit 1
fi

if [[ -n "$RESULTS_DIR" ]]; then
  mkdir -p "$RESULTS_DIR"
  results_dir="$(python3 - "$RESULTS_DIR" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"
else
  results_dir="$(mktemp -d "${TMPDIR:-/tmp}/xuunity_multi_project_gui_subset.XXXXXX")"
fi

if [[ "$KEEP_RESULTS" == "false" ]]; then
  trap 'rm -rf "$results_dir"' EXIT
fi

printf 'selected_projects=%s\n' "${#PROJECT_ROOTS[@]}"
printf 'parallelism=%s\n' "$PARALLELISM"
printf 'startup_policy=%s\n' "$STARTUP_POLICY"
printf 'window_arrangement=%s\n' "$WINDOW_ARRANGEMENT"
printf 'results_dir=%s\n' "$results_dir"

printf '%s\0' "${PROJECT_ROOTS[@]}" | \
  xargs -0 -n1 -P "$PARALLELISM" "$0" __worker__ "$results_dir" "$STARTUP_POLICY" "$WINDOW_ARRANGEMENT"

emit_final_summary "$results_dir"
