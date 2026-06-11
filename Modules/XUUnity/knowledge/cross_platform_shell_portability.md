# Knowledge: Cross-Platform Shell Portability (macOS / Linux / Windows Git Bash)

## When To Load
- a bash script, wrapper, or CI step must also run on Windows (Git Bash / MSYS)
- a Windows CI job hangs with zero output while macOS/Linux legs pass
- tests spawn bash or shell scripts via `subprocess` from Python or another native host

## Rules
- Path-upward walks via `dirname` must terminate on a fixed point (`candidate == previous`), never on `== "/"`. Windows path forms walk `D:/a → D: → . → .` and never reach `/`; inside `$(...)` this hangs with zero output.
- From a native (non-MSYS) parent on Windows, spawning `"bash"` resolves through CreateProcess search order to the System32 WSL stub. Resolve Git Bash explicitly; prefer `Git/usr/bin/bash.exe` over the `Git/bin` shim (one less process layer, reliable tree-kill).
- `xargs -P` is unreliable under MSYS fork emulation. Branch to a sequential in-process loop when `OSTYPE` is `msys`/`cygwin` or parallelism ≤ 1.
- Any repo with `.sh` files needs `.gitattributes` with `*.sh text eol=lf` (`*.cmd`/`*.ps1` → `crlf`). Windows CI runners check out with `autocrlf=true` by default.
- Env vars carrying interpreter paths may arrive in backslash form (`C:\...\python.exe`); normalize `\` → `/` before `command -v` checks or exec inside bash.
- A platform-support claim requires a CI leg per claimed platform. Assumptions accumulate invisibly on platforms CI never executes.

## Anti-Patterns
- Comparing full path strings in cross-platform tests: MSYS `/tmp/...`, `C:\Users\RUNNER~1\...` (8.3 short name), and `C:/Users/runneradmin/...` are the same directory. Compare separator-normalized suffixes or resolved `Path` equality.
- Spawning subprocesses in tests without a timeout plus process-tree kill (`taskkill /T /F` on Windows, `killpg` on POSIX). A child that never exits otherwise eats the whole CI job time limit.
- Burying failure diagnostics at suite end. Dump captured partial stdout/stderr at the moment the timeout fires; canceled runs lose everything printed later.

## Cross-Links
- `knowledge/remote_only_failure_bisection.md` for diagnosing where such a script hangs when it only fails remotely.
