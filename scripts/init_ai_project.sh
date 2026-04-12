#!/usr/bin/env bash

set -euo pipefail

AIRROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ROOT_DIR="$(cd "$AIRROOT_DIR/.." && pwd -P)"
MODE="--fix"
PROJECT_ARG=""
PROJECT_KIND="gameplay"
PRIORITY="Stability > Performance > Maintainability"
HAS_AIMODULES=0
HAS_XUUNITY_INTERNAL=0
REPO_MODE="auto"
ALLOW_MANAGED_REFRESH=0
ALLOW_ADOPT_EXISTING=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  bash AIRoot/scripts/init_ai_project.sh --project <path-or-name> [--kind gameplay|infrastructure] [--priority "custom priority"] [--repo-mode auto|single-project|monorepo] [--refresh-managed-router] [--adopt-existing-router] [--dry-run] [--check|--fix]

Examples:
  bash AIRoot/scripts/init_ai_project.sh --project NewGame
  bash AIRoot/scripts/init_ai_project.sh --project /path/to/NewGame --kind infrastructure
  bash AIRoot/scripts/init_ai_project.sh --project NewGame --repo-mode single-project
  bash AIRoot/scripts/init_ai_project.sh --project NewGame --repo-mode single-project --dry-run
  bash AIRoot/scripts/init_ai_project.sh --project ExistingGame --repo-mode monorepo --refresh-managed-router
  bash AIRoot/scripts/init_ai_project.sh --project ExistingGame --repo-mode monorepo --adopt-existing-router
EOF
}

log() {
  printf '%s\n' "$1"
}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

dry_log() {
  printf 'DRY RUN: %s\n' "$1"
}

resolve_path() {
  local value="$1"

  python3 - "$ROOT_DIR" "$value" <<'PY'
import os
import sys

root = sys.argv[1]
value = sys.argv[2]

if os.path.isabs(value):
    path = os.path.normpath(value)
else:
    path = os.path.normpath(os.path.join(root, value))

print(os.path.realpath(path))
PY
}

relative_path() {
  local target="$1"
  local start="$2"

  python3 - "$target" "$start" <<'PY'
import os
import sys

print(os.path.relpath(sys.argv[1], sys.argv[2]))
PY
}

validate_file() {
  local path="$1"
  [ -e "$path" ] || fail "Missing: $path"
}

is_expected_symlink() {
  local link_path="$1"
  local expected_target="$2"

  [ -L "$link_path" ] || return 1
  [ "$(readlink "$link_path")" = "$expected_target" ]
}

ensure_symlink() {
  local target="$1"
  local link_path="$2"

  if is_expected_symlink "$link_path" "$target"; then
    log "OK: $link_path -> $target"
    return 0
  fi

  if [ "$MODE" = "--check" ]; then
    fail "Invalid or missing symlink: $link_path -> $target"
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would configure symlink $link_path -> $target"
    return 0
  fi

  if [ -L "$link_path" ]; then
    rm "$link_path"
  elif [ -e "$link_path" ]; then
    fail "Refusing to replace non-symlink path: $link_path"
  fi

  ln -s "$target" "$link_path"
  log "Configured: $link_path -> $target"
}

router_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_project\.sh -->$' "$path"
}

write_router() {
  local router_path="$1"
  local project_name="$2"
  local project_kind="$3"
  local priority="$4"
  local repo_router_rel="$5"
  local airroot_rel="$6"
  local aimodules_rel="$7"
  local has_aimodules="$8"
  local repo_mode="$9"

  local load_order_line
  local optional_note=""
  local host_local_block
  local xuunity_internal_line=""
  local project_memory_line="6. Project memory from \`Assets/AIOutput/ProjectMemory/\`"
  local prior_outputs_line="7. Relevant prior analysis outputs from \`Assets/AIOutput/\`"

  if [ "$repo_mode" = "monorepo" ] && [ "$has_aimodules" = "1" ]; then
    load_order_line="2. Shared protocol modules from \`$airroot_rel/Modules/\` and optional host-local prompt families from \`$aimodules_rel/\` when that root exists. Use local alias \`AIModules/\` only for host-local families when it exists and mirrors the same structure."
    xuunity_internal_line="6. Monorepo-internal \`xuunity\` overlay from \`$aimodules_rel/XUUnityInternal/\` only when it exists and is relevant to the task"
    project_memory_line="7. Project memory from \`Assets/AIOutput/ProjectMemory/\`"
    prior_outputs_line="8. Relevant prior analysis outputs from \`Assets/AIOutput/\`"
    host_local_block=$(cat <<EOF
### \`host-local protocols\`
Use host-local protocol families only when the repo explicitly attaches them under \`$aimodules_rel/\`.
Load those families from verified on-disk paths instead of assuming any named private modules.
EOF
)
  else
    load_order_line="2. Shared protocol modules from \`$airroot_rel/Modules/\`. Host-local prompt families under \`AIModules/\` are optional and are not required for this host topology."
    optional_note="This project is configured for a core-only host shape unless the repo later attaches host-local modules. Use the shared \`xuunity\` layer from \`AIRoot\` plus project memory as the default setup."
    host_local_block=$(cat <<'EOF'
### `host-local protocols`
Host-local protocol families are optional and unavailable until the repo attaches them under `AIModules/`.
EOF
)
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would write managed project router to $router_path using repo mode $repo_mode"
    return 0
  fi

  cat > "$router_path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_project.sh -->
# Project Agent Router: $project_name

## Purpose
This file is the project-level routing layer.
Keep it short. Route the work first, then load the minimum required protocol files.

## Load Order
1. Local repo router alias \`Agents.repo.md\` if available, otherwise repo-level \`$repo_router_rel\`
$load_order_line
3. This project file
4. Project memory from \`Assets/AIOutput/ProjectMemory/\`
5. Existing project outputs from \`Assets/AIOutput/\`

After loading this router, always verify the real on-disk prompt structure before opening files. Do not assume older flat paths still exist.
${optional_note}

## Project Context
- Project: \`$project_name\`
- Engine context: Unity project
- Project kind: \`$project_kind\`
- Priority: $priority
- Project memory path: \`Assets/AIOutput/ProjectMemory/\`
- AI output path: \`Assets/AIOutput/\`

## Routing

### \`xuunity\`
Use \`xuunity\` as the default protocol for project work, including bug fixing, refactoring, feature development, code review, SDK integration, SDK review, native plugin work, native plugin review, Unity runtime safety, JNI, Objective-C, Swift, performance audits, and store compliance.

Load in this order:
1. \`$airroot_rel/Modules/XUUnity/role/base_role.md\`
2. One or more relevant files from \`$airroot_rel/Modules/XUUnity/codestyle/\`
3. One task file from \`$airroot_rel/Modules/XUUnity/tasks/\`
4. One or more review or utility files from \`$airroot_rel/Modules/XUUnity/reviews/\` or \`$airroot_rel/Modules/XUUnity/utilities/\`
5. Platform files from \`$airroot_rel/Modules/XUUnity/platforms/\` only if relevant
${xuunity_internal_line}
${project_memory_line}
${prior_outputs_line}

$host_local_block

## Override Rules
- Project memory in \`Assets/AIOutput/ProjectMemory/\` overrides shared prompts when there is a conflict.
- Follow the repo-level AI output storage rule from \`$repo_router_rel\` instead of redefining local storage semantics.
- For feature work, bug fixing, refactoring, and code review, load durable guidance from \`Assets/AIOutput/ProjectMemory/\` by default.
- Load historical analysis outputs from \`Assets/AIOutput/\` only for behavior investigation, legacy reconstruction, or old bug research.
- For shared prompts, prefer repo-level canonical files and validate their actual folder layout before loading.
- If legacy text conflicts with this router, this router wins.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project)
      [ "$#" -ge 2 ] || fail "Missing value for --project"
      PROJECT_ARG="$2"
      shift 2
      ;;
    --kind)
      [ "$#" -ge 2 ] || fail "Missing value for --kind"
      PROJECT_KIND="$2"
      shift 2
      ;;
    --priority)
      [ "$#" -ge 2 ] || fail "Missing value for --priority"
      PRIORITY="$2"
      shift 2
      ;;
    --repo-mode)
      [ "$#" -ge 2 ] || fail "Missing value for --repo-mode"
      REPO_MODE="$2"
      shift 2
      ;;
    --refresh-managed-router)
      ALLOW_MANAGED_REFRESH=1
      shift
      ;;
    --adopt-existing-router)
      ALLOW_ADOPT_EXISTING=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --check|--fix)
      MODE="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[ -n "$PROJECT_ARG" ] || fail "Missing required --project argument"

case "$PROJECT_KIND" in
  gameplay|infrastructure)
    ;;
  *)
    fail "Unsupported --kind '$PROJECT_KIND'. Use gameplay or infrastructure."
    ;;
esac

case "$REPO_MODE" in
  auto|single-project|monorepo)
    ;;
  *)
    fail "Unsupported --repo-mode '$REPO_MODE'. Use auto, single-project, or monorepo."
    ;;
esac

validate_file "$ROOT_DIR/Agents.md"
validate_file "$AIRROOT_DIR/Modules/XUUnity/README.md"
if [ -d "$ROOT_DIR/AIModules" ]; then
  HAS_AIMODULES=1
fi
if [ -d "$ROOT_DIR/AIModules/XUUnityInternal" ]; then
  HAS_XUUNITY_INTERNAL=1
fi

if [ "$REPO_MODE" = "auto" ]; then
  if [ "$HAS_XUUNITY_INTERNAL" = "1" ]; then
    REPO_MODE="monorepo"
  else
    REPO_MODE="single-project"
  fi
fi

PROJECT_DIR="$(resolve_path "$PROJECT_ARG")"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
ROUTER_PATH="$PROJECT_DIR/Agents.md"
LEGACY_PATH="$PROJECT_DIR/Agents.legacy.md"
REPO_ALIAS_PATH="$PROJECT_DIR/Agents.repo.md"
AIMODULES_ALIAS_PATH="$PROJECT_DIR/AIModules"
PROJECT_MEMORY_DIR="$PROJECT_DIR/Assets/AIOutput/ProjectMemory"
PROJECT_OUTPUT_DIR="$PROJECT_DIR/Assets/AIOutput"

REPO_ROUTER_REL="$(relative_path "$ROOT_DIR/Agents.md" "$PROJECT_DIR")"
AIRROOT_REL="$(relative_path "$AIRROOT_DIR" "$PROJECT_DIR")"
AIMODULES_REL="$(relative_path "$ROOT_DIR/AIModules" "$PROJECT_DIR")"

log "AI project init: $PROJECT_DIR"
log "Mode: $MODE"
log "Repo mode: $REPO_MODE"
if [ "$DRY_RUN" = "1" ]; then
  log "Dry run: enabled"
fi

if [ ! -d "$PROJECT_DIR" ]; then
  if [ "$MODE" = "--check" ]; then
    fail "Missing project directory: $PROJECT_DIR"
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would create project directory: $PROJECT_DIR"
  else
    mkdir -p "$PROJECT_DIR"
    log "Created project directory: $PROJECT_DIR"
  fi
fi

if [ "$MODE" = "--fix" ]; then
  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would ensure directory exists: $PROJECT_MEMORY_DIR"
    dry_log "would ensure directory exists: $PROJECT_OUTPUT_DIR"
  else
    mkdir -p "$PROJECT_MEMORY_DIR" "$PROJECT_OUTPUT_DIR"
  fi
fi

ensure_symlink "$REPO_ROUTER_REL" "$REPO_ALIAS_PATH"
if [ "$REPO_MODE" = "monorepo" ] && [ "$HAS_AIMODULES" = "1" ]; then
  ensure_symlink "$AIMODULES_REL" "$AIMODULES_ALIAS_PATH"
fi

if [ -f "$ROUTER_PATH" ]; then
  if router_is_managed "$ROUTER_PATH"; then
    if [ "$MODE" = "--fix" ] && [ "$ALLOW_MANAGED_REFRESH" = "1" ]; then
      write_router "$ROUTER_PATH" "$PROJECT_NAME" "$PROJECT_KIND" "$PRIORITY" "$REPO_ROUTER_REL" "$AIRROOT_REL" "$AIMODULES_REL" "$HAS_AIMODULES" "$REPO_MODE"
      if [ "$DRY_RUN" != "1" ]; then
        log "Refreshed managed router: $ROUTER_PATH"
      fi
    elif [ "$MODE" = "--fix" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "managed router already exists and would not be refreshed without --refresh-managed-router: $ROUTER_PATH"
        goto_router_done=1
      else
        fail "Managed router already exists: $ROUTER_PATH
Refusing to refresh it without explicit approval.
Re-run with --refresh-managed-router if you want to rewrite the managed router."
      fi
    fi
  else
    if [ "$MODE" = "--check" ] || [ "$ALLOW_ADOPT_EXISTING" != "1" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "unmanaged router exists and would not be replaced without --adopt-existing-router: $ROUTER_PATH"
        goto_router_done=1
      else
        fail "Project router exists and is not managed by AIRoot/scripts/init_ai_project.sh: $ROUTER_PATH
Refusing to modify an existing project router without explicit approval.
Read the current router, decide whether to merge or replace it, then re-run with --adopt-existing-router only if replacement is approved."
      fi
    fi

    if [ "${goto_router_done:-0}" = "1" ]; then
      :
    elif [ -e "$LEGACY_PATH" ]; then
      fail "Cannot preserve existing router because backup already exists: $LEGACY_PATH"
    elif [ "$DRY_RUN" = "1" ]; then
      dry_log "would preserve existing unmanaged router as legacy backup: $LEGACY_PATH"
      write_router "$ROUTER_PATH" "$PROJECT_NAME" "$PROJECT_KIND" "$PRIORITY" "$REPO_ROUTER_REL" "$AIRROOT_REL" "$AIMODULES_REL" "$HAS_AIMODULES" "$REPO_MODE"
    fi
    if [ "${goto_router_done:-0}" != "1" ] && [ "$DRY_RUN" != "1" ]; then
      mv "$ROUTER_PATH" "$LEGACY_PATH"
      log "Preserved existing router as legacy backup: $LEGACY_PATH"
      write_router "$ROUTER_PATH" "$PROJECT_NAME" "$PROJECT_KIND" "$PRIORITY" "$REPO_ROUTER_REL" "$AIRROOT_REL" "$AIMODULES_REL" "$HAS_AIMODULES" "$REPO_MODE"
      log "Created managed router: $ROUTER_PATH"
    fi
  fi
else
  if [ "$MODE" = "--check" ]; then
    fail "Missing project router: $ROUTER_PATH"
  fi

  write_router "$ROUTER_PATH" "$PROJECT_NAME" "$PROJECT_KIND" "$PRIORITY" "$REPO_ROUTER_REL" "$AIRROOT_REL" "$AIMODULES_REL" "$HAS_AIMODULES" "$REPO_MODE"
  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would create managed router: $ROUTER_PATH"
  else
    log "Created managed router: $ROUTER_PATH"
  fi
fi

if [ "$DRY_RUN" != "1" ]; then
  validate_file "$PROJECT_OUTPUT_DIR"
  validate_file "$PROJECT_MEMORY_DIR"
  validate_file "$ROUTER_PATH"
  if [ "$REPO_MODE" = "monorepo" ] && [ "$HAS_AIMODULES" = "1" ]; then
    validate_file "$AIMODULES_ALIAS_PATH"
  fi
fi

log "AI project init complete."
