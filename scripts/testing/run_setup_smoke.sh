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

assert_contains_either() {
  local path="$1"
  local pattern_a="$2"
  local pattern_b="$3"

  if grep -q "$pattern_a" "$path" || grep -q "$pattern_b" "$path"; then
    return 0
  fi

  fail "Expected '$pattern_a' or '$pattern_b' in $path"
}

file_sha256() {
  local path="$1"

  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
    return 0
  fi

  "$PYTHON_BIN" - "$path" <<'PY'
import hashlib
import sys

with open(sys.argv[1], "rb") as f:
    print(hashlib.sha256(f.read()).hexdigest())
PY
}

assert_exact_entry() {
  local path="$1"

  "$PYTHON_BIN" - "$path" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.parent.is_dir() or not any(entry.name == path.name for entry in path.parent.iterdir()):
    raise SystemExit(f"Missing exact directory entry: {path}")
PY
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
assert_exact_entry "$host_root/AGENTS.md"
assert_contains "$host_root/AIOutput/Registry/host_topology.yaml" "active_repo_router: AGENTS.md"
assert_contains "$host_root/AIOutput/Registry/setup_status.yaml" "host_root: ."
assert_contains "$host_root/AIOutput/Registry/setup_status.yaml" 'last_provisioned_at: "'

"$PYTHON_BIN" - "$host_root/AIOutput/Registry/setup_status.yaml" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace('last_provisioned_at: "', "last_provisioned_at: ").replace('Z"\n', "Z\n")
path.write_text(text, encoding="utf-8")
PY
"$PYTHON_BIN" "$host_root/AIRoot/scripts/routing_audit.py" --host-root "$host_root"

log "Unmanaged router preflight"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/unmanaged"
make_host_fixture "$host_root"
printf '# Existing Router\n' > "$host_root/AGENTS.md"
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
printf '# Existing Router\nkeep me\n' > "$host_root/AGENTS.md"
before_sum="$(file_sha256 "$host_root/AGENTS.md")"
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --preserve-existing-router
  bash AIRoot/scripts/init_ai_topology.sh --profile single_project_default --preserve-existing-router --check
)
after_sum="$(file_sha256 "$host_root/AGENTS.md")"
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
[ -f "$host_root/AGENTS.legacy.md" ] || fail "Adopt did not create AGENTS.legacy.md"
assert_contains "$host_root/AGENTS.legacy.md" "Existing Router"
assert_exact_entry "$host_root/AGENTS.md"
assert_contains "$host_root/AGENTS.md" "Managed by AIRoot/scripts/init_ai_repo.sh"

log "Managed mixed-case router migration"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/managed-migration"
make_host_fixture "$host_root"
printf '<!-- Managed by AIRoot/scripts/init_ai_repo.sh -->\n# Legacy Managed Router\n' > "$host_root/Agents.md"
(
  cd "$host_root"
  bash AIRoot/scripts/init_ai_repo.sh --repo-mode single-project --refresh-managed-router
)
assert_exact_entry "$host_root/AGENTS.md"
assert_contains "$host_root/AGENTS.md" "Managed by AIRoot/scripts/init_ai_repo.sh"

log "Project alias fallback without symlink"
tmp_root="$(mktemp -d)"
host_root="$tmp_root/project"
fakebin="$tmp_root/fakebin"
make_host_fixture "$host_root"
mkdir -p "$fakebin"
printf '# Root Router\n' > "$host_root/AGENTS.md"
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
[ -f "$host_root/Game/AGENTS.repo.md" ] || fail "Alias fallback file missing"
assert_contains "$host_root/Game/AGENTS.repo.md" "alias-fallback"
assert_contains_either "$host_root/Game/AGENTS.repo.md" "target: ../AGENTS.md" "target: ..\\\\AGENTS.md"
assert_exact_entry "$host_root/Game/AGENTS.md"

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
