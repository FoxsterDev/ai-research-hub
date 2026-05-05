#!/bin/zsh
set -euo pipefail

dry_run=0
force=0
install_codex_config=0
enable_project=0
disable_project=0
uninstall_project=0
project_root=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)
      project_root="$2"
      shift 2
      ;;
    --install-codex-config)
      install_codex_config=1
      shift
      ;;
    --enable-project)
      enable_project=1
      shift
      ;;
    --disable-project)
      disable_project=1
      shift
      ;;
    --uninstall-project)
      uninstall_project=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage:
  bash AIRoot/Operations/XUUnityLightUnityMcp/init_xuunity_light_unity_mcp.sh [options]

Options:
    --project-root <path>     Optional Unity project root for copying the editor-only package scaffold.
  --install-codex-config    Also append the early-stage Codex MCP config block.
  --enable-project          Write local bridge config under Library/ so the editor-only bridge is active on next editor load.
  --disable-project         Remove local bridge config and local bridge state under Library/.
  --uninstall-project       Remove the project package, manifest dependency, and local bridge state from the Unity project.
  --dry-run                 Print intended actions without writing files.
  --force                   Overwrite installed scaffold files.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

script_dir="$(cd "$(dirname "$0")" && pwd)"
templates_dir="$script_dir/templates"
codex_home="${CODEX_HOME:-$HOME/.codex}"
tools_home="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
install_dir="$tools_home/xuunity-light-unity-mcp"
config_path="$codex_home/config.toml"
run_path="$install_dir/run.sh"

run() {
  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] %s' "$1"
    shift
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

copy_if_needed() {
  local src="$1"
  local dst="$2"
  local mode="$3"

  if [[ -f "$dst" && $force -ne 1 ]]; then
    printf 'kept existing %s\n' "$dst"
    return
  fi

  run cp "$src" "$dst"
  run chmod "$mode" "$dst"
  printf 'installed %s\n' "$dst"
}

copy_dir_if_needed() {
  local src="$1"
  local dst="$2"

  if [[ -d "$dst" && $force -ne 1 ]]; then
    printf 'kept existing %s\n' "$dst"
    return
  fi

  run mkdir -p "$dst"
  run cp -R "$src/." "$dst/"
  printf 'installed %s\n' "$dst"
}

append_codex_block_if_missing() {
  local block
  block=$'[mcp_servers.xuunity_light_unity]\n'
  block+="command = \"$run_path\""$'\n'
  block+=$'required = false\n'

  if [[ -f "$config_path" ]] && rg -q '^\[mcp_servers\.xuunity_light_unity\]' "$config_path"; then
    printf 'kept existing MCP config in %s\n' "$config_path"
    return
  fi

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] append experimental MCP block to %s\n' "$config_path"
    printf '%s' "$block"
    return
  fi

  mkdir -p "$codex_home"
  touch "$config_path"
  if [[ -s "$config_path" ]]; then
    printf '\n' >> "$config_path"
  fi
  printf '%s' "$block" >> "$config_path"
  printf 'updated %s\n' "$config_path"
}

patch_manifest_if_needed() {
  local manifest_path="$1"

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] patch manifest %s with com.xuunity.light-mcp file dependency\n' "$manifest_path"
    return
  fi

  python3 - "$manifest_path" <<'PY'
import json
import sys

manifest_path = sys.argv[1]
with open(manifest_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

deps = data.setdefault("dependencies", {})
value = "file:Packages/com.xuunity.light-mcp"
if deps.get("com.xuunity.light-mcp") != value:
    deps["com.xuunity.light-mcp"] = value
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=True)
        fh.write("\n")
PY

  printf 'updated %s\n' "$manifest_path"
}

unpatch_manifest_if_needed() {
  local manifest_path="$1"

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] remove com.xuunity.light-mcp dependency from %s\n' "$manifest_path"
    return
  fi

  python3 - "$manifest_path" <<'PY'
import json
import sys

manifest_path = sys.argv[1]
with open(manifest_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

deps = data.get("dependencies", {})
deps.pop("com.xuunity.light-mcp", None)

with open(manifest_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=True)
    fh.write("\n")
PY

  printf 'updated %s\n' "$manifest_path"
}

write_bridge_config() {
  local project_root="$1"
  local config_dir="$project_root/Library/XUUnityLightMcp/config"
  local config_path="$config_dir/bridge_config.json"

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] write %s\n' "$config_path"
    return
  fi

  mkdir -p "$config_dir"
  cat > "$config_path" <<'EOF'
{
  "enabled": true,
  "heartbeat_interval_ms": 2000,
  "pump_interval_ms": 500
}
EOF
  printf 'updated %s\n' "$config_path"
}

remove_bridge_state() {
  local project_root="$1"
  local bridge_root="$project_root/Library/XUUnityLightMcp"

  if [[ ! -e "$bridge_root" ]]; then
    return
  fi

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] remove %s\n' "$bridge_root"
    return
  fi

  rm -rf "$bridge_root"
  printf 'removed %s\n' "$bridge_root"
}

run mkdir -p "$codex_home" "$install_dir"
copy_if_needed "$templates_dir/server.py" "$install_dir/server.py" 644
copy_if_needed "$templates_dir/run.sh" "$install_dir/run.sh" 755

if [[ -n "$project_root" ]]; then
  project_root="$(cd "$project_root" && pwd)"
  if [[ ! -d "$project_root/Assets" || ! -f "$project_root/ProjectSettings/ProjectVersion.txt" ]]; then
    echo "Not a Unity project root: $project_root" >&2
    exit 1
  fi

  project_package_dir="$project_root/Packages/com.xuunity.light-mcp"
  manifest_path="$project_root/Packages/manifest.json"

  if [[ $uninstall_project -eq 1 ]]; then
    if [[ $dry_run -eq 1 ]]; then
      printf '[dry-run] remove %s\n' "$project_package_dir"
    else
      rm -rf "$project_package_dir"
      printf 'removed %s\n' "$project_package_dir"
    fi
    unpatch_manifest_if_needed "$manifest_path"
    remove_bridge_state "$project_root"
  elif [[ $disable_project -eq 1 ]]; then
    remove_bridge_state "$project_root"
  else
    copy_dir_if_needed "$templates_dir/unity-package" "$project_package_dir"
    patch_manifest_if_needed "$manifest_path"

    if [[ $enable_project -eq 1 ]]; then
      write_bridge_config "$project_root"
    fi

    if [[ $disable_project -eq 1 ]]; then
      remove_bridge_state "$project_root"
    fi
  fi
fi

if [[ $install_codex_config -eq 1 ]]; then
  append_codex_block_if_missing
else
  printf 'skipped Codex config install by default; use --install-codex-config once you want to test the early-stage stdio MCP layer in a real client.\n'
fi

cat <<EOF

Next steps:
1. If you passed --project-root with --enable-project, open or reopen the Unity project once so the editor-only bridge can start writing heartbeat state.
2. Smoke-check bridge state:
   python3 $install_dir/server.py bridge-state --project-root /path/to/UnityProject
3. Smoke-check the direct file IPC status path:
   python3 $install_dir/server.py request-status --project-root /path/to/UnityProject

Installed files:
- $install_dir/server.py
- $install_dir/run.sh
EOF
