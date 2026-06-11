# Knowledge: Remote-Only Failure Bisection

## When To Load
- a failure (hang, crash, flake) reproduces only in CI or another environment with no interactive access
- each verification attempt costs a full push-and-wait round-trip
- a job hangs with no output and gets canceled before diagnostics appear

## Rule
Spend the first round-trip on bisection instrumentation, not on plausible fixes. Serial theory-driven fixes cost one round-trip per theory; instrumentation locates the failing line in one.

The instrumentation kit, in order of leverage:
- **Layer canaries**: one minimal test per spawn/interpreter layer (plain spawn → script file → script with args → script with the suspect env → real artifact), short timeouts, run first in the suite. The first failing canary names the broken layer.
- **Prefix ladder**: run growing prefixes of the suspect script (cut at top-level boundaries) each with a short timeout; report a map like `153=ok 181=TIMEOUT`. The first timing-out prefix brackets the failing line.
- **Kill-time diagnostics**: on timeout, kill the process tree and immediately write the command plus captured partial stdout/stderr to the live log. Diagnostics deferred to suite end are destroyed when the operator cancels a stuck run.
- **First-failure skip**: after one timeout, skip remaining same-class heavy tests with an explanatory message. Worst-case run stays in minutes; the operator stops canceling before the evidence prints.

## Anti-Patterns
- Fixing the most plausible cause and re-running to see. Each "obvious" cause that pattern-matches the symptom (wrong interpreter, parallelism bug, line endings) can be real-but-secondary; only bisection proves which defect is the blocker.
- Timeouts longer than the operator's patience. A 300s timeout no one waits out is equivalent to no timeout.
- Treating zero output as "it never started". A subshell `$(...)` spinning in an infinite loop produces exactly the same silence as a process that failed to launch; only layer canaries distinguish them.

## Proportionality
This is incident tooling, not standing process: build it when a remote-only failure appears, delete the bisection scaffolding once the root cause lands, keep one end-to-end canary as the regression guard.

## Cross-Links
- `knowledge/cross_platform_shell_portability.md` for the Windows/MSYS failure modes that most often cause silent remote hangs.
