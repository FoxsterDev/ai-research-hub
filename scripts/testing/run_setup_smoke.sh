#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
AIRROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
PYTHON_BIN=""

log() {
  printf '\n== %s ==\n' "$1"
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

  fail "Python 3 was not found. Set AIRROOT_PYTHON or PYTHON."
}

make_host_fixture() {
  local host_root="$1"

  mkdir -p "$host_root/AIRoot/scripts" "$host_root/AIRoot/Modules/XUUnity"
  cp "$AIRROOT_DIR/scripts/init_ai_topology.sh" \
    "$AIRROOT_DIR/scripts/init_ai_repo.sh" \
    "$AIRROOT_DIR/scripts/init_ai_project.sh" \
    "$AIRROOT_DIR/scripts/routing_audit.py" \
    "$host_root/AIRoot/scripts/"
  printf '# XUUnity\n' > "$host_root/AIRoot/Modules/XUUnity/README.md"
}

assert_contains() {
  local path="$1"
  local pattern="$2"

  grep -q "$pattern" "$path" || fail "Expected '$pattern' in $path"
}

PYTHON_BIN="$(resolve_python_bin)"

log "Syntax"
bash -n "$AIRROOT_DIR/scripts/init_ai_topology.sh"
bash -n "$AIRROOT_DIR/scripts/init_ai_repo.sh"
bash -n "$AIRROOT_DIR/scripts/init_ai_project.sh"
bash -n "$AIRROOT_DIR/scripts/refresh_public_site.sh"
bash -n "$AIRROOT_DIR/scripts/testing/run_setup_smoke.sh"

if command -v git >/dev/null 2>&1; then
  log "Line endings"
  git -C "$AIRROOT_DIR" ls-files --eol 'scripts/*.sh' '.gitattributes'
fi

log "Fresh topology setup"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/fresh"
make_host_fixture "$host_root"
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --dry-run
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --check
  "$PYTHON_BIN" AIRoot/scripts/routing_audit.py --host-root "$host_root"
)

log "Unmanaged router preflight"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/unmanaged"
make_host_fixture "$host_root"
printf '# Existing Router\n' > "$host_root/Agents.md"
set +e
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --dry-run
) >"$tmp_root/unmanaged.out" 2>"$tmp_root/unmanaged.err"
rc="$?"
set -e
[ "$rc" -ne 0 ] || fail "Unmanaged router dry-run unexpectedly succeeded"
[ ! -e "$host_root/AIOutput" ] || fail "Unmanaged router preflight wrote AIOutput before failing"
assert_contains "$tmp_root/unmanaged.err" "Refusing topology setup before writing scaffold"

log "Preserve unmanaged router"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/preserve"
make_host_fixture "$host_root"
printf '# Existing Router\nkeep me\n' > "$host_root/Agents.md"
before_sum="$(shasum "$host_root/Agents.md" | awk '{print $1}')"
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --preserve-existing-router
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --preserve-existing-router --check
)
after_sum="$(shasum "$host_root/Agents.md" | awk '{print $1}')"
[ "$before_sum" = "$after_sum" ] || fail "Preserved unmanaged router changed"
assert_contains "$host_root/AIOutput/Registry/setup_status.yaml" "preserved_unmanaged_repo_router"
assert_contains "$host_root/AIOutput/Registry/host_topology.yaml" "preserved_unmanaged_repo_router"

log "Adopt unmanaged router"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/adopt"
make_host_fixture "$host_root"
printf '# Existing Router\nadopt me\n' > "$host_root/Agents.md"
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --adopt-existing-router
)
[ -f "$host_root/Agents.legacy.md" ] || fail "Adopt did not create Agents.legacy.md"
assert_contains "$host_root/Agents.legacy.md" "Existing Router"
assert_contains "$host_root/Agents.md" "Managed by AIRoot/scripts/init_ai_repo.sh"

log "Project alias fallback without symlink"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/project"
fakebin="$tmp_root/fakebin"
make_host_fixture "$host_root"
mkdir -p "$fakebin"
printf '# Root Router\n' > "$host_root/Agents.md"
cat > "$fakebin/ln" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$fakebin/ln"
(
  cd "$host_root"
  PATH="$fakebin:$PATH" AIRROOT_PYTHON="$PYTHON_BIN" bash AIRoot/scripts/init_ai_project.sh --project Game --repo-mode single-project
  PATH="$fakebin:$PATH" AIRROOT_PYTHON="$PYTHON_BIN" bash AIRoot/scripts/init_ai_project.sh --project Game --repo-mode single-project --check
)
[ -f "$host_root/Game/Agents.repo.md" ] || fail "Alias fallback file missing"
assert_contains "$host_root/Game/Agents.repo.md" "alias-fallback"
assert_contains "$host_root/Game/Agents.repo.md" "target: ../Agents.md"

log "Python fallback"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/python-fallback"
fakebin="$tmp_root/fakebin"
make_host_fixture "$host_root"
mkdir -p "$fakebin"
cat > "$fakebin/python3" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat > "$fakebin/python" <<'EOF'
#!/usr/bin/env bash
exec "$AIRROOT_REAL_PYTHON_FOR_TEST" "$@"
EOF
chmod +x "$fakebin/python3" "$fakebin/python"
(
  cd "$host_root"
  PATH="$fakebin:$PATH" AIRROOT_REAL_PYTHON_FOR_TEST="$PYTHON_BIN" bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --dry-run
)

log "AIRoot setup smoke passed"
