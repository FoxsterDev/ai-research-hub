#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AIROOT_PATH="${XUUNITY_LIGHT_UNITY_MCP_AIRROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
if [[ -n "${XUUNITY_LIGHT_UNITY_MCP_REPO_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "$XUUNITY_LIGHT_UNITY_MCP_REPO_ROOT" && pwd)"
elif [[ -d "$AIROOT_PATH/../AIOutput" || -d "$AIROOT_PATH/../AIModules" ]]; then
  REPO_ROOT="$(cd "$AIROOT_PATH/.." && pwd)"
else
  REPO_ROOT="$(pwd)"
fi
WRAPPER_PATH="${XUUNITY_LIGHT_UNITY_MCP_WRAPPER:-$SCRIPT_DIR/xuunity_light_unity_mcp.sh}"

PARALLELISM=4
CLOSE_LIVE_EDITORS="true"
KEEP_RESULTS="true"
RESULTS_DIR=""
PROJECT_ROOTS=()

usage() {
  cat <<'EOF'
Usage:
  run_multi_project_batch_compile_matrix.sh [options]

Options:
  --parallelism N          Number of concurrent batch compile workers. Default: 4
  --repo-root PATH         Root containing Unity project directories. Defaults to env or current repo layout.
  --project-root PATH      Include one explicit Unity project root. Repeatable.
  --close-live-editors     Try to recover/close live editors before batch compile. Default.
  --no-close-live-editors  Skip the recovery preflight and fail fast on editor conflicts.
  --results-dir DIR        Write status artifacts to a persistent directory.
  --cleanup-results        Remove the results dir on exit instead of keeping it.
  --help                   Show this message.

Behavior:
  - auto-discovers direct child Unity projects under the selected repo root
  - filters to projects that already declare com.xuunity.light-mcp
  - runs batch-build-config-compile-matrix in parallel
  - emits one compact per-project summary plus a final aggregate summary
  - keeps results_dir by default so it can feed later GUI-subset runs
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

discover_project_roots() {
  local child_dir=""
  for child_dir in "$REPO_ROOT"/*; do
    [[ -d "$child_dir" ]] || continue
    [[ -f "$child_dir/Packages/manifest.json" ]] || continue
    [[ -f "$child_dir/ProjectSettings/ProjectVersion.txt" ]] || continue
    if grep -Eq '"com\.xuunity\.light-mcp"' "$child_dir/Packages/manifest.json"; then
      printf '%s\n' "$child_dir"
    fi
  done | sort
}

run_worker() {
  local results_dir="$1"
  local close_live_editors="$2"
  local project_root="$3"
  local project_name
  project_name="$(basename "$project_root")"
  local worker_prefix="$results_dir/$project_name"
  local recover_output_file="${worker_prefix}_recover.log"
  local stdout_file="${worker_prefix}_batch_stdout.json"
  local stderr_file="${worker_prefix}_batch_stderr.log"
  local status_file="${worker_prefix}_status.json"
  local recover_rc=0
  local batch_rc=0

  if [[ "$close_live_editors" == "true" ]]; then
    if ! "$WRAPPER_PATH" recover-editor-session --project-root "$project_root" >"$recover_output_file" 2>&1; then
      recover_rc=$?
    fi
  fi

  if ! "$WRAPPER_PATH" batch-build-config-compile-matrix --project-root "$project_root" >"$stdout_file" 2>"$stderr_file"; then
    batch_rc=$?
  fi

  python3 - "$project_name" "$project_root" "$stdout_file" "$stderr_file" "$status_file" "$recover_rc" "$batch_rc" <<'PY'
import json
import sys
from pathlib import Path

project_name = sys.argv[1]
project_root = sys.argv[2]
stdout_file = Path(sys.argv[3])
stderr_file = Path(sys.argv[4])
status_file = Path(sys.argv[5])
recover_rc = int(sys.argv[6])
batch_rc = int(sys.argv[7])

payload = {}
parse_error = ""
if stdout_file.is_file():
    try:
        payload = json.loads(stdout_file.read_text(encoding="utf-8"))
    except Exception as exc:
        parse_error = str(exc)

result_summary = payload.get("result_summary") if isinstance(payload, dict) else {}
matrix = result_summary.get("matrix") if isinstance(result_summary, dict) else {}
stderr_tail = ""
if stderr_file.is_file():
    stderr_lines = stderr_file.read_text(encoding="utf-8", errors="replace").splitlines()
    stderr_tail = "\n".join(stderr_lines[-20:])

status = {
    "project": project_name,
    "project_root": project_root,
    "recover_rc": recover_rc,
    "batch_rc": batch_rc,
    "json_parse_ok": bool(payload),
    "parse_error": parse_error,
    "succeeded": bool(payload.get("succeeded")) if isinstance(payload, dict) else False,
    "unity_outcome": result_summary.get("unity_outcome", "") if isinstance(result_summary, dict) else "",
    "transport_outcome": result_summary.get("transport_outcome", "") if isinstance(result_summary, dict) else "",
    "matrix_status": matrix.get("status", "") if isinstance(matrix, dict) else "",
    "total": int(matrix.get("total", 0)) if isinstance(matrix, dict) else 0,
    "passed": int(matrix.get("passed", 0)) if isinstance(matrix, dict) else 0,
    "failed": int(matrix.get("failed", 0)) if isinstance(matrix, dict) else 0,
    "skipped": int(matrix.get("skipped", 0)) if isinstance(matrix, dict) else 0,
    "summary_file": str(payload.get("summary_file", "")) if isinstance(payload, dict) else "",
    "result_file": str(payload.get("result_file", "")) if isinstance(payload, dict) else "",
    "log_path": str(payload.get("log_path", "")) if isinstance(payload, dict) else "",
    "stderr_tail": stderr_tail,
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

print("MULTI_PROJECT_BATCH_COMPILE_MATRIX_SUMMARY_BEGIN")
overall_failed = 0
for item in statuses:
    ok = (
        item.get("recover_rc", 0) == 0
        and item.get("batch_rc", 0) == 0
        and item.get("succeeded") is True
        and item.get("matrix_status") == "passed"
        and item.get("failed", 0) == 0
    )
    if not ok:
        overall_failed += 1
    fields = [
        item.get("project", ""),
        f"recover_rc={item.get('recover_rc', 0)}",
        f"batch_rc={item.get('batch_rc', 0)}",
        f"succeeded={str(bool(item.get('succeeded'))).lower()}",
        f"matrix_status={item.get('matrix_status', '')}",
        f"total={item.get('total', 0)}",
        f"passed={item.get('passed', 0)}",
        f"failed={item.get('failed', 0)}",
        f"skipped={item.get('skipped', 0)}",
    ]
    print("|".join(fields))
print("MULTI_PROJECT_BATCH_COMPILE_MATRIX_SUMMARY_END")

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
  run_worker "$2" "$3" "$4"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --parallelism)
      PARALLELISM="${2:-}"
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
    --close-live-editors)
      CLOSE_LIVE_EDITORS="true"
      shift
      ;;
    --no-close-live-editors)
      CLOSE_LIVE_EDITORS="false"
      shift
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

if [[ ! -x "$WRAPPER_PATH" ]]; then
  echo "Wrapper not found or not executable: $WRAPPER_PATH" >&2
  exit 1
fi

if [[ ${#PROJECT_ROOTS[@]} -eq 0 ]]; then
  while IFS= read -r project_root; do
    [[ -n "$project_root" ]] || continue
    PROJECT_ROOTS+=("$project_root")
  done < <(discover_project_roots)
fi

if [[ ${#PROJECT_ROOTS[@]} -eq 0 ]]; then
  echo "No Unity projects with com.xuunity.light-mcp were discovered." >&2
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
  results_dir="$(mktemp -d "${TMPDIR:-/tmp}/xuunity_multi_project_batch_compile.XXXXXX")"
fi

if [[ "$KEEP_RESULTS" == "false" ]]; then
  trap 'rm -rf "$results_dir"' EXIT
fi

printf 'discovered_projects=%s\n' "${#PROJECT_ROOTS[@]}"
printf 'parallelism=%s\n' "$PARALLELISM"
printf 'close_live_editors=%s\n' "$CLOSE_LIVE_EDITORS"
printf 'results_dir=%s\n' "$results_dir"

printf '%s\0' "${PROJECT_ROOTS[@]}" | \
  xargs -0 -n1 -P "$PARALLELISM" "$0" __worker__ "$results_dir" "$CLOSE_LIVE_EDITORS"

emit_final_summary "$results_dir"
