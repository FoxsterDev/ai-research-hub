# XUUnity Knowledge: Routing Trigger Matrix

Use this file to route runtime-warning, exception, popup, remote-content, and startup/config-ownership families from a visible symptom to the required stack, owner chain, allowed patch shapes, validation lane, and private capability check — before proposing a source patch.

This matrix is the signal-to-routing owner for those families. The execution-contract field set and meanings are owned by `knowledge/execution_contract.md`; the validation cluster is owned by `knowledge/validation_contract.md`; the patch-shape taxonomy is owned by `tasks/bug_fixing.md`. Route a derived routing contract through the pre-patch gate checker `scripts/routing_gate_check.py` (fixtures in `scripts/tests/routing_fixtures/`) to block shallow classification.

## Public Trigger Matrix

| Signal | Required stack | Required chain | Allowed patch shapes | Validation lane | Private capability check |
| --- | --- | --- | --- | --- | --- |
| popup/runtime-content warning + remote content | `tasks/bug_fixing.md` + `startup/config ownership`; `reviews/policy_packs/ui_heavy_changes.md` secondary | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `configuration_fix`, `sequencing_fix`, `ownership_fix`; `local_fix` only after upstream ownership is disproven | `interactive_mcp` or `scenario` for full proof; `config_inspection` with explicit runtime gap for partial proof | runtime UI validation or playmode smoke planning when an optional private pack is available; otherwise an explicit validation gap |
| missing asset/design/config warning (no remote content) | `tasks/bug_fixing.md` + `startup/config ownership` | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `configuration_fix`, `sequencing_fix`; `local_fix` only after upstream ownership is disproven | `config_inspection` with explicit runtime gap; `interactive_mcp` when an editor path exists | none unless runtime UI validation is required |
| runtime exception crossing feature startup / flow / async service / SDK init | `tasks/bug_fixing.md` + `startup/config ownership`; matched SDK/startup policy pack | symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability | `sequencing_fix`, `ownership_fix`, `configuration_fix`; `local_fix` only after the init/owner path is disproven | `interactive_mcp` or `scenario`; `batch_compile` when signatures/owners moved | runtime validation gap recorded if no representative run happened |
| SDK init / consent / attribution / ad-revenue / reward warning | `tasks/bug_fixing.md` + `reviews/policy_packs/sdk_changes.md` (+ `startup_changes.md` / `monetization_changes.md` as matched); `skills/sdk/` | symptom -> wrapper/adapter -> startup/consent owner -> identity owner -> reward/entitlement/revenue owner -> queue/delay/retry path | `sequencing_fix`, `ownership_fix`; `local_fix` only after readiness/identity/consent ownership is disproven | `interactive_mcp` or `scenario`; `batch_compile` for wrapper compile fallout | none in public core; record runtime markers expected at runtime |

`local_fix` is never the default for these families. It is allowed only after the upstream owner chain has been inspected and disproven, and `why_not_local_fix` must record that disposition.

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
