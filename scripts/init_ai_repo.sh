#!/usr/bin/env bash

set -euo pipefail

AIRROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ROOT_DIR="$(cd "$AIRROOT_DIR/.." && pwd -P)"
MODE="--fix"
REPO_MODE="auto"
REPO_NAME="$(basename "$ROOT_DIR")"
ALLOW_MANAGED_REFRESH=0
ALLOW_ADOPT_EXISTING=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  bash AIRoot/scripts/init_ai_repo.sh [--repo-mode auto|single-project|monorepo] [--repo-name "CustomName"] [--refresh-managed-router] [--adopt-existing-router] [--dry-run] [--check|--fix]

Examples:
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo --refresh-managed-router
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

validate_file() {
  local path="$1"
  [ -e "$path" ] || fail "Missing: $path"
}

router_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_repo\.sh -->$' "$path"
}

ensure_dir() {
  local path="$1"

  if [ -d "$path" ]; then
    return 0
  fi

  if [ "$MODE" = "--check" ]; then
    fail "Missing directory: $path"
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would ensure directory exists: $path"
    return 0
  fi

  mkdir -p "$path"
  log "Created directory: $path"
}

write_repo_router() {
  local router_path="$1"
  local repo_name="$2"
  local repo_mode="$3"

  local title="Repo Agent Router"
  local purpose_line="This file is the repo-level routing layer."
  local load_order_block
  local prompt_map_block
  local storage_block

  if [ "$repo_mode" = "monorepo" ]; then
    title="Monorepo Agent Router"
    purpose_line="This file is the repo-level routing layer for the host."
    load_order_block=$(cat <<'EOF'
1. This repo-level `Agents.md`
2. Shared protocol modules from `AIRoot/Modules/`, with `xuunity` loading public core from `AIRoot/Modules/XUUnity/`
3. Optional monorepo-internal overlay from `AIModules/XUUnityInternal/` when the host uses it
4. Other host-local prompt families from `AIModules/` when the selected protocol is host-local
5. Project-level `Agents.md`
6. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
7. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant
EOF
)
    prompt_map_block=$(cat <<'EOF'
- `xuunity` -> public core `AIRoot/Modules/XUUnity/` plus internal overlay `AIModules/XUUnityInternal/` when the host uses it
- optional host-local protocol families -> `AIModules/` when the host attaches them
EOF
)
    storage_block=$(cat <<'EOF'
- Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`.
- Project reports and drafts belong in `<Project>/Assets/AIOutput/`.
- Host-level setup, handoff, registry, and reports belong in `AIOutput/`.
- Public reusable `xuunity` guidance belongs in `AIRoot/Modules/XUUnity/`.
- Monorepo-internal shared `xuunity` guidance belongs in `AIModules/XUUnityInternal/`.
EOF
)
  else
    load_order_block=$(cat <<'EOF'
1. This repo-level `Agents.md`
2. Shared protocol modules from `AIRoot/Modules/`
3. Project-level `Agents.md`
4. Project-local memory from `<Project>/Assets/AIOutput/ProjectMemory/`
5. Project-local previous AI outputs from `<Project>/Assets/AIOutput/` when they are relevant
EOF
)
    prompt_map_block=$(cat <<'EOF'
- `xuunity` -> `AIRoot/Modules/XUUnity/`
- optional host-local protocol families -> `AIModules/` when the host attaches them
EOF
)
    storage_block=$(cat <<'EOF'
- Durable project-local guidance belongs in `<Project>/Assets/AIOutput/ProjectMemory/`.
- Project reports and drafts belong in `<Project>/Assets/AIOutput/`.
- Host-level setup, handoff, registry, and reports belong in `AIOutput/`.
- Public reusable `xuunity` guidance belongs in `AIRoot/Modules/XUUnity/`.
EOF
)
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would write managed repo router to $router_path using repo mode $repo_mode"
    return 0
  fi

  cat > "$router_path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh -->
# $title

## Purpose
$purpose_line
Keep it minimal.
Use it to select shared prompt families, define load order, and route project-local overrides.

## Host Context
- Repo: \`$repo_name\`
- Topology: \`$repo_mode\`
- Shared public core: \`AIRoot/Modules/XUUnity/\`

## Load Order
$load_order_block

## Routing Table
- Use \`xuunity\` as the default protocol for Unity implementation, review, refactoring, product-facing implementation explanation, SDK work, native work, runtime safety, startup, performance, and compliance.
- Use host-local protocol families only when the host intentionally attaches them under \`AIModules/\`.

## Prompt Family Map
$prompt_map_block

## Project Memory Override Rule
- Project-specific memory in \`<Project>/Assets/AIOutput/ProjectMemory/\` overrides shared prompts when there is a conflict.
- Do not move project-specific constraints into shared prompts.
- Historical reports in \`<Project>/Assets/AIOutput/\` are opt-in context and should be loaded only when relevant.

## AI Output Storage Rule
$storage_block

## Sensitive Data Protocol
- Treat project-specific intellectual property, internal architecture, business logic, and credentials as confidential by default.
- Never promote project-specific confidential details into shared prompts.
- Report sensitive config evidence using structure and redacted values only.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-mode)
      [ "$#" -ge 2 ] || fail "Missing value for --repo-mode"
      REPO_MODE="$2"
      shift 2
      ;;
    --repo-name)
      [ "$#" -ge 2 ] || fail "Missing value for --repo-name"
      REPO_NAME="$2"
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

case "$REPO_MODE" in
  auto|single-project|monorepo)
    ;;
  *)
    fail "Unsupported --repo-mode '$REPO_MODE'. Use auto, single-project, or monorepo."
    ;;
esac

validate_file "$AIRROOT_DIR/Modules/XUUnity/README.md"

if [ "$REPO_MODE" = "auto" ]; then
  if [ -d "$ROOT_DIR/AIModules/XUUnityInternal" ]; then
    REPO_MODE="monorepo"
  else
    REPO_MODE="single-project"
  fi
fi

ROUTER_PATH="$ROOT_DIR/Agents.md"
LEGACY_PATH="$ROOT_DIR/Agents.legacy.md"
AI_OUTPUT_DIR="$ROOT_DIR/AIOutput"
AI_OUTPUT_OPERATIONS_DIR="$ROOT_DIR/AIOutput/Operations"
AI_OUTPUT_REPORTS_DIR="$ROOT_DIR/AIOutput/Reports"
AI_OUTPUT_REGISTRY_DIR="$ROOT_DIR/AIOutput/Registry"

log "AI repo init: $ROOT_DIR"
log "Mode: $MODE"
log "Repo mode: $REPO_MODE"
if [ "$DRY_RUN" = "1" ]; then
  log "Dry run: enabled"
fi

if [ "$MODE" = "--fix" ]; then
  ensure_dir "$AI_OUTPUT_DIR"
  ensure_dir "$AI_OUTPUT_OPERATIONS_DIR"
  ensure_dir "$AI_OUTPUT_REPORTS_DIR"
  ensure_dir "$AI_OUTPUT_REGISTRY_DIR"
fi

if [ -f "$ROUTER_PATH" ]; then
  if router_is_managed "$ROUTER_PATH"; then
    if [ "$MODE" = "--fix" ] && [ "$ALLOW_MANAGED_REFRESH" = "1" ]; then
      write_repo_router "$ROUTER_PATH" "$REPO_NAME" "$REPO_MODE"
      if [ "$DRY_RUN" != "1" ]; then
        log "Refreshed managed repo router: $ROUTER_PATH"
      fi
    elif [ "$MODE" = "--fix" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "managed repo router already exists and would not be refreshed without --refresh-managed-router: $ROUTER_PATH"
      else
        fail "Managed repo router already exists: $ROUTER_PATH
Refusing to refresh it without explicit approval.
Re-run with --refresh-managed-router if you want to rewrite the managed repo router."
      fi
    fi
  else
    if [ "$MODE" = "--check" ] || [ "$ALLOW_ADOPT_EXISTING" != "1" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "unmanaged repo router exists and would not be replaced without --adopt-existing-router: $ROUTER_PATH"
      else
        fail "Repo router exists and is not managed by AIRoot/scripts/init_ai_repo.sh: $ROUTER_PATH
Refusing to modify an existing repo router without explicit approval.
Read the current router, decide whether to merge or replace it, then re-run with --adopt-existing-router only if replacement is approved."
      fi
    elif [ -e "$LEGACY_PATH" ]; then
      fail "Cannot preserve existing repo router because backup already exists: $LEGACY_PATH"
    elif [ "$DRY_RUN" = "1" ]; then
      dry_log "would preserve existing unmanaged repo router as legacy backup: $LEGACY_PATH"
      write_repo_router "$ROUTER_PATH" "$REPO_NAME" "$REPO_MODE"
    else
      mv "$ROUTER_PATH" "$LEGACY_PATH"
      log "Preserved existing repo router as legacy backup: $LEGACY_PATH"
      write_repo_router "$ROUTER_PATH" "$REPO_NAME" "$REPO_MODE"
      log "Created managed repo router: $ROUTER_PATH"
    fi
  fi
else
  if [ "$MODE" = "--check" ]; then
    fail "Missing repo router: $ROUTER_PATH"
  fi

  write_repo_router "$ROUTER_PATH" "$REPO_NAME" "$REPO_MODE"
  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would create managed repo router: $ROUTER_PATH"
  else
    log "Created managed repo router: $ROUTER_PATH"
  fi
fi

if [ "$DRY_RUN" != "1" ]; then
  validate_file "$AI_OUTPUT_DIR"
  validate_file "$AI_OUTPUT_OPERATIONS_DIR"
  validate_file "$AI_OUTPUT_REPORTS_DIR"
  validate_file "$AI_OUTPUT_REGISTRY_DIR"
  validate_file "$ROUTER_PATH"
fi

log "AI repo init complete."
