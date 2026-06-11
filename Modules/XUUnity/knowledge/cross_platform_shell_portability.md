# Knowledge: Cross-Platform Shell Portability (macOS / Linux / Windows Git Bash)

## When To Load
- a bash script, wrapper, or CI step must also run on Windows (Git Bash / MSYS)
- a Windows CI job hangs with zero output while macOS/Linux legs pass
- tests spawn bash or shell scripts via `subprocess` from Python or another native host

## Rules
- Path-upward walks via `dirname` must terminate on a fixed point (`candidate == previous`), never on `== "/"`. Windows path forms walk `D:/a → D: → . → .` and never reach `/`; inside `$(...)` this hangs with zero output.
- From a native (non-MSYS) parent on Windows, spawning `"bash"` resolves through CreateProcess search order to the System32 WSL stub. Resolve Git Bash explicitly; prefer `Git/usr/bin/bash.exe` over the `Git/bin` shim (one less process layer, reliable tree-kill).
- `xargs -P` is unreliable under MSYS fork emulation. Tactical guard: branch to a sequential in-process loop when `OSTYPE` is `msys`/`cygwin` or parallelism ≤ 1. Durable fix: move the orchestration into Python — `ThreadPoolExecutor` over subprocess waits is I/O-bound, needs no fork, and parallelizes identically on all three OSes.
- Any repo with `.sh` files needs `.gitattributes` with `*.sh text eol=lf` (`*.cmd`/`*.ps1` → `crlf`). Windows CI runners check out with `autocrlf=true` by default.
- Env vars carrying interpreter paths may arrive in backslash form (`C:\...\python.exe`); normalize `\` → `/` before `command -v` checks or exec inside bash.
- Env-value conversion is asymmetric per launcher flavor: Git Bash rewrites POSIX-looking env *values* (e.g. `/tmp/x`) into Windows paths when exec'ing native executables; cmd/PowerShell pass them verbatim. Fixtures or config shared across `.sh`/`.cmd`/`.ps1` flavors must use native paths (`tempfile.gettempdir()`), or the flavors diverge for fixture reasons only.
- Porting bash `cd ... && pwd` to Python: use `os.path.abspath` (logical, keeps `/tmp` on macOS), not `Path.resolve()`; keep `realpath` only where the original explicitly used it. Otherwise symlinked temp dirs (`/var` vs `/private/var`) create false output diffs.
- A platform-support claim requires a CI leg per claimed platform. Assumptions accumulate invisibly on platforms CI never executes.

## Thin Launcher End-State
- The durable fix for fragile operator bash is not more guards — guards cover known traps, MSYS emulation is a permanent risk *class*. Shrink every shell entrypoint to "find a Python ≥ N interpreter + exec" (≤ ~30 lines) and move the body into Python.
- Behavior-preserving port discipline: keep the legacy implementation callable behind an env flag through the same entrypoint; prove parity with golden tests that run both implementations in isolated sandboxes comparing stdout, stderr, exit codes, and filesystem effects; delete legacy only after a green CI leg per claimed platform.
- Replicate latent bugs discovered during the port and file them as follow-ups; fixing them mid-port invalidates the golden baseline.
- Reference implementation: `xuunity-mcp` repo — `templates/server_launcher.py` (core), `xuunity_light_unity_mcp.sh/.cmd/.ps1` (launchers), `tests/test_launcher_parity.py` (golden dual-run harness).

## Anti-Patterns
- Comparing full path strings in cross-platform tests: MSYS `/tmp/...`, `C:\Users\RUNNER~1\...` (8.3 short name via `TMP`), `C:/Users/runneradmin/...`, and JSON-escaped `C:\\Users\\...` are the same directory. For sandboxed A/B output comparison, key normalization on the unique sandbox basename (no separators — immune to all four forms), then collapse separators and host temp prefixes (`tempfile.gettempdir()`, `TMP`/`TEMP`, and their `realpath` variants).
- Spawning subprocesses in tests without a timeout plus process-tree kill (`taskkill /T /F` on Windows, `killpg` on POSIX). A child that never exits otherwise eats the whole CI job time limit.
- Burying failure diagnostics at suite end. Dump captured partial stdout/stderr at the moment the timeout fires; canceled runs lose everything printed later.

## Cross-Links
- `knowledge/remote_only_failure_bisection.md` for diagnosing where such a script hangs when it only fails remotely.
