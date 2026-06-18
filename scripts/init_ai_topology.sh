#!/usr/bin/env bash

set -euo pipefail

AIRROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ROOT_DIR=""
MODE="--fix"
PROFILE=""
REPO_NAME=""
PROJECT_KIND="unity_project"
PRIORITY="Stability > Performance > Maintainability"
DRY_RUN=0
ALLOW_MANAGED_REFRESH=0
ALLOW_ADOPT_EXISTING=0
ALLOW_PRESERVE_EXISTING=0
REFRESH_MANAGED_OVERLAY=0
HOST_ROOT_ARG=""
PYTHON_BIN=""
declare -a PROJECTS=()

usage() {
  cat <<'EOF'
Usage:
  bash AIRoot/scripts/init_ai_topology.sh [--host-root <path>] --profile <single_project_default|monorepo_overlay_default> [--project <path-or-name>]... [--kind <project-kind>] [--priority "custom priority"] [--repo-name "CustomName"] [--refresh-managed-router] [--refresh-managed-overlay] [--preserve-existing-router] [--adopt-existing-router] [--dry-run] [--check|--fix]

Examples:
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --project MyGame --dry-run
  bash AIRoot/scripts/init_ai_topology.sh --profile monorepo_overlay_default --project ProjectA --project ProjectB
  bash AIRoot/scripts/init_ai_topology.sh --profile monorepo_overlay_default --dry-run
EOF
}

log() {
  printf '%s\n' "$1"
}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

normalize_bash_path() {
  printf '%s' "$1" | tr '\\' '/'
}

resolve_python_bin() {
  local candidate
  local normalized
  local resolved

  for candidate in "${AIRROOT_PYTHON:-}" "${PYTHON:-}" python3 python; do
    [ -n "$candidate" ] || continue
    normalized="$(normalize_bash_path "$candidate")"
    if resolved="$(command -v "$normalized" 2>/dev/null)" && "$resolved" - <<'PY' >/dev/null 2>&1; then
import sys
raise SystemExit(0 if sys.version_info[0] >= 3 else 1)
PY
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  fail "Python 3 was not found. Set AIRROOT_PYTHON or PYTHON to a Python 3 interpreter path."
}

is_supported_project_kind() {
  case "$1" in
    unity_project|unity_package_source|unity_native_package_source|unity_package_validation_consumer|unity_embedded_package_validation_consumer|unity_package_validation_demo|unity_package_and_editor_tooling_source|public_unity_mcp_tooling|infrastructure|tooling|gameplay)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
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

  "$PYTHON_BIN" - "$value" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
}

path_contains() {
  local root="$1"
  local child="$2"

  "$PYTHON_BIN" - "$root" "$child" <<'PY'
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

  "$PYTHON_BIN" - "$target" "$start" <<'PY'
import os
import sys

print(os.path.relpath(sys.argv[1], sys.argv[2]))
PY
}

resolve_project_path() {
  local value="$1"

  "$PYTHON_BIN" - "$ROOT_DIR" "$value" <<'PY'
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

repo_router_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_repo\.sh -->$' "$path"
}

project_router_is_managed() {
  local path="$1"
  [ -f "$path" ] && grep -Eq '^<!-- Managed by (scripts|AIRoot/scripts)/init_ai_project\.sh -->$' "$path"
}

router_warning_block() {
  local warnings=""
  local project_count=0
  local project_path
  local project

  if [ "$ALLOW_PRESERVE_EXISTING" = "1" ] && [ -f "$ROOT_DIR/Agents.md" ] && ! repo_router_is_managed "$ROOT_DIR/Agents.md"; then
    warnings="${warnings}  - preserved_unmanaged_repo_router"$'\n'
  fi

  set +u
  project_count="${#PROJECTS[@]}"
  set -u

  if [ "$ALLOW_PRESERVE_EXISTING" = "1" ] && [ "$project_count" -gt 0 ]; then
    for project in "${PROJECTS[@]}"; do
      project_path="$(resolve_project_path "$project")"
      if [ -f "$project_path/Agents.md" ] && ! project_router_is_managed "$project_path/Agents.md"; then
        warnings="${warnings}  - preserved_unmanaged_project_router: ${project}"$'\n'
      fi
    done
  fi

  if [ -n "$warnings" ]; then
    printf '%s' "${warnings%$'\n'}"
  else
    printf '  []'
  fi
}

preflight_router_conflicts() {
  local project_count=0
  local project_path
  local project

  if [ "$ALLOW_ADOPT_EXISTING" = "1" ] || [ "$ALLOW_PRESERVE_EXISTING" = "1" ]; then
    return 0
  fi

  if [ -f "$ROOT_DIR/Agents.md" ] && ! repo_router_is_managed "$ROOT_DIR/Agents.md"; then
    fail "Repo router exists and is not managed by AIRoot/scripts/init_ai_repo.sh: $ROOT_DIR/Agents.md
Refusing topology setup before writing scaffold or registry files.
Use --preserve-existing-router to leave it unchanged, or --adopt-existing-router only if replacement is approved."
  fi

  set +u
  project_count="${#PROJECTS[@]}"
  set -u

  if [ "$project_count" -gt 0 ]; then
    for project in "${PROJECTS[@]}"; do
      project_path="$(resolve_project_path "$project")"
      if [ -f "$project_path/Agents.md" ] && ! project_router_is_managed "$project_path/Agents.md"; then
        fail "Project router exists and is not managed by AIRoot/scripts/init_ai_project.sh: $project_path/Agents.md
Refusing topology setup before writing scaffold or registry files.
Use --preserve-existing-router to leave it unchanged, or --adopt-existing-router only if replacement is approved."
      fi
    done
  fi
}

write_topology_metadata() {
  local metadata_path="$ROOT_DIR/AIOutput/Registry/host_topology.yaml"
  local repo_mode="$1"
  local with_overlay="$2"
  local project_list=""
  local project_count=0
  local projects_snapshot=()
  local project
  local warnings_block

  if [ "$MODE" = "--check" ]; then
    [ -f "$metadata_path" ] || fail "Missing topology metadata: $metadata_path"
    return 0
  fi

  set +u
  project_count="${#PROJECTS[@]}"
  projects_snapshot=("${PROJECTS[@]}")
  set -u

  if [ "$project_count" -gt 0 ]; then
    for project in "${projects_snapshot[@]}"; do
      project_list="${project_list}  - ${project}"$'\n'
    done
  fi

  if [ -z "$project_list" ]; then
    project_list="  []"$'\n'
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would write topology metadata: $metadata_path"
    return 0
  fi

  warnings_block="$(router_warning_block)"

  cat > "$metadata_path" <<EOF
profile_id: $PROFILE
repo_mode: $repo_mode
storage_profile: project-local
router_mode: repo-and-project
project_link_mode: direct
solution_mode: none
active_repo_router: Agents.md
active_project_memory_root: <Project>/Assets/AIOutput/ProjectMemory/
active_project_reports_root: <Project>/Assets/AIOutput/
active_project_skill_overrides_root: <Project>/Assets/AIOutput/ProjectMemory/SkillOverrides/
internal_overlay_root: $( [ "$with_overlay" = "1" ] && printf 'AIModules/XUUnityInternal/' || printf 'none' )
routed_projects:
${project_list%$'\n'}
warnings:
$warnings_block
EOF

  log "Wrote topology metadata: $metadata_path"
}

write_setup_status() {
  local status_path="$ROOT_DIR/AIOutput/Registry/setup_status.yaml"
  local repo_mode="$1"
  local with_overlay="$2"
  local project_list=""
  local project_count=0
  local projects_snapshot=()
  local project
  local warnings_block=""
  local airroot_rel
  local timestamp

  if [ "$MODE" = "--check" ]; then
    [ -f "$status_path" ] || fail "Missing setup status: $status_path"
    return 0
  fi

  set +u
  project_count="${#PROJECTS[@]}"
  projects_snapshot=("${PROJECTS[@]}")
  set -u

  if [ "$project_count" -gt 0 ]; then
    for project in "${projects_snapshot[@]}"; do
      project_list="${project_list}  - ${project}"$'\n'
    done
  else
    project_list="  []"$'\n'
    warnings_block=$'  - repo_only_setup_no_projects'
  fi

  if [ -z "$warnings_block" ]; then
    warnings_block="$(router_warning_block)"
  else
    local router_warnings
    router_warnings="$(router_warning_block)"
    if [ "$router_warnings" != "  []" ]; then
      warnings_block="${warnings_block}"$'\n'"$router_warnings"
    fi
  fi

  if [ "$DRY_RUN" = "1" ]; then
    dry_log "would write setup status: $status_path"
    return 0
  fi

  airroot_rel="$(relative_path "$AIRROOT_DIR" "$ROOT_DIR")"
  timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  cat > "$status_path" <<EOF
setup_state: provisioned
host_root: $ROOT_DIR
airroot_root: ${airroot_rel}/
profile_id: $PROFILE
repo_mode: $repo_mode
overlay_expected: $( [ "$with_overlay" = "1" ] && printf 'true' || printf 'false' )
overlay_root: $( [ "$with_overlay" = "1" ] && printf 'AIModules/XUUnityInternal/' || printf 'none' )
report_scaffold_status: scaffolded
project_memory_baseline_status: seeded_or_existing
last_provisioned_at: "$timestamp"
routed_projects:
${project_list%$'\n'}
warnings:
$warnings_block
EOF

  log "Wrote setup status: $status_path"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host-root)
      [ "$#" -ge 2 ] || fail "Missing value for --host-root"
      HOST_ROOT_ARG="$2"
      shift 2
      ;;
    --profile)
      [ "$#" -ge 2 ] || fail "Missing value for --profile"
      PROFILE="$2"
      shift 2
      ;;
    --project)
      [ "$#" -ge 2 ] || fail "Missing value for --project"
      PROJECTS+=("$2")
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
    --repo-name)
      [ "$#" -ge 2 ] || fail "Missing value for --repo-name"
      REPO_NAME="$2"
      shift 2
      ;;
    --refresh-managed-router)
      ALLOW_MANAGED_REFRESH=1
      shift
      ;;
    --refresh-managed-overlay)
      REFRESH_MANAGED_OVERLAY=1
      shift
      ;;
    --preserve-existing-router)
      ALLOW_PRESERVE_EXISTING=1
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

PYTHON_BIN="$(resolve_python_bin)"
ROOT_DIR="$(resolve_root_dir "$HOST_ROOT_ARG")"
validate_host_root
[ -n "$REPO_NAME" ] || REPO_NAME="$(basename "$ROOT_DIR")"
[ -n "$PROFILE" ] || fail "Missing required --profile argument"

case "$PROFILE" in
  single_project_default)
    REPO_MODE="single-project"
    WITH_OVERLAY=0
    ;;
  monorepo_overlay_default)
    REPO_MODE="monorepo"
    WITH_OVERLAY=1
    ;;
  *)
    fail "Unsupported --profile '$PROFILE'. Use single_project_default or monorepo_overlay_default."
    ;;
esac

if ! is_supported_project_kind "$PROJECT_KIND"; then
  fail "Unsupported --kind '$PROJECT_KIND'. Use a supported routing kind such as unity_project, unity_package_source, unity_package_validation_consumer, unity_package_and_editor_tooling_source, public_unity_mcp_tooling, infrastructure, or tooling."
fi

REPO_CMD=(bash "$AIRROOT_DIR/scripts/init_ai_repo.sh" --host-root "$ROOT_DIR" --repo-mode "$REPO_MODE" "$MODE")
if [ -n "$REPO_NAME" ]; then
  REPO_CMD+=(--repo-name "$REPO_NAME")
fi
if [ "$WITH_OVERLAY" = "1" ]; then
  REPO_CMD+=(--with-xuunity-internal-overlay)
fi
if [ "$ALLOW_MANAGED_REFRESH" = "1" ]; then
  REPO_CMD+=(--refresh-managed-router)
fi
if [ "$REFRESH_MANAGED_OVERLAY" = "1" ]; then
  REPO_CMD+=(--refresh-managed-overlay)
fi
if [ "$ALLOW_ADOPT_EXISTING" = "1" ]; then
  REPO_CMD+=(--adopt-existing-router)
fi
if [ "$ALLOW_PRESERVE_EXISTING" = "1" ]; then
  REPO_CMD+=(--preserve-existing-router)
fi
if [ "$DRY_RUN" = "1" ]; then
  REPO_CMD+=(--dry-run)
fi

preflight_router_conflicts

log "AI topology init: $ROOT_DIR"
log "Profile: $PROFILE"
log "Repo mode: $REPO_MODE"
if [ "$DRY_RUN" = "1" ]; then
  log "Dry run: enabled"
fi

"${REPO_CMD[@]}"
write_topology_metadata "$REPO_MODE" "$WITH_OVERLAY"

set +u
PROJECT_COUNT="${#PROJECTS[@]}"
PROJECTS_SNAPSHOT=("${PROJECTS[@]}")
set -u

if [ "$PROJECT_COUNT" -gt 0 ]; then
  for project in "${PROJECTS_SNAPSHOT[@]}"; do
    PROJECT_CMD=(
      bash "$AIRROOT_DIR/scripts/init_ai_project.sh"
      --host-root "$ROOT_DIR"
      --project "$project"
      --kind "$PROJECT_KIND"
      --priority "$PRIORITY"
      --repo-mode "$REPO_MODE"
      "$MODE"
    )
    if [ "$ALLOW_MANAGED_REFRESH" = "1" ]; then
      PROJECT_CMD+=(--refresh-managed-router)
    fi
    if [ "$ALLOW_ADOPT_EXISTING" = "1" ]; then
      PROJECT_CMD+=(--adopt-existing-router)
    fi
    if [ "$ALLOW_PRESERVE_EXISTING" = "1" ]; then
      PROJECT_CMD+=(--preserve-existing-router)
    fi
    if [ "$DRY_RUN" = "1" ]; then
      PROJECT_CMD+=(--dry-run)
    fi
    "${PROJECT_CMD[@]}"
  done
fi

write_setup_status "$REPO_MODE" "$WITH_OVERLAY"

log "AI topology init complete."
