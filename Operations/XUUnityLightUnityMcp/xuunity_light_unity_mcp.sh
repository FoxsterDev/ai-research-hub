#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AIROOT_PATH="${XUUNITY_LIGHT_UNITY_MCP_AIRROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
REPO_ROOT="${XUUNITY_LIGHT_UNITY_MCP_REPO_ROOT:-$(cd "$AIROOT_PATH/.." && pwd)}"
INSTALL_DIR="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}/xuunity-light-unity-mcp"
SERVER_PATH="${XUUNITY_LIGHT_UNITY_MCP_SERVER:-$INSTALL_DIR/server.py}"
RUN_PATH="$INSTALL_DIR/run.sh"
SERVER_TEMPLATE_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/server.py"
RUN_TEMPLATE_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/run.sh"
SERVER_MODULES_TEMPLATE_RELATIVE_GLOB="Operations/XUUnityLightUnityMcp/templates/server_*.py"
RUNTIME_DEFAULTS_TEMPLATE_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/xuunity_light_unity_mcp_runtime_defaults.json"
PACKAGE_NAME="com.xuunity.light-mcp"
PACKAGE_TEMPLATE_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/unity-package"
COMPACT_SUMMARY="false"

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 1
  fi
}

emit_compact_summary_from_json_file() {
  local json_file="$1"
  local exit_code="$2"

  python3 - "$json_file" "$exit_code" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
exit_code = int(sys.argv[2])
if not path.is_file():
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)
if not isinstance(payload, dict):
    raise SystemExit(0)

def line(*parts):
    sys.stderr.write("[xuunity-light-unity-mcp] compact " + " ".join(str(p) for p in parts if str(p)) + "\n")

if str(payload.get("reason") or "") == "assistive_access_not_granted":
    line("outcome=window_arrangement", "reason=assistive_access_not_granted", "remediation=grant_accessibility_permission_then_rerun")
    raise SystemExit(0)

error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
error_code = str(error.get("code") or "")
if exit_code != 0 or error_code:
    parts = ["outcome=error", f"exit_code={exit_code}", f"code={error_code}"]
    if payload.get("request_id"):
        parts.append(f"request_id={payload.get('request_id')}")
    next_action = payload.get("recommended_next_action") or error.get("recommended_next_action")
    if next_action:
        parts.append(f"next={next_action}")
    line(*parts)
    raise SystemExit(0)

if payload.get("action") == "unity_status_summary" or "health_status" in payload:
    line(
        "outcome=status",
        f"health={payload.get('health_status', '')}",
        f"editor_running={str(bool(payload.get('editor_running'))).lower()}",
        f"mcp_reachable={str(bool(payload.get('mcp_reachable'))).lower()}",
        f"pending={int(payload.get('pending_request_count') or 0)}",
        f"busy_reason={payload.get('busy_reason', '')}",
        f"playmode={payload.get('playmode_state', '')}",
    )
    raise SystemExit(0)

if payload.get("request_id") and payload.get("payload_type"):
    parts = [
        "outcome=ok",
        f"request_id={payload.get('request_id')}",
        f"payload_type={payload.get('payload_type')}",
        f"status={payload.get('status', '')}",
    ]
    decoded = {}
    raw = payload.get("payload_json")
    if isinstance(raw, str) and raw:
        try:
            decoded = json.loads(raw)
        except Exception:
            decoded = {}
    payload_type = str(payload.get("payload_type") or "")
    if payload_type == "unity.compile.matrix":
        parts.extend([
            f"matrix_status={decoded.get('status', '')}",
            f"total={int(decoded.get('total') or 0)}",
            f"passed={int(decoded.get('passed') or 0)}",
            f"failed={int(decoded.get('failed') or 0)}",
        ])
    elif payload_type.startswith("unity.tests."):
        parts.extend([
            f"test_status={decoded.get('status', '')}",
            f"total={int(decoded.get('total') or 0)}",
            f"passed={int(decoded.get('passed') or 0)}",
            f"failed={int(decoded.get('failed') or 0)}",
        ])
    line(*parts)
PY
}

run_server_with_optional_compact_summary() {
  if [[ "$COMPACT_SUMMARY" != "true" ]]; then
    exec python3 "$SERVER_PATH" "$@"
  fi

  local stdout_file
  stdout_file="$(mktemp)"
  local exit_code=0

  if python3 "$SERVER_PATH" "$@" >"$stdout_file"; then
    exit_code=0
  else
    exit_code=$?
  fi

  cat "$stdout_file"
  emit_compact_summary_from_json_file "$stdout_file" "$exit_code"
  rm -f "$stdout_file"
  return "$exit_code"
}

sync_file_from_source() {
  local destination_path="$1"
  local relative_source_path="$2"
  local temp_path
  temp_path="$(mktemp)"
  cp "$AIROOT_PATH/$relative_source_path" "$temp_path"

  if [[ -f "$destination_path" ]] && cmp -s "$temp_path" "$destination_path"; then
    rm -f "$temp_path"
    return 0
  fi

  mv "$temp_path" "$destination_path"
}

sync_installed_helper_if_needed() {
  if [[ ! -e "$AIROOT_PATH/.git" || ! -f "$AIROOT_PATH/$SERVER_TEMPLATE_RELATIVE_PATH" ]]; then
    return 0
  fi

  mkdir -p "$INSTALL_DIR"

  sync_file_from_source "$SERVER_PATH" "$SERVER_TEMPLATE_RELATIVE_PATH"
  sync_file_from_source "$RUN_PATH" "$RUN_TEMPLATE_RELATIVE_PATH"
  sync_file_from_source "$INSTALL_DIR/$(basename "$RUNTIME_DEFAULTS_TEMPLATE_RELATIVE_PATH")" "$RUNTIME_DEFAULTS_TEMPLATE_RELATIVE_PATH"

  local module_source_path=""
  for module_source_path in "$AIROOT_PATH"/$SERVER_MODULES_TEMPLATE_RELATIVE_GLOB; do
    [[ -f "$module_source_path" ]] || continue
    sync_file_from_source "$INSTALL_DIR/$(basename "$module_source_path")" "${module_source_path#"$AIROOT_PATH/"}"
  done
  chmod 755 "$RUN_PATH"
}

require_project_root_argument() {
  local project_root=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project-root)
        shift
        if [[ $# -eq 0 ]]; then
          echo "--project-root requires a value" >&2
          exit 1
        fi
        project_root="$1"
        ;;
    esac
    shift || true
  done

  if [[ -z "$project_root" ]]; then
    echo "missing required argument: --project-root /path/to/UnityProject" >&2
    exit 1
  fi

  if [[ ! -d "$project_root/Packages" ]]; then
    echo "Unity project Packages directory not found under: $project_root" >&2
    exit 1
  fi

  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$project_root"
}

normalize_git_url_for_unity_upm() {
  local git_url="$1"

  case "$git_url" in
    git@github.com:*)
      git_url="https://github.com/${git_url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      git_url="https://github.com/${git_url#ssh://git@github.com/}"
      ;;
  esac

  printf '%s\n' "$git_url"
}

remote_advertises_commit() {
  local repo_root="$1"
  local remote_name="$2"
  local git_commit="$3"
  git -C "$repo_root" ls-remote --heads --tags "$remote_name" \
    | awk '{print $1}' \
    | grep -Fxq "$git_commit"
}

read_project_unity_version() {
  local project_root="$1"
  python3 - "$project_root/ProjectSettings/ProjectVersion.txt" <<'PY'
import pathlib
import sys

project_version_path = pathlib.Path(sys.argv[1])
for line in project_version_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("m_EditorVersion:"):
        print(line.split(":", 1)[1].strip())
        raise SystemExit(0)
raise SystemExit("Could not find m_EditorVersion in ProjectVersion.txt")
PY
}

update_manifest_dependency() {
  local manifest_path="$1"
  local dependency_value="$2"

  python3 - "$manifest_path" "$PACKAGE_NAME" "$dependency_value" <<'PY'
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
package_name = sys.argv[2]
dependency_value = sys.argv[3]

data = json.loads(manifest_path.read_text())
dependencies = data.setdefault("dependencies", {})
dependencies[package_name] = dependency_value
manifest_path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

remove_lock_dependency() {
  local lock_path="$1"

  if [[ ! -f "$lock_path" ]]; then
    return 0
  fi

  python3 - "$lock_path" "$PACKAGE_NAME" <<'PY'
import json
import pathlib
import sys

lock_path = pathlib.Path(sys.argv[1])
package_name = sys.argv[2]

data = json.loads(lock_path.read_text())
dependencies = data.get("dependencies")
if isinstance(dependencies, dict) and package_name in dependencies:
    del dependencies[package_name]
    lock_path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

switch_project_to_devmode() {
  require_command python3

  local project_root
  project_root="$(require_project_root_argument "$@")"
  local manifest_path="$project_root/Packages/manifest.json"
  local lock_path="$project_root/Packages/packages-lock.json"
  local package_source_path="$AIROOT_PATH/$PACKAGE_TEMPLATE_RELATIVE_PATH"

  if [[ ! -f "$package_source_path/package.json" ]]; then
    echo "local MCP package source not found: $package_source_path/package.json" >&2
    exit 1
  fi

  local dependency_value
  dependency_value="$(python3 - "$project_root/Packages" "$package_source_path" <<'PY'
import os
import sys
print("file:" + os.path.relpath(os.path.realpath(sys.argv[2]), os.path.realpath(sys.argv[1])))
PY
)"

  update_manifest_dependency "$manifest_path" "$dependency_value"
  remove_lock_dependency "$lock_path"

  echo "xuunity-light-unity-mcp mode switched: devmode"
  echo "project_root=$project_root"
  echo "dependency=$dependency_value"
  echo "package_source=$package_source_path"
  echo "packages_lock_entry_removed=true"
  echo "next_step=let Unity re-resolve packages by reopen, focus, or explicit refresh"
}

switch_project_to_prodmode() {
  require_command git
  require_command python3

  local project_root
  project_root="$(require_project_root_argument "$@")"
  local unity_version
  unity_version="$(read_project_unity_version "$project_root")"
  local unity_major="${unity_version%%.*}"

  if [[ ! -e "$AIROOT_PATH/.git" ]]; then
    echo "AIRoot git metadata not found: $AIROOT_PATH/.git" >&2
    exit 1
  fi

  case "$unity_major" in
    6000|6[0-9][0-9][0-9])
      ;;
    *)
      echo "prodmode is currently supported only for Unity 6000+ package variants; use devmode for direct local AIRoot package iteration on $unity_version" >&2
      exit 1
      ;;
  esac

  local manifest_path="$project_root/Packages/manifest.json"
  local lock_path="$project_root/Packages/packages-lock.json"
  local remote_name="origin"
  local git_url
  git_url="$(git -C "$AIROOT_PATH" remote get-url "$remote_name")"
  git_url="$(normalize_git_url_for_unity_upm "$git_url")"
  local git_commit
  git_commit="$(git -C "$AIROOT_PATH" rev-parse HEAD)"
  local airroot_branch
  airroot_branch="$(git -C "$AIROOT_PATH" branch --show-current)"

  if ! remote_advertises_commit "$AIROOT_PATH" "$remote_name" "$git_commit"; then
    echo "prodmode requires the current AIRoot HEAD to be published on the remote before pinning it." >&2
    echo "AIRoot commit is not currently advertised by remote '$remote_name' as a branch or tag tip: $git_commit" >&2
    if [[ -n "$airroot_branch" ]]; then
      echo "Push it first, for example: git -C \"$AIROOT_PATH\" push $remote_name $airroot_branch" >&2
    else
      echo "Push the AIRoot commit to '$remote_name' first, or use devmode for local-only iteration." >&2
    fi
    exit 1
  fi

  local dependency_value="${git_url}?path=/${PACKAGE_TEMPLATE_RELATIVE_PATH}#${git_commit}"

  update_manifest_dependency "$manifest_path" "$dependency_value"
  remove_lock_dependency "$lock_path"

  local worktree_dirty="false"
  if [[ -n "$(git -C "$AIROOT_PATH" status --short)" ]]; then
    worktree_dirty="true"
  fi

  echo "xuunity-light-unity-mcp mode switched: prodmode"
  echo "project_root=$project_root"
  echo "dependency=$dependency_value"
  echo "airroot_remote=$remote_name"
  echo "airroot_branch=$airroot_branch"
  echo "airroot_commit=$git_commit"
  echo "airroot_worktree_dirty=$worktree_dirty"
  echo "packages_lock_entry_removed=true"
  if [[ "$worktree_dirty" == "true" ]]; then
    echo "warning=prodmode pins the last committed AIRoot state only"
  else
    echo "warning=prodmode pins the current AIRoot HEAD commit; Unity must re-resolve to apply it"
  fi
}

dispatch_arrange_unity_windows() {
  local arrange_script_path="$AIROOT_PATH/Operations/XUUnityLightUnityMcp/arrange_unity_windows.py"
  if [[ ! -f "$arrange_script_path" ]]; then
    echo "arrange_unity_windows.py not found: $arrange_script_path" >&2
    exit 1
  fi

  exec python3 "$arrange_script_path" "$@"
}

filtered_args=()
for arg in "$@"; do
  if [[ "$arg" == "--compact-summary" ]]; then
    COMPACT_SUMMARY="true"
    continue
  fi
  filtered_args+=("$arg")
done
set -- "${filtered_args[@]}"

sync_installed_helper_if_needed

case "${1:-}" in
  arrange-unity-windows)
    shift
    dispatch_arrange_unity_windows "$@"
    exit 0
    ;;
  devmode)
    shift
    switch_project_to_devmode "$@"
    exit 0
    ;;
  prodmode)
    shift
    switch_project_to_prodmode "$@"
    exit 0
    ;;
esac

if [[ ! -f "$SERVER_PATH" ]]; then
  echo "xuunity-light-unity-mcp server not found: $SERVER_PATH" >&2
  echo "Install it with AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh" >&2
  exit 1
fi

run_server_with_optional_compact_summary "$@"
