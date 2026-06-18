# XUUnity Knowledge: Routing Trigger Matrix

Use this file to route runtime-warning, exception, popup, remote-content, and startup/config-ownership families from a visible symptom to the required stack, owner chain, allowed patch shapes, validation lane, and private capability check — before proposing a source patch. It also routes the tooling / install / cross-platform / remote-only family (see the dedicated section below), which uses a process/argv/shell/host owner chain rather than a feature/config one.

This matrix is the signal-to-routing owner for those families. The execution-contract field set and meanings are owned by `knowledge/execution_contract.md`; the validation cluster is owned by `knowledge/validation_contract.md`; the patch-shape taxonomy is owned by `tasks/bug_fixing.md`. Route a derived routing contract through the pre-patch gate checker `scripts/routing_gate_check.py` (fixtures in `scripts/tests/routing_fixtures/`) to block shallow classification.

## Public Trigger Matrix

| Signal | Required stack | Required chain | Allowed patch shapes | Validation lane | Private capability check |
| --- | --- | --- | --- | --- | --- |
| popup/runtime-content warning + remote content | `tasks/bug_fixing.md` + `startup/config ownership`; `reviews/policy_packs/ui_heavy_changes.md` secondary | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `configuration_fix`, `sequencing_fix`, `ownership_fix`; `local_fix` only after upstream ownership is disproven | `interactive_mcp` or `scenario` for full proof; `config_inspection` with explicit runtime gap for partial proof | runtime UI validation or playmode smoke planning when an optional private pack is available; otherwise an explicit validation gap |
| missing asset/design/config warning (no remote content) | `tasks/bug_fixing.md` + `startup/config ownership` | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `configuration_fix`, `sequencing_fix`; `local_fix` only after upstream ownership is disproven | `config_inspection` with explicit runtime gap; `interactive_mcp` when an editor path exists | none unless runtime UI validation is required |
| runtime exception crossing feature startup / flow / async service / SDK init | `tasks/bug_fixing.md` + `startup/config ownership`; matched SDK/startup policy pack | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `sequencing_fix`, `ownership_fix`, `configuration_fix`; `local_fix` only after the init/owner path is disproven | `interactive_mcp` or `scenario`; `batch_compile` when signatures/owners moved | runtime validation gap recorded if no representative run happened |
| SDK init / consent / attribution / ad-revenue / reward warning | `tasks/bug_fixing.md` + `reviews/policy_packs/sdk_changes.md` (+ `startup_changes.md` / `monetization_changes.md` as matched); `skills/sdk/` | symptom -> wrapper/adapter -> startup/consent owner -> identity owner -> reward/entitlement/revenue owner -> queue/delay/retry path | `sequencing_fix`, `ownership_fix`; `local_fix` only after readiness/identity/consent ownership is disproven | `interactive_mcp` or `scenario`; `batch_compile` for wrapper compile fallout | none in public core; record runtime markers expected at runtime |

`local_fix` is never the default for these families. It is allowed only after the upstream owner chain has been inspected and disproven, and `why_not_local_fix` must record that disposition.

## Tooling / Install / Cross-Platform / Remote-Only Family

This family covers failures in the MCP tooling itself — install/setup wizard, CLI wrappers (`.sh` / `.cmd` / `.ps1`), argument and path handling, host/editor lifecycle and bridge readiness — and any failure that reproduces only on another platform or in CI/remote with no interactive access. These are not Unity-runtime-content bugs, so the owner chain is process/argv/shell/host, not feature/config ownership.

| Signal | Required knowledge to load first | Owner chain | Approach |
| --- | --- | --- | --- |
| Setup/CLI/wrapper failure on Windows; path or argument handling; `.sh` vs `.cmd` vs `.ps1` divergence; spaces in paths; MSYS / Git-Bash / `os.name` behavior | `knowledge/cross_platform_shell_portability.md` | symptom -> launcher flavor -> argv/env delivery -> interpreter resolution -> host path/shell layer | Trace argv/env delivery across all three launcher flavors before patching; prefer shrinking the shell entrypoint to "find Python + exec" and moving logic into Python over adding guards; validate with a golden dual-run (`tests/test_launcher_flavor_parity.py`) and add a fixture for the failing case (e.g. a project path containing a space). |
| Failure reproduces only in CI / another environment / remote with no interactive access; hang with no output; cancelled before diagnostics print | `knowledge/remote_only_failure_bisection.md` | symptom -> spawn/interpreter layer -> failing line (located by bisection) | Spend the first round-trip on bisection instrumentation (layer canaries, prefix ladder, kill-time diagnostics, first-failure skip), not serial plausible fixes. |
| Both at once (e.g. a Windows-only install hang investigated from a non-Windows host or CI) | both of the above | combine both chains | Bisection instrumentation to locate the failing layer + shell-portability owner chain to fix it. |

These two knowledge files carry their own `## When To Load` headers but are otherwise orphaned — no runtime-warning row above routes to them. This section is their explicit trigger; `tasks/bug_fixing.md` cross-links here for tooling/install/CLI/cross-platform/remote-only symptoms.

## Runtime Proof Classes
Classify the evidence the closeout actually has:
- `static_route_only`
- `source_inspection`
- `config_inspection`
- `compile`
- `interactive_runtime`
- `scenario_runtime`

For popup/runtime UI warnings:
- partial closeout may use `config_inspection` only with an explicit runtime validation gap
- full closeout requires `interactive_runtime` or `scenario_runtime`

## Pre-Patch Gate
Before a source patch on these families, derive a routing contract using the execution-contract field set and run it through the gate checker:

```bash
python3 scripts/routing_gate_check.py --contract <routing_contract.json>
```

The gate fails (non-zero exit) when:
- a runtime warning is classified `local_fix` without active config/profile inspection
- a popup/runtime-content warning with remote content did not load `startup/config ownership` overlay routing
- runtime UI validation is required but neither a private capability check nor an explicit validation gap is recorded
- `why_not_local_fix` is empty while upstream ownership is involved
- `root_cause_chain_checked` is missing the minimum owner chain for the bug family

See `scripts/tests/routing_fixtures/` for worked examples of both a deep (passing) and a shallow (failing) classification.

## Host-Local Extension
Host-local overlays extend this public matrix with project or organization symbols. The public core names the extension mechanism, not private symbols. A host-local matrix row should map:
- local signal names
- local service names
- local bootstrap/config owners
- expected owner chain
- required policy-pack additions
- required private capability checks

Keep host-local signal names, private service names, and private bootstrap owners in the host overlay, not in this public file.
