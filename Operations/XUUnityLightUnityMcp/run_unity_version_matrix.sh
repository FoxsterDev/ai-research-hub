#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBLIC_OPS_ROOT="$SCRIPT_DIR"
WRAPPER="$PUBLIC_OPS_ROOT/xuunity_light_unity_mcp.sh"
INIT_SCRIPT="$PUBLIC_OPS_ROOT/init_xuunity_light_unity_mcp.sh"
ACCEPTANCE_SCENARIO="$PUBLIC_OPS_ROOT/templates/scenarios/interactive_acceptance_smoke.json"
REFRESH_SCENARIO="$PUBLIC_OPS_ROOT/templates/scenarios/refresh_contract_smoke.json"
COMPILE_SCENARIO="$PUBLIC_OPS_ROOT/templates/scenarios/compile_contract_smoke.json"

ARTIFACT_ROOT="${XUUNITY_LIGHT_UNITY_MCP_VERSION_MATRIX_ROOT:-${TMPDIR:-/tmp}/xuunity-light-unity-mcp-version-matrix}"
RUN_ID="$(date -u '+%Y%m%dT%H%M%SZ')"
RUN_ROOT="$ARTIFACT_ROOT/$RUN_ID"
PROJECTS_ROOT="$RUN_ROOT/projects"
RESULTS_ROOT="$RUN_ROOT/results"
SUMMARY_TSV="$RUN_ROOT/summary.tsv"
DISCOVERED_EDITORS_TSV="$RUN_ROOT/discovered_editors.tsv"

VERSIONS=()
KEEP_PROJECTS="false"
RECREATE_PROJECTS="false"
LIST_DETECTED="false"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [options] [unity_version...]

Options:
  --artifact-root <path>   Override artifact root. Default: $ARTIFACT_ROOT
  --keep-projects          Keep generated clean projects after the run.
  --recreate-projects      Recreate each clean project even if it already exists for this run.
  --list-detected          Print detected Unity versions and editor executables, then exit.
  -h, --help               Show this help.

If no Unity versions are provided, the script auto-discovers installed Unity editors on this host.
Set XUUNITY_UNITY_EDITOR_ROOTS to one or more custom editor roots separated by the platform path separator.
EOF
}

fail() {
  echo "$1" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact-root)
      shift
      [[ $# -gt 0 ]] || fail "--artifact-root requires a value"
      ARTIFACT_ROOT="$1"
      ;;
    --keep-projects)
      KEEP_PROJECTS="true"
      ;;
    --recreate-projects)
      RECREATE_PROJECTS="true"
      ;;
    --list-detected)
      LIST_DETECTED="true"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      VERSIONS+=("$1")
      ;;
  esac
  shift
done

ARTIFACT_ROOT="$(python3 - "$ARTIFACT_ROOT" <<'PY'
import os
import sys

path = sys.argv[1]
parent = os.path.dirname(path) or "."
parent_real = os.path.realpath(parent)
print(os.path.join(parent_real, os.path.basename(path)))
PY
)"

RUN_ROOT="$ARTIFACT_ROOT/$RUN_ID"
PROJECTS_ROOT="$RUN_ROOT/projects"
RESULTS_ROOT="$RUN_ROOT/results"
SUMMARY_TSV="$RUN_ROOT/summary.tsv"
DISCOVERED_EDITORS_TSV="$RUN_ROOT/discovered_editors.tsv"

mkdir -p "$PROJECTS_ROOT" "$RESULTS_ROOT"

echo -e "unity_version\tresult\tfailed_step\tproject_root\tresult_dir\tnotes" > "$SUMMARY_TSV"

discover_installed_editors() {
  python3 - <<'PY'
import os
import re
import sys
from pathlib import Path


def host_platform_kind():
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    return "linux"


def parse_version(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    match = re.search(r"(\d{4}\.\d+\.\d+[A-Za-z]\d+)", value)
    return match.group(1) if match else value


def version_sort_key(version: str):
    match = re.match(r"(\d+)\.(\d+)\.(\d+)([A-Za-z])(\d+)$", version or "")
    if not match:
        return (0, 0, 0, 0, 0, version or "")
    stream_rank = {"a": 0, "b": 1, "f": 2, "p": 3, "x": 4}
    major, minor, patch, stream, stream_number = match.groups()
    return (
        int(major),
        int(minor),
        int(patch),
        stream_rank.get(stream.lower(), 99),
        int(stream_number),
        version,
    )


def configured_roots():
    raw = (os.environ.get("XUUNITY_UNITY_EDITOR_ROOTS") or "").strip()
    if not raw:
        return []
    return [Path(entry).expanduser() for entry in raw.split(os.pathsep) if entry.strip()]


def candidate_roots():
    roots = configured_roots()
    if roots:
        return roots

    platform_kind = host_platform_kind()
    if platform_kind == "macos":
        return [Path("/Applications/Unity/Hub/Editor")]

    if platform_kind == "windows":
        values = []
        seen = set()
        for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            value = (os.environ.get(env_name) or "").strip()
            if not value:
                continue
            normalized = value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            values.append(Path(value).expanduser())
        return values

    return [
        Path.home() / "Unity" / "Hub" / "Editor",
        Path("/opt/Unity/Hub/Editor"),
        Path("/opt/unity/Hub/Editor"),
    ]


def normalize_installation(path: Path):
    candidate = path.expanduser().resolve()
    platform_kind = host_platform_kind()

    if platform_kind == "macos":
        if candidate.is_file() and candidate.name == "Unity" and candidate.parent.name == "MacOS":
            app_path = candidate.parent.parent.parent
            if app_path.name == "Unity.app":
                return app_path
        if candidate.is_dir() and candidate.name == "Unity.app" and (candidate / "Contents" / "MacOS" / "Unity").is_file():
            return candidate
        return None

    if platform_kind == "windows":
        if candidate.is_file() and candidate.name.lower() == "unity.exe":
            return candidate
        if candidate.is_dir():
            direct = candidate / "Unity.exe"
            nested = candidate / "Editor" / "Unity.exe"
            if direct.is_file():
                return direct
            if nested.is_file():
                return nested
        return None

    if candidate.is_file() and candidate.name == "Unity":
        return candidate
    if candidate.is_dir():
        direct = candidate / "Unity"
        nested = candidate / "Editor" / "Unity"
        if direct.is_file():
            return direct
        if nested.is_file():
            return nested
    return None


def resolve_executable(installation: Path):
    platform_kind = host_platform_kind()
    if platform_kind == "macos":
        return installation / "Contents" / "MacOS" / "Unity"
    return installation


def resolve_version(installation: Path):
    platform_kind = host_platform_kind()
    if platform_kind == "macos":
        return installation.parent.name
    if platform_kind == "windows":
        if installation.parent.name == "Editor":
            return parse_version(installation.parent.parent.name)
        return parse_version(installation.parent.name)
    if installation.parent.name == "Editor":
        return parse_version(installation.parent.parent.name)
    return parse_version(installation.parent.name)


def iter_candidates_from_root(root: Path):
    normalized = normalize_installation(root)
    if normalized is not None:
        yield normalized
        return

    if not root.exists():
        return

    platform_kind = host_platform_kind()
    patterns = []
    if platform_kind == "macos":
        patterns = ["*/Unity.app"]
    elif platform_kind == "windows":
        patterns = [
            "Unity/Hub/Editor/*/Editor/Unity.exe",
            "Unity*/Editor/Unity.exe",
            "Unity/Editor/Unity.exe",
        ]
    else:
        patterns = ["*/Editor/Unity", "*/Unity"]

    for pattern in patterns:
        for candidate in sorted(root.glob(pattern)):
            normalized_candidate = normalize_installation(candidate)
            if normalized_candidate is not None:
                yield normalized_candidate


discovered = []
seen = set()
for root in candidate_roots():
    for installation in iter_candidates_from_root(root):
        key = str(installation).lower() if os.name == "nt" else str(installation)
        if key in seen:
            continue
        seen.add(key)
        version = resolve_version(installation)
        executable = resolve_executable(installation)
        if version and executable.is_file():
            discovered.append((version, str(executable.resolve())))

for version, executable in sorted(discovered, key=lambda item: version_sort_key(item[0])):
    print(f"{version}\t{executable}")
PY
}

load_detected_versions_if_needed() {
  : > "$DISCOVERED_EDITORS_TSV"
  discover_installed_editors > "$DISCOVERED_EDITORS_TSV"

  if [[ "$LIST_DETECTED" == "true" ]]; then
    cat "$DISCOVERED_EDITORS_TSV"
    exit 0
  fi

  if [[ ${#VERSIONS[@]} -eq 0 ]]; then
    while IFS=$'\t' read -r unity_version unity_executable; do
      [[ -n "$unity_version" ]] || continue
      [[ -n "$unity_executable" ]] || continue
      VERSIONS+=("$unity_version")
    done < "$DISCOVERED_EDITORS_TSV"
  fi

  if [[ ${#VERSIONS[@]} -eq 0 ]]; then
    fail "No Unity editors were auto-detected. Install Unity via Hub or set XUUNITY_UNITY_EDITOR_ROOTS."
  fi
}

editor_path_for() {
  local version="$1"
  python3 - "$DISCOVERED_EDITORS_TSV" "$version" <<'PY'
import sys

tsv_path, target_version = sys.argv[1:3]
with open(tsv_path, "r", encoding="utf-8") as handle:
    for raw_line in handle:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        version, _, executable = line.partition("\t")
        if version == target_version:
            print(executable)
            raise SystemExit(0)
raise SystemExit(1)
PY
}

load_detected_versions_if_needed

write_json_result() {
  local output_path="$1"
  local status="$2"
  local unity_version="$3"
  local failed_step="$4"
  local notes="$5"
  python3 - "$output_path" "$status" "$unity_version" "$failed_step" "$notes" <<'PY'
import json
import sys

path, status, unity_version, failed_step, notes = sys.argv[1:6]
payload = {
    "status": status,
    "unity_version": unity_version,
    "failed_step": failed_step,
    "notes": notes,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
}

record_summary_row() {
  local unity_version="$1"
  local result="$2"
  local failed_step="$3"
  local project_root="$4"
  local result_dir="$5"
  local notes="$6"
  printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$unity_version" \
    "$result" \
    "$failed_step" \
    "$project_root" \
    "$result_dir" \
    "$notes" >> "$SUMMARY_TSV"
}

copy_if_exists() {
  local source_path="$1"
  local destination_path="$2"
  if [[ -f "$source_path" ]]; then
    cp "$source_path" "$destination_path"
  fi
}

run_step() {
  local step_name="$1"
  local stdout_path="$2"
  local stderr_path="$3"
  shift 3

  if "$@" >"$stdout_path" 2>"$stderr_path"; then
    return 0
  fi
  return 1
}

create_project_if_needed() {
  local unity_version="$1"
  local unity_path="$2"
  local project_root="$3"
  local result_dir="$4"

  if [[ -d "$project_root/Assets" && "$RECREATE_PROJECTS" != "true" ]]; then
    return 0
  fi

  rm -rf "$project_root"
  mkdir -p "$(dirname "$project_root")"

  "$unity_path" \
    -batchmode \
    -quit \
    -createProject "$project_root" \
    -logFile "$result_dir/create_project.log"
}

install_mcp_package() {
  local project_root="$1"
  bash "$INIT_SCRIPT" \
    --project-root "$project_root" \
    --enable-project
}

run_version_matrix_entry() {
  local unity_version="$1"
  local unity_path
  unity_path="$(editor_path_for "$unity_version")"

  local safe_version="${unity_version//./_}"
  local project_root="$PROJECTS_ROOT/SampleProject_$safe_version"
  local result_dir="$RESULTS_ROOT/$unity_version"
  mkdir -p "$result_dir"

  local result="passed"
  local failed_step="none"
  local notes=""

  if [[ ! -x "$unity_path" ]]; then
    result="editor_missing"
    failed_step="editor_lookup"
    notes="Unity executable not found at $unity_path"
    write_json_result "$result_dir/result.json" "$result" "$unity_version" "$failed_step" "$notes"
    record_summary_row "$unity_version" "$result" "$failed_step" "$project_root" "$result_dir" "$notes"
    return 0
  fi

  if ! create_project_if_needed "$unity_version" "$unity_path" "$project_root" "$result_dir"; then
    result="failed"
    failed_step="create_project"
    notes="Unity failed to create a clean project"
    write_json_result "$result_dir/result.json" "$result" "$unity_version" "$failed_step" "$notes"
    record_summary_row "$unity_version" "$result" "$failed_step" "$project_root" "$result_dir" "$notes"
    return 0
  fi

  if ! install_mcp_package "$project_root" >"$result_dir/init.stdout.txt" 2>"$result_dir/init.stderr.txt"; then
    result="failed"
    failed_step="init_mcp_package"
    notes="init_xuunity_light_unity_mcp.sh failed"
    write_json_result "$result_dir/result.json" "$result" "$unity_version" "$failed_step" "$notes"
    record_summary_row "$unity_version" "$result" "$failed_step" "$project_root" "$result_dir" "$notes"
    return 0
  fi

  local restore_needed="false"
  trap 'if [[ "$restore_needed" == "true" ]]; then "$WRAPPER" restore-editor-state --project-root "$project_root" --timeout-ms 30000 >/dev/null 2>&1 || true; fi' RETURN

  restore_needed="true"

  if ! run_step \
    "ensure-ready" \
    "$result_dir/ensure_ready.stdout.json" \
    "$result_dir/ensure_ready.stderr.txt" \
    "$WRAPPER" ensure-ready --project-root "$project_root" --open-editor --timeout-ms 240000; then
    result="failed"
    failed_step="ensure_ready"
    notes="ensure-ready failed"
  elif ! run_step \
    "request-status" \
    "$result_dir/request_status.stdout.json" \
    "$result_dir/request_status.stderr.txt" \
    "$WRAPPER" request-status --project-root "$project_root" --timeout-ms 15000; then
    result="failed"
    failed_step="request_status"
    notes="request-status failed"
  elif ! run_step \
    "request-health-probe" \
    "$result_dir/request_health_probe.stdout.json" \
    "$result_dir/request_health_probe.stderr.txt" \
    "$WRAPPER" request-health-probe --project-root "$project_root" --timeout-ms 15000; then
    result="failed"
    failed_step="request_health_probe"
    notes="request-health-probe failed"
  elif ! run_step \
    "request-capabilities" \
    "$result_dir/request_capabilities.stdout.json" \
    "$result_dir/request_capabilities.stderr.txt" \
    "$WRAPPER" request-capabilities --project-root "$project_root" --timeout-ms 15000; then
    result="failed"
    failed_step="request_capabilities"
    notes="request-capabilities failed"
  elif ! run_step \
    "interactive-acceptance" \
    "$result_dir/interactive_acceptance.stdout.json" \
    "$result_dir/interactive_acceptance.stderr.txt" \
    "$WRAPPER" request-scenario-run-and-wait --project-root "$project_root" --scenario-file "$ACCEPTANCE_SCENARIO" --timeout-ms 180000 --poll-interval-ms 500; then
    result="failed"
    failed_step="interactive_acceptance"
    notes="Interactive acceptance smoke failed"
  elif ! run_step \
    "refresh-contract" \
    "$result_dir/refresh_contract.stdout.json" \
    "$result_dir/refresh_contract.stderr.txt" \
    "$WRAPPER" request-scenario-run-and-wait --project-root "$project_root" --scenario-file "$REFRESH_SCENARIO" --timeout-ms 90000 --poll-interval-ms 500; then
    result="failed"
    failed_step="refresh_contract"
    notes="Refresh contract smoke failed"
  elif ! run_step \
    "compile-contract" \
    "$result_dir/compile_contract.stdout.json" \
    "$result_dir/compile_contract.stderr.txt" \
    "$WRAPPER" request-scenario-run-and-wait --project-root "$project_root" --scenario-file "$COMPILE_SCENARIO" --timeout-ms 180000 --poll-interval-ms 500; then
    result="failed"
    failed_step="compile_contract"
    notes="Compile contract smoke failed"
  fi

  copy_if_exists "$project_root/ProjectSettings/ProjectVersion.txt" "$result_dir/ProjectVersion.txt"
  copy_if_exists "$project_root/Library/XUUnityLightMcp/state/bridge_state.json" "$result_dir/bridge_state.json"
  copy_if_exists "$project_root/Library/XUUnityLightMcp/state/capabilities_report.json" "$result_dir/capabilities_report.json"

  "$WRAPPER" restore-editor-state \
    --project-root "$project_root" \
    --timeout-ms 30000 >"$result_dir/restore_editor_state.stdout.txt" 2>"$result_dir/restore_editor_state.stderr.txt" || true
  restore_needed="false"
  trap - RETURN

  write_json_result "$result_dir/result.json" "$result" "$unity_version" "$failed_step" "$notes"
  record_summary_row "$unity_version" "$result" "$failed_step" "$project_root" "$result_dir" "$notes"

  if [[ "$KEEP_PROJECTS" != "true" ]]; then
    rm -rf "$project_root"
  fi
}

for unity_version in "${VERSIONS[@]}"; do
  echo "[version-matrix] running $unity_version"
  run_version_matrix_entry "$unity_version"
done

echo "[version-matrix] summary=$SUMMARY_TSV"
