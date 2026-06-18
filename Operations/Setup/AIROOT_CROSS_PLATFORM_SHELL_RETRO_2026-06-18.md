# AIRoot Cross-Platform Shell Retro

Date: `2026-06-18`
Status: `implemented with local fixture validation`

## Executive Verdict
AIRoot setup scripts had the same risk class that previously hurt XUUnity MCP:
shell entrypoints were nominally simple, but key assumptions were Unix-biased.
The highest-risk issues were hardcoded `python3` and mandatory symlink creation
for project aliases. Both are now guarded with cross-platform fallbacks.

## What Was Reviewed
- `scripts/init_ai_topology.sh`
- `scripts/init_ai_repo.sh`
- `scripts/init_ai_project.sh`
- `scripts/refresh_public_site.sh`
- XUUnity MCP cross-platform shell skill and public portability knowledge

## Findings And Fixes
- **Python launcher portability:** setup scripts called `python3` directly.
  Windows Git Bash and some fresh hosts expose Python as `python` instead.
  Fixed by resolving Python once from `AIRROOT_PYTHON`, `PYTHON`, `python3`,
  then `python`, with backslash-to-slash normalization for Git Bash.
- **Project alias symlink portability:** `init_ai_project.sh` required `ln -s`
  and `readlink` for `Agents.repo.md` and `AIModules`. Windows hosts may lack
  symlink privilege. Fixed by keeping symlinks as the preferred path and writing
  managed alias fallback files/directories when symlink creation fails.
- **Line endings:** AIRoot now has `.gitattributes` pinning `.sh` files to LF
  and Windows launcher files to CRLF.
- **Router preserve mode:** unmanaged routers can now be intentionally preserved
  while setup/check still validates scaffold and registry state.
- **YAML timestamp parse:** `setup_status.yaml` now quotes
  `last_provisioned_at` so strict safe YAML loaders do not reject it as a native
  timestamp object.

## Validation Run
- `bash -n` passed for all AIRoot shell scripts.
- `git ls-files --eol` shows `scripts/*.sh` using `attr/text eol=lf`.
- Fresh temp host topology setup passed dry-run, apply, and check.
- Unmanaged router without preserve/adopt fails before writing scaffold.
- Preserve mode keeps unmanaged router content unchanged.
- Adopt mode still writes `Agents.legacy.md` and a managed router.
- Project alias fallback passed with `ln` intentionally forced to fail.
- Python fallback passed with `python3` intentionally forced to fail and
  `python` delegated to Python 3.
- Fresh generated temp host passed `scripts/routing_audit.py --host-root`.

## Residual Risk
- Native Windows Git Bash was not executed in this local pass. The fixes target
  known XUUnity MCP failure classes, but a real Windows CI/job leg is still
  required before claiming full Windows proof.
- AIRoot setup still contains substantive logic in Bash. The XUUnity MCP
  long-term lesson remains valid: if setup grows more complex, move orchestration
  into Python and keep `.sh` files as thin launchers.

## Recommended Next Step
Add a small CI matrix for AIRoot setup smoke tests on macOS, Linux, and Windows
Git Bash. The first Windows test should exercise `init_ai_project.sh` with
symlink creation unavailable or mocked so the alias fallback remains covered.
