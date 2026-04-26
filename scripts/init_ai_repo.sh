#!/usr/bin/env bash

set -euo pipefail

AIRROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ROOT_DIR=""
MODE="--fix"
REPO_MODE="auto"
REPO_NAME=""
ALLOW_MANAGED_REFRESH=0
ALLOW_ADOPT_EXISTING=0
WITH_XUUNITY_INTERNAL_OVERLAY=0
REFRESH_MANAGED_OVERLAY=0
DRY_RUN=0
HOST_ROOT_ARG=""

usage() {
  cat <<'EOF'
Usage:
  bash AIRoot/scripts/init_ai_repo.sh [--host-root <path>] [--repo-mode auto|single-project|monorepo] [--repo-name "CustomName"] [--with-xuunity-internal-overlay] [--refresh-managed-router] [--refresh-managed-overlay] [--adopt-existing-router] [--dry-run] [--check|--fix]

Examples:
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode monorepo --with-xuunity-internal-overlay
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

resolve_root_dir() {
  local value="$1"

  if [ -z "$value" ]; then
    pwd -P
    return 0
  fi

  python3 - "$value" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
}

path_contains() {
  local root="$1"
  local child="$2"

  python3 - "$root" "$child" <<'PY'
import os
import sys

root = os.path.realpath(sys.argv[1])
child = os.path.realpath(sys.argv[2])
print("1" if os.path.commonpath([root, child]) == root else "0")
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

validate_host_root() {
  local contains
  local airroot_rel

  [ -n "$ROOT_DIR" ] || fail "Internal error: ROOT_DIR is empty"
  [ "$ROOT_DIR" != "$AIRROOT_DIR" ] || fail "Host root resolves to the AIRoot repo itself: $ROOT_DIR
Run setup from the host repo root that contains AIRoot, or pass --host-root <host-repo-root> explicitly."

  contains="$(path_contains "$ROOT_DIR" "$AIRROOT_DIR")"
  [ "$contains" = "1" ] || fail "Host root does not contain AIRoot: $ROOT_DIR
AIRoot location: $AIRROOT_DIR
The host root must be the repo that contains AIRoot as a subdirectory."

  airroot_rel="$(relative_path "$AIRROOT_DIR" "$ROOT_DIR")"
  case "$airroot_rel" in
    ../*|..)
      fail "AIRoot must be inside the selected host root.
Host root: $ROOT_DIR
AIRoot location: $AIRROOT_DIR"
      ;;
  esac
}

validate_file() {
  local path="$1"
  [ -e "$path" ] || fail "Missing: $path"
}

router_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_repo\.sh -->$' "$path"
}

overlay_file_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_repo\.sh overlay -->$' "$path"
}

report_file_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq 'Managed by (scripts|AIRoot/scripts)/init_ai_repo\.sh report-scaffold|"managed_by":[[:space:]]*"(scripts|AIRoot/scripts)/init_ai_repo\.sh report-scaffold"' "$path"
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

write_aimodules_readme() {
  local path="$1"
  cat > "$path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh overlay -->
# Host-Local AI Modules

## Purpose
This directory holds host-local AI overlays for \`$REPO_NAME\`.
Load these modules only after the public \`AIRoot\` core when the task needs repo-specific reusable routing or internal knowledge.

## Active Modules
- \`XUUnityInternal/\` -> monorepo-internal overlay for \`xuunity\`

## Rules
- Keep public-safe reusable guidance in \`AIRoot/\`.
- Keep repo-specific reusable guidance in \`AIModules/\`.
- Keep project-only truth in each project's \`Assets/AIOutput/ProjectMemory/\`.
- Keep mutable reports in \`AIOutput/\` or project-local \`Assets/AIOutput/\`, not here.
EOF
}

write_xuunity_internal_readme() {
  local path="$1"
  cat > "$path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh overlay -->
# XUUnity Internal Overlay

## Purpose
This directory is the host-local \`xuunity\` overlay for \`$REPO_NAME\`.
Load it after \`AIRoot/Modules/XUUnity/\` and before project-local memory when the task needs repo-specific routing, workspace selection, validation targeting, or reusable internal knowledge.

## Entry Point
- \`start_session.md\`

## Starter Knowledge Files
- \`knowledge/host_topology.md\`
- \`knowledge/validation_paths.md\`

## Rules
- Keep this overlay reusable across projects in the current host.
- Keep project-only facts out of this tree.
- Add explicit trigger or entrypoint references for every new knowledge file you introduce here.
EOF
}

write_xuunity_internal_start_session() {
  local path="$1"
  cat > "$path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh overlay -->
# XUUnity Internal Start Session Overlay

## Purpose
Apply host-local routing rules for \`$REPO_NAME\` after the public \`xuunity\` core is loaded.

## Load Order
1. Repo router at \`Agents.md\`
2. Public core at \`AIRoot/Modules/XUUnity/\`
3. This file
4. Narrow host-local knowledge files from \`knowledge/\` using the trigger rules below
5. Target project router
6. Target project memory

## Knowledge File Selection
- Load \`knowledge/host_topology.md\` when the task needs:
  - canonical source versus consumer selection
  - nested repo boundary awareness
  - project ownership resolution across multiple workspaces
  - repo-specific workspace exceptions
- Load \`knowledge/validation_paths.md\` when the task needs:
  - validation target selection
  - authoring-versus-validation workspace separation
  - release-proof interpretation for local-only or auxiliary workspaces
- Load both files when a task spans implementation plus validation planning.

## Routing Rules
- Resolve the concrete target project before narrowing task context.
- Keep shared public guidance in \`AIRoot/Modules/XUUnity/\`.
- Keep reusable host-specific guidance in this overlay.
- Keep project-only truth in \`Assets/AIOutput/ProjectMemory/\`.
- Keep mutable reports out of this overlay.
EOF
}

write_xuunity_internal_host_topology() {
  local path="$1"
  cat > "$path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh overlay -->
# Host Topology

## Purpose
Describe the reusable workspace map for \`$REPO_NAME\`.
Update this file when canonical source projects, consumer validation workspaces, or nested repo boundaries change.

## Fill In
- Repo root solution or main workspace entrypoint
- Canonical source projects
- Consumer validation projects
- Any embedded-copy or divergent consumer exceptions
- Any nested git boundaries that affect rollout

## Rules
- Package or shared-source fixes should start in canonical source projects.
- Consumer workspaces should mainly be used for repro and validation unless they intentionally own divergent code.
- If a workspace is local-only or ignored by git, say that explicitly here.
EOF
}

write_xuunity_internal_validation_paths() {
  local path="$1"
  cat > "$path" <<EOF
<!-- Managed by AIRoot/scripts/init_ai_repo.sh overlay -->
# Validation Paths

## Purpose
Capture host-level validation routing for \`$REPO_NAME\`.
Update this file when the best authoring workspace, representative consumer validation targets, or release-proof rules change.

## Fill In
- Authoring workspace or solution entrypoint
- Primary consumer validation targets
- Engine-line-specific validation preferences
- Local-only workspaces that are useful evidence but not tracked release proof

## Rules
- Separate implementation targets from validation targets.
- Do not treat one consumer workspace as proof for all supported engine lines unless the host explicitly says so.
- Note any local-only or ignored workspace so later reports do not overstate release evidence.
EOF
}

ensure_overlay_file() {
  local path="$1"
  local writer_fn="$2"

  if [ -e "$path" ]; then
    if overlay_file_is_managed "$path" && [ "$REFRESH_MANAGED_OVERLAY" = "1" ]; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "would refresh managed overlay file: $path"
      else
        "$writer_fn" "$path"
        log "Refreshed managed overlay file: $path"
      fi
      return 0
    fi

    if overlay_file_is_managed "$path"; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "managed overlay file already exists and would not be refreshed without --refresh-managed-overlay: $path"
      else
        log "Kept existing managed overlay file: $path"
      fi
    else
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "unmanaged overlay file already exists and would be left unchanged: $path"
      else
        log "Kept existing unmanaged overlay file: $path"
      fi
    fi
    return 0
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would create overlay file: $path"
    return 0
  fi

  if [ "$MODE" = "--check" ]; then
    fail "Missing overlay file: $path"
  fi

  "$writer_fn" "$path"
  log "Created overlay file: $path"
}

ensure_xuunity_internal_overlay() {
  local aimodules_dir="$ROOT_DIR/AIModules"
  local overlay_dir="$aimodules_dir/XUUnityInternal"
  local knowledge_dir="$overlay_dir/knowledge"

  ensure_dir "$aimodules_dir"
  ensure_dir "$overlay_dir"
  ensure_dir "$knowledge_dir"

  ensure_overlay_file "$aimodules_dir/README.md" write_aimodules_readme
  ensure_overlay_file "$overlay_dir/README.md" write_xuunity_internal_readme
  ensure_overlay_file "$overlay_dir/start_session.md" write_xuunity_internal_start_session
  ensure_overlay_file "$knowledge_dir/host_topology.md" write_xuunity_internal_host_topology
  ensure_overlay_file "$knowledge_dir/validation_paths.md" write_xuunity_internal_validation_paths
}

write_reports_system_readme() {
  local path="$1"
  cat > "$path" <<'EOF'
<!-- Managed by AIRoot/scripts/init_ai_repo.sh report-scaffold -->
# System Reports

## Purpose
Store host-level AI system reports, evaluation baselines, and canonical health evidence.

## Canonical Extraction Evidence
- `knowledge_extraction_eval_baseline_v1.md` only after approval
- `knowledge_extraction_eval_baseline_v1_run.json` only after a real evaluation run
- `knowledge_extraction_eval_latest_summary.json` only after a real evaluation run

## Rules
- Keep the current named extraction baseline here only after it is real.
- Bootstrap should create slots, not fake health evidence.
- Treat smoke or demo outputs as harness evidence, not production health proof.
EOF
}

write_reports_system_smoke_readme() {
  local path="$1"
  cat > "$path" <<'EOF'
<!-- Managed by AIRoot/scripts/init_ai_repo.sh report-scaffold -->
# Smoke Reports

## Purpose
Temporary smoke outputs for protocol harness validation.

## Rules
- Keep only non-authoritative smoke or demo runs here.
- Do not treat files in this directory as release-proof extraction health evidence.
- Promote only approved canonical summaries to `../`.
EOF
}

write_reports_review_artifacts_readme() {
  local path="$1"
  cat > "$path" <<'EOF'
<!-- Managed by AIRoot/scripts/init_ai_repo.sh report-scaffold -->
# Review Artifacts

## Purpose
Reusable host-level review artifacts that may inform future system or cross-project work.

## Rules
- Keep only artifacts that remain useful beyond a single task.
- Do not store mutable project-local findings here when they belong under a specific project.
EOF
}

write_reports_research_readme() {
  local path="$1"
  cat > "$path" <<'EOF'
<!-- Managed by AIRoot/scripts/init_ai_repo.sh report-scaffold -->
# Research Reports

## Purpose
Host-level research-watch outputs and external change tracking.

## Rules
- Keep time-sensitive research outputs here.
- Refresh or archive stale research rather than treating it as durable protocol truth.
EOF
}

write_extraction_baseline_slot() {
  local path="$1"
  cat > "$path" <<'EOF'
<!-- Managed by AIRoot/scripts/init_ai_repo.sh report-scaffold -->
# Knowledge Extraction Evaluation Baseline Slot

## Status
- State: waiting_for_real_baseline
- Canonical baseline file: `knowledge_extraction_eval_baseline_v1.md`

## Purpose
This file reserves the baseline slot for the current host repo.
Do not treat this file as baseline evidence.

## Real Evidence Targets
- `knowledge_extraction_eval_baseline_v1.md`
- `knowledge_extraction_eval_baseline_v1_run.json`
- `knowledge_extraction_eval_latest_summary.json`

## Next Step
1. Run the golden extraction evaluation harness from `AIRoot/Operations/`.
2. Score the cases with human review.
3. Write the approved baseline to `knowledge_extraction_eval_baseline_v1.md`.
EOF
}

write_extraction_run_slot_json() {
  local path="$1"
  cat > "$path" <<'EOF'
{
  "managed_by": "AIRoot/scripts/init_ai_repo.sh report-scaffold",
  "status": "waiting_for_real_run",
  "canonical_targets": [
    "knowledge_extraction_eval_baseline_v1_run.json",
    "knowledge_extraction_eval_latest_summary.json"
  ],
  "source_case_pack": "AIRoot/Operations/XUUNITY_KNOWLEDGE_EXTRACTION_GOLDEN_CASES.json",
  "note": "Bootstrap creates this slot so the host knows which real extraction evidence files should appear after evaluation."
}
EOF
}

ensure_report_file() {
  local path="$1"
  local writer_fn="$2"

  if [ -e "$path" ]; then
    if report_file_is_managed "$path"; then
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "managed report scaffold already exists and would be left unchanged: $path"
      else
        log "Kept existing managed report scaffold: $path"
      fi
    else
      if [ "$DRY_RUN" = "1" ]; then
        dry_log "unmanaged report file already exists and would be left unchanged: $path"
      else
        log "Kept existing unmanaged report file: $path"
      fi
    fi
    return 0
  fi

  if [ "$MODE" = "--check" ]; then
    fail "Missing report scaffold file: $path"
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would create report scaffold file: $path"
    return 0
  fi

  "$writer_fn" "$path"
  log "Created report scaffold file: $path"
}

ensure_report_scaffold() {
  local reports_system_dir="$AI_OUTPUT_REPORTS_DIR/System"
  local reports_smoke_dir="$reports_system_dir/Smoke"
  local reports_review_dir="$AI_OUTPUT_REPORTS_DIR/ReviewArtifacts"
  local reports_research_dir="$AI_OUTPUT_REPORTS_DIR/Research"

  ensure_dir "$reports_system_dir"
  ensure_dir "$reports_smoke_dir"
  ensure_dir "$reports_review_dir"
  ensure_dir "$reports_research_dir"

  if [ -f "$reports_system_dir/knowledge_extraction_eval_baseline_v1.md" ] && report_file_is_managed "$reports_system_dir/knowledge_extraction_eval_baseline_v1.md"; then
    if [ "$MODE" = "--fix" ] && [ "$DRY_RUN" != "1" ]; then
      rm "$reports_system_dir/knowledge_extraction_eval_baseline_v1.md"
      log "Removed legacy managed baseline placeholder: $reports_system_dir/knowledge_extraction_eval_baseline_v1.md"
    elif [ "$DRY_RUN" = "1" ]; then
      dry_log "would remove legacy managed baseline placeholder: $reports_system_dir/knowledge_extraction_eval_baseline_v1.md"
    fi
  fi

  if [ -f "$reports_system_dir/knowledge_extraction_eval_baseline_v1_run.json" ] && report_file_is_managed "$reports_system_dir/knowledge_extraction_eval_baseline_v1_run.json"; then
    if [ "$MODE" = "--fix" ] && [ "$DRY_RUN" != "1" ]; then
      rm "$reports_system_dir/knowledge_extraction_eval_baseline_v1_run.json"
      log "Removed legacy managed run placeholder: $reports_system_dir/knowledge_extraction_eval_baseline_v1_run.json"
    elif [ "$DRY_RUN" = "1" ]; then
      dry_log "would remove legacy managed run placeholder: $reports_system_dir/knowledge_extraction_eval_baseline_v1_run.json"
    fi
  fi

  if [ -f "$reports_system_dir/knowledge_extraction_eval_latest_summary.json" ] && report_file_is_managed "$reports_system_dir/knowledge_extraction_eval_latest_summary.json"; then
    if [ "$MODE" = "--fix" ] && [ "$DRY_RUN" != "1" ]; then
      rm "$reports_system_dir/knowledge_extraction_eval_latest_summary.json"
      log "Removed legacy managed latest-summary placeholder: $reports_system_dir/knowledge_extraction_eval_latest_summary.json"
    elif [ "$DRY_RUN" = "1" ]; then
      dry_log "would remove legacy managed latest-summary placeholder: $reports_system_dir/knowledge_extraction_eval_latest_summary.json"
    fi
  fi

  ensure_report_file "$reports_system_dir/README.md" write_reports_system_readme
  ensure_report_file "$reports_smoke_dir/README.md" write_reports_system_smoke_readme
  ensure_report_file "$reports_review_dir/README.md" write_reports_review_artifacts_readme
  ensure_report_file "$reports_research_dir/README.md" write_reports_research_readme
  ensure_report_file "$reports_system_dir/knowledge_extraction_eval_baseline_slot.md" write_extraction_baseline_slot
  ensure_report_file "$reports_system_dir/knowledge_extraction_eval_run_slot.json" write_extraction_run_slot_json
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

## Fast Shortcuts
- \`xuunity fix this bug\`
- \`xuunity refactor this code\`
- \`xuunity review the git change\`
- \`xuunity sdk review this integration\`
- \`xuunity native review this bridge\`
- \`xuunity feature plan this flow\`
- \`xuunity product explain this feature\`
- \`xuunity product health this project\`
- \`xuunity project memory freshness this project\`

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
    --host-root)
      [ "$#" -ge 2 ] || fail "Missing value for --host-root"
      HOST_ROOT_ARG="$2"
      shift 2
      ;;
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
    --with-xuunity-internal-overlay)
      WITH_XUUNITY_INTERNAL_OVERLAY=1
      shift
      ;;
    --refresh-managed-router)
      ALLOW_MANAGED_REFRESH=1
      shift
      ;;
    --refresh-managed-overlay)
      REFRESH_MANAGED_OVERLAY=1
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

ROOT_DIR="$(resolve_root_dir "$HOST_ROOT_ARG")"
validate_host_root
[ -n "$REPO_NAME" ] || REPO_NAME="$(basename "$ROOT_DIR")"

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
  ensure_report_scaffold
  if [ "$WITH_XUUNITY_INTERNAL_OVERLAY" = "1" ]; then
    ensure_xuunity_internal_overlay
  fi
fi

if [ "$MODE" = "--check" ]; then
  ensure_dir "$AI_OUTPUT_DIR"
  ensure_dir "$AI_OUTPUT_OPERATIONS_DIR"
  ensure_dir "$AI_OUTPUT_REPORTS_DIR"
  ensure_dir "$AI_OUTPUT_REGISTRY_DIR"
  ensure_report_scaffold
fi

if [ "$MODE" = "--check" ] && [ "$WITH_XUUNITY_INTERNAL_OVERLAY" = "1" ]; then
  ensure_xuunity_internal_overlay
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
