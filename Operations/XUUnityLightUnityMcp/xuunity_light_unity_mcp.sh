#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HOST_WRAPPER_PATH="$REPO_ROOT/AIOutput/Operations/XUUnityLightUnityMcp/xuunity_light_unity_mcp.sh"
AIROOT_PATH="${XUUNITY_LIGHT_UNITY_MCP_AIRROOT:-$REPO_ROOT/AIRoot}"
INSTALL_DIR="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}/xuunity-light-unity-mcp"
SERVER_PATH="${XUUNITY_LIGHT_UNITY_MCP_SERVER:-$INSTALL_DIR/server.py}"
PACKAGE_NAME="com.xuunity.light-mcp"
PACKAGE_TEMPLATE_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/unity-package"
PACKAGE_MANIFEST_TEMPLATE_DIR_RELATIVE_PATH="Operations/XUUnityLightUnityMcp/templates/package-manifests"

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "required command not found: $command_name" >&2
    exit 1
  fi
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
    | rg -qx "$git_commit"
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

package_manifest_template_relative_path_for_version() {
  local unity_version="$1"
  local major="${unity_version%%.*}"

  case "$major" in
    6000|6[0-9][0-9][0-9])
      printf '%s/unity-package-6000.json\n' "$PACKAGE_MANIFEST_TEMPLATE_DIR_RELATIVE_PATH"
      ;;
    *)
      printf '%s/unity-package-2021_2022.json\n' "$PACKAGE_MANIFEST_TEMPLATE_DIR_RELATIVE_PATH"
      ;;
  esac
}

materialized_package_source_root() {
  local project_root="$1"
  printf '%s\n' "$project_root/XUUnityLightMcpPackageSource/$PACKAGE_NAME"
}

materialize_project_package_source() {
  local project_root="$1"
  local unity_version="$2"
  local source_template_path="$AIROOT_PATH/$PACKAGE_TEMPLATE_RELATIVE_PATH"
  local manifest_template_relative_path
  manifest_template_relative_path="$(package_manifest_template_relative_path_for_version "$unity_version")"
  local manifest_template_path="$AIROOT_PATH/$manifest_template_relative_path"
  local destination_path
  destination_path="$(materialized_package_source_root "$project_root")"

  if [[ ! -f "$source_template_path/package.json" ]]; then
    echo "local MCP package source not found: $source_template_path/package.json" >&2
    exit 1
  fi

  if [[ ! -f "$manifest_template_path" ]]; then
    echo "package manifest template not found: $manifest_template_path" >&2
    exit 1
  fi

  python3 - "$source_template_path" "$manifest_template_path" "$destination_path" "$unity_version" <<'PY'
import json
import pathlib
import shutil
import sys

source_template = pathlib.Path(sys.argv[1])
manifest_template = pathlib.Path(sys.argv[2])
destination = pathlib.Path(sys.argv[3])
unity_version = sys.argv[4]

if destination.exists():
    shutil.rmtree(destination)

shutil.copytree(source_template, destination)
shutil.copyfile(manifest_template, destination / "package.json")

metadata = {
    "materialized_for_unity_version": unity_version,
    "manifest_template": str(manifest_template),
    "source_template": str(source_template),
}
(destination / ".xuunity-package-source.json").write_text(
    json.dumps(metadata, indent=2) + "\n",
    encoding="utf-8",
)
PY

  printf 'updated %s\n' "$destination_path" >&2
  printf '%s\n' "$destination_path"
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
  local unity_version
  unity_version="$(read_project_unity_version "$project_root")"

  local manifest_path="$project_root/Packages/manifest.json"
  local lock_path="$project_root/Packages/packages-lock.json"
  local package_source_path
  package_source_path="$(materialize_project_package_source "$project_root" "$unity_version")"

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
  echo "unity_version=$unity_version"
  echo "dependency=$dependency_value"
  echo "materialized_package_source=$package_source_path"
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
      echo "prodmode is currently supported only for Unity 6000+ package variants; use devmode for version-aware materialized package sources on $unity_version" >&2
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

case "${1:-}" in
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

if [[ -x "$HOST_WRAPPER_PATH" ]]; then
  exec "$HOST_WRAPPER_PATH" "$@"
fi

if [[ ! -f "$SERVER_PATH" ]]; then
  echo "xuunity-light-unity-mcp server not found: $SERVER_PATH" >&2
  echo "Install it with AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh" >&2
  exit 1
fi

exec python3 "$SERVER_PATH" "$@"
