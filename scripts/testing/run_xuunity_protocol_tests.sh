#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
AIRROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd -P)"

resolve_python_bin() {
  local candidate

  for candidate in "${AIRROOT_PYTHON:-}" "${PYTHON:-}" python3 python; do
    [ -n "$candidate" ] || continue
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY' >/dev/null 2>&1; then
import sys
raise SystemExit(0 if sys.version_info[0] >= 3 else 1)
PY
      command -v "$candidate"
      return 0
    fi
  done

  printf '%s\n' "Python 3 was not found. Set AIRROOT_PYTHON or PYTHON." >&2
  return 1
}

PYTHON_BIN="$(resolve_python_bin)"
export PYTHONDONTWRITEBYTECODE=1

printf '\n== XUUnity public protocol tests ==\n'
"$PYTHON_BIN" -m unittest discover \
  -s "$AIRROOT_DIR/Modules/XUUnity/scripts/tests" \
  -p 'test_*.py'

printf '\n== XUUnity model-fitness tests ==\n'
"$PYTHON_BIN" -m unittest discover \
  -s "$AIRROOT_DIR/Operations/XUUnityModelFitness/tests" \
  -p 'test_*.py'

protocol_host="$(mktemp -d)"
trap 'rm -rf "$protocol_host"' EXIT
mkdir -p "$protocol_host/AIRoot/Modules"
cp -R "$AIRROOT_DIR/Modules/XUUnity" \
  "$protocol_host/AIRoot/Modules/XUUnity"
printf '# Synthetic host router for public protocol validation\n' \
  > "$protocol_host/AGENTS.md"

printf '\n== Reduced-stack rules and authored probes ==\n'
"$PYTHON_BIN" \
  "$AIRROOT_DIR/Modules/XUUnity/scripts/ruleset_check.py" \
  --repo-root "$protocol_host" \
  --ruleset "$protocol_host/AIRoot/Modules/XUUnity/knowledge/reduced_stack_rules.json" \
  --probes "$protocol_host/AIRoot/Modules/XUUnity/knowledge/reduced_stack_probes.json"

printf '\n== Entrypoint kernel invariant ==\n'
"$PYTHON_BIN" \
  "$AIRROOT_DIR/Modules/XUUnity/scripts/check_entrypoint_kernel.py" \
  "$AIRROOT_DIR/Modules/XUUnity/tasks/start_session.md"

printf '\nXUUnity protocol validation passed.\n'
