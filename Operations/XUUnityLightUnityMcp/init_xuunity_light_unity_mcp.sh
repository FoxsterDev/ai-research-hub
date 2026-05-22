#!/bin/zsh
set -euo pipefail

dry_run=0
force=0
install_codex_config=0
install_claude_config=0
enable_project=0
disable_project=0
uninstall_project=0
project_root=""
target="both"

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
    --install-claude-config)
      install_claude_config=1
      shift
      ;;
    --target)
      target="$2"
      case "$target" in
        codex|claude|both) ;;
        *)
          echo "Unknown --target value: $target (allowed: codex, claude, both)" >&2
          exit 1
          ;;
      esac
      shift 2
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
    --project-root <path>     Optional Unity project root for wiring the editor-only package as a direct local AIRoot file dependency.
  --target codex|claude|both  Choose which install location(s) receive the server files.
                              codex  -> \$CODEX_TOOLS_HOME/xuunity-light-unity-mcp  (default \$HOME/.codex-tools)
                              claude -> \$CLAUDE_TOOLS_HOME/xuunity-light-unity-mcp (default \$HOME/.claude-tools)
                              both   -> install into both. Default: both.
  --install-codex-config      Also append the early-stage Codex MCP config block.
  --install-claude-config     Also register the MCP server in ~/.claude.json (Claude Code user scope).
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
codex_tools_home="${CODEX_TOOLS_HOME:-$HOME/.codex-tools}"
claude_tools_home="${CLAUDE_TOOLS_HOME:-$HOME/.claude-tools}"
codex_install_dir="$codex_tools_home/xuunity-light-unity-mcp"
claude_install_dir="$claude_tools_home/xuunity-light-unity-mcp"
config_path="$codex_home/config.toml"
claude_config_path="${CLAUDE_CONFIG_PATH:-$HOME/.claude.json}"
codex_run_path="$codex_install_dir/run.sh"
claude_run_path="$claude_install_dir/run.sh"

materialized_package_source_path() {
  local project_root="$1"
  printf '%s\n' "$project_root/XUUnityLightMcpPackageSource/com.xuunity.light-mcp"
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

warn_ripgrep_fallback_once() {
  if [[ "${xuunity_light_unity_mcp_rg_fallback_warned:-0}" -eq 1 ]]; then
    return 0
  fi
  print -u2 'optional command not found: rg; using grep fallback. Install ripgrep for faster local checks: brew install ripgrep'
  xuunity_light_unity_mcp_rg_fallback_warned=1
}

file_contains_regex() {
  local pattern="$1"
  local file_path="$2"
  if command -v rg >/dev/null 2>&1; then
    rg -q "$pattern" "$file_path"
  else
    warn_ripgrep_fallback_once
    grep -Eq "$pattern" "$file_path"
  fi
}

append_codex_block_if_missing() {
  local block
  block=$'[mcp_servers.xuunity_light_unity]\n'
  block+="command = \"$codex_run_path\""$'\n'
  block+=$'required = false\n'

  if [[ -f "$config_path" ]] && file_contains_regex '^\[mcp_servers\.xuunity_light_unity\]' "$config_path"; then
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

append_claude_block_if_missing() {
  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] register xuunity_light_unity MCP server in %s\n' "$claude_config_path"
    return
  fi

  mkdir -p "$(dirname "$claude_config_path")"

  python3 - "$claude_config_path" "$claude_run_path" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
run_path = sys.argv[2]

if config_path.exists() and config_path.stat().st_size > 0:
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"refusing to modify malformed JSON at {config_path}", file=sys.stderr)
        raise SystemExit(2)
else:
    data = {}

if not isinstance(data, dict):
    print(f"refusing to modify non-object JSON at {config_path}", file=sys.stderr)
    raise SystemExit(2)

servers = data.setdefault("mcpServers", {})
existing = servers.get("xuunity_light_unity")

portable_run_command = f'exec "{run_path}"'
desired = {
    "type": "stdio",
    "command": "bash",
    "args": ["-c", portable_run_command],
}

if existing == desired:
    print(f"kept existing Claude MCP config in {config_path}")
    raise SystemExit(0)

servers["xuunity_light_unity"] = desired
config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"updated {config_path}")
PY
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
  "transport": "tcp_loopback",
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

install_server_into() {
  local target_dir="$1"
  run mkdir -p "$target_dir"
  copy_if_needed "$templates_dir/server.py" "$target_dir/server.py" 644
  for helper_module in "$templates_dir"/server_*.py; do
    [[ -f "$helper_module" ]] || continue
    copy_if_needed "$helper_module" "$target_dir/$(basename "$helper_module")" 644
  done
  copy_if_needed "$templates_dir/run.sh" "$target_dir/run.sh" 755
}

run mkdir -p "$codex_home"
case "$target" in
  codex)
    install_server_into "$codex_install_dir"
    ;;
  claude)
    install_server_into "$claude_install_dir"
    ;;
  both)
    install_server_into "$codex_install_dir"
    install_server_into "$claude_install_dir"
    ;;
esac

if [[ -n "$project_root" ]]; then
  project_root="$(cd "$project_root" && pwd)"
  if [[ ! -d "$project_root/Assets" || ! -f "$project_root/ProjectSettings/ProjectVersion.txt" ]]; then
    echo "Not a Unity project root: $project_root" >&2
    exit 1
  fi

  project_package_dir="$project_root/Packages/com.xuunity.light-mcp"
  manifest_path="$project_root/Packages/manifest.json"
  package_source_path=""

  if [[ $uninstall_project -eq 0 && $disable_project -eq 0 ]]; then
    package_source_path="$(python3 - "$project_root/Packages" "$templates_dir/unity-package" <<'PY'
import os
import sys
print("file:" + os.path.relpath(os.path.realpath(sys.argv[2]), os.path.realpath(sys.argv[1])))
PY
)"
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

if [[ $install_claude_config -eq 1 ]]; then
  append_claude_block_if_missing
else
  printf 'skipped Claude Code user-scope config install by default; use --install-claude-config to register the server in ~/.claude.json, or copy templates/clients/claude-code/.mcp.json into a repo for project scope.\n'
fi

smoke_install_dir=""
case "$target" in
  codex) smoke_install_dir="$codex_install_dir" ;;
  claude) smoke_install_dir="$claude_install_dir" ;;
  both) smoke_install_dir="$codex_install_dir" ;;
esac

cat <<EOF

Next steps:
1. If you passed --project-root with --enable-project, open or reopen the Unity project once so the editor-only bridge can start writing heartbeat state.
2. Smoke-check bridge state:
   python3 $smoke_install_dir/server.py bridge-state --project-root /path/to/UnityProject
3. Smoke-check the direct same-host request status path:
   python3 $smoke_install_dir/server.py request-status --project-root /path/to/UnityProject
4. Preferred interactive startup helper:
   python3 $smoke_install_dir/server.py ensure-ready --project-root /path/to/UnityProject --open-editor --background-open --startup-policy fail_fast_on_interactive_compile_block

Installed files:
EOF

case "$target" in
  codex)
    printf -- '- %s/server.py\n- %s/run.sh\n' "$codex_install_dir" "$codex_install_dir"
    ;;
  claude)
    printf -- '- %s/server.py\n- %s/run.sh\n' "$claude_install_dir" "$claude_install_dir"
    ;;
  both)
    printf -- '- %s/server.py\n- %s/run.sh\n- %s/server.py\n- %s/run.sh\n' \
      "$codex_install_dir" "$codex_install_dir" "$claude_install_dir" "$claude_install_dir"
    ;;
esac
