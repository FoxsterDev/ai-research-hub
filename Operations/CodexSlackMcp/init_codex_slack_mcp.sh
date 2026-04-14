#!/bin/zsh
set -euo pipefail

dry_run=0
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
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
  bash AIOutput/Operations/CodexSlackMcp/init_codex_slack_mcp.sh [--dry-run] [--force]

Flags:
  --dry-run  Print intended actions without writing files.
  --force    Overwrite installed server files and refresh the env template.
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
install_dir="$tools_home/slack-single-channel-mcp"
config_path="$codex_home/config.toml"
env_path="$codex_home/slack-single-channel.env"
run_path="$install_dir/run.sh"

run() {
  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    eval "$@"
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

  run "cp \"$src\" \"$dst\""
  run "chmod $mode \"$dst\""
  printf 'installed %s\n' "$dst"
}

append_mcp_block_if_missing() {
  local block
  block=$'[mcp_servers.slack_single_channel]\n'
  block+="command = \"$run_path\""$'\n'
  block+=$'required = false\n'

  if [[ -f "$config_path" ]] && rg -q '^\[mcp_servers\.slack_single_channel\]' "$config_path"; then
    printf 'kept existing MCP config in %s\n' "$config_path"
    return
  fi

  if [[ $dry_run -eq 1 ]]; then
    printf '[dry-run] append MCP block to %s\n' "$config_path"
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

run "mkdir -p \"$codex_home\" \"$install_dir\""
copy_if_needed "$templates_dir/server.mjs" "$install_dir/server.mjs" 644
copy_if_needed "$templates_dir/run.sh" "$install_dir/run.sh" 755
copy_if_needed "$templates_dir/slack-single-channel.env.template" "$env_path" 600
append_mcp_block_if_missing

cat <<EOF

Next steps:
1. Fill values in:
   $env_path
2. Restart Rider/Codex.
3. Ask Codex to run:
   slack_channel_status

Installed files:
- $install_dir/server.mjs
- $install_dir/run.sh
- $env_path
EOF
