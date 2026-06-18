# XUUnity Task: Incident Response

## Goal
Triage production-impacting failures quickly and safely.

## Focus
- Reproduction path
- Blast radius
- rollback or mitigation path
- logging and observability gaps

## Output
- Incident summary
- Suspected cause
- Immediate mitigation
- Follow-up hardening actions

## Load When Relevant
- For a failure that reproduces only in CI or another environment with no interactive access (a hang with no output, or a run cancelled before diagnostics print), load `knowledge/remote_only_failure_bisection.md` and spend the first round-trip on bisection instrumentation, not serial plausible fixes.
- For install / setup-wizard / CLI-wrapper incidents, `.sh`/`.cmd`/`.ps1` flavor divergence, spaces-in-paths, or MSYS/Git-Bash/`os.name` behavior, load `knowledge/cross_platform_shell_portability.md`.
- Route both through the Tooling / Install / Cross-Platform / Remote-Only family in `knowledge/routing_trigger_matrix.md`.
