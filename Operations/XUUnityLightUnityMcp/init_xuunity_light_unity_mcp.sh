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
    --project-root <path>     Optional Unity project root for wiring the editor-only package as a file dependency with a version-aware generated package source.
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

select_package_manifest_template() {
  local unity_version="$1"
  local major="${unity_version%%.*}"

  case "$major" in
    6000|6[0-9][0-9][0-9])
      printf '%s\n' "$templates_dir/package-manifests/unity-package-6000.json"
      ;;
    *)
      printf '%s\n' "$templates_dir/package-manifests/unity-package-2021_2022.json"
      ;;
  esac
}

materialized_package_source_path() {
  local project_root="$1"
  printf '%s\n' "$project_root/XUUnityLightMcpPackageSource/com.xuunity.light-mcp"
}

materialize_package_source() {
  local project_root="$1"
  local unity_version="$2"
  local source_template_path="$templates_dir/unity-package"
  local manifest_template_path
  manifest_template_path="$(select_package_manifest_template "$unity_version")"
  local destination_path
  destination_path="$(materialized_package_source_path "$project_root")"

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] materialize package source %s from %s with manifest %s\n' \
      "$destination_path" \
      "$source_template_path" \
      "$manifest_template_path"
    printf '%s\n' "$destination_path"
    return
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

remove_materialized_package_source() {
  local project_root="$1"
  local source_root
  source_root="$(materialized_package_source_path "$project_root")"

  if [[ ! -e "$source_root" ]]; then
    return
  fi

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] remove %s\n' "$source_root"
    return
  fi

  rm -rf "$source_root"
  printf 'removed %s\n' "$source_root"
}

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

  if [[ -f "$dst" && $force -ne 1 ]] && cmp -s "$src" "$dst"; then
    printf 'kept existing %s\n' "$dst"
    return
  fi

  run cp "$src" "$dst"
  run chmod "$mode" "$dst"
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
  local package_source_path="$2"

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] patch manifest %s with com.xuunity.light-mcp file dependency -> %s\n' "$manifest_path" "$package_source_path"
    return
  fi

  python3 - "$manifest_path" "$package_source_path" <<'PY'
import json
import os
import sys

manifest_path = sys.argv[1]
package_source_path = sys.argv[2]
with open(manifest_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

deps = data.setdefault("dependencies", {})
manifest_dir = os.path.dirname(manifest_path)
relative_package_source_path = os.path.relpath(package_source_path, start=manifest_dir).replace(os.sep, "/")
value = "file:" + relative_package_source_path
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
  "pump_interval_ms": 500,
  "transport": "file_ipc",
  "loopback_host": "127.0.0.1",
  "loopback_port": 0
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
for helper_module in "$templates_dir"/server_*.py; do
  [[ -f "$helper_module" ]] || continue
  copy_if_needed "$helper_module" "$install_dir/$(basename "$helper_module")" 644
done
copy_if_needed "$templates_dir/run.sh" "$install_dir/run.sh" 755

if [[ -n "$project_root" ]]; then
  project_root="$(cd "$project_root" && pwd)"
  if [[ ! -d "$project_root/Assets" || ! -f "$project_root/ProjectSettings/ProjectVersion.txt" ]]; then
    echo "Not a Unity project root: $project_root" >&2
    exit 1
  fi

  unity_version="$(read_project_unity_version "$project_root")"
  project_package_dir="$project_root/Packages/com.xuunity.light-mcp"
  manifest_path="$project_root/Packages/manifest.json"
  package_source_path=""

  if [[ $uninstall_project -eq 0 && $disable_project -eq 0 ]]; then
    package_source_path="$(materialize_package_source "$project_root" "$unity_version")"
  fi

  if [[ $uninstall_project -eq 1 ]]; then
    if [[ $dry_run -eq 1 ]]; then
      printf '[dry-run] remove %s\n' "$project_package_dir"
    else
      rm -rf "$project_package_dir"
      printf 'removed %s\n' "$project_package_dir"
    fi
    unpatch_manifest_if_needed "$manifest_path"
    remove_materialized_package_source "$project_root"
    remove_bridge_state "$project_root"
  elif [[ $disable_project -eq 1 ]]; then
    remove_bridge_state "$project_root"
  else
    patch_manifest_if_needed "$manifest_path" "$package_source_path"

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
4. Preferred interactive startup helper:
   python3 $install_dir/server.py ensure-ready --project-root /path/to/UnityProject --open-editor --background-open --startup-policy fail_fast_on_interactive_compile_block

Installed files:
- $install_dir/server.py
- $install_dir/run.sh
EOF
