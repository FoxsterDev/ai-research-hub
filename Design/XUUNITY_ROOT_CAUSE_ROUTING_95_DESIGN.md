# XUUnity Root-Cause Routing 95+ Design

## Goal
Raise runtime-warning, exception, popup, remote-content, and startup/config routing from prompt-guided discipline to an enforceable, testable contract.

The target is 95+ routing quality for cases where the nearest stack frame is not the owner of the root cause.

## First Principles
1. An agent fails where a rule is not converted into a required gate.
2. Prompt text is weaker than an executable routing smoke test.
3. One canonical execution contract is stronger than several copied field lists.
4. Root cause cannot be proven from the nearest stack frame alone.
5. Runtime UI correctness cannot be proven by static grep or source inspection.
6. A private pack is loaded only through the registry/session contract, not through agent confidence.

## Design

### 1. Canonical Execution Contract
The canonical owner exists at:

`AIRoot/Modules/XUUnity/knowledge/execution_contract.md`

It owns the field set, field meanings, and contract rules. The live field set is, in order:
- `resolved_project`
- `primary_task`
- `overlay_tasks`
- `matched_skills`
- `matched_policy_packs`
- `matched_private_packs`
- `private_pack_report_references`
- `trigger_reasons`
- `risk_class`
- `root_cause_chain_checked`
- `patch_shape`
- `pre_patch_blockers`
- `primary_validation_lane`
- `secondary_validation_lane`
- `lane_selection_reason`
- `expected_evidence_class`
- `validation_contract`
- `why_not_local_fix`
- `validation_gaps`
- `required_validation`
- `required_self_review`

The validation cluster (`primary_validation_lane`, `secondary_validation_lane`, `lane_selection_reason`, `expected_evidence_class`, `validation_gaps`, and the umbrella `validation_contract`) is owned by `knowledge/validation_contract.md`; the execution-contract owner references it rather than redefining it.

All task, review, and utility files should reference this owner instead of copying the full schema.

### 2. Routing Smoke Test Harness
Add routing fixtures under:

`AIRoot/Modules/XUUnity/scripts/tests/routing_fixtures/`

Each fixture should contain:
- task text
- referenced paths
- expected resolved project
- expected primary task
- expected overlays
- expected policy packs
- required root-cause chain
- allowed patch shapes
- required private capability checks
- expected validation lane or explicit validation gap

The first fixture should represent a popup/runtime-content warning where the visible symptom is emitted by UI code but the likely owner is startup/config/content availability.

### 3. Pre-Patch Gate Checker
Add a small checker, either as a new script or as an extension to the module registry tooling.

Input: routing contract JSON.

Fail when:
- a runtime warning has `patch_shape: local_fix` without active config/profile inspection
- popup or runtime-content warning with remote content does not load startup/config ownership routing
- runtime UI validation is required but neither a private capability check nor an explicit validation gap is recorded
- `why_not_local_fix` is empty when upstream ownership is involved
- `root_cause_chain_checked` does not include the minimum required owner chain for the bug family

### 4. Trigger Matrix
Create:

`AIRoot/Modules/XUUnity/knowledge/routing_trigger_matrix.md`

Use a table shape:
- signal
- required stack
- required chain
- allowed patch shapes
- validation lane
- private capability check

Example row:

```text
signal: popup/runtime-content warning + remote content
required_stack: bug_fixing + startup/config ownership, ui-heavy secondary
required_chain: symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability
allowed_patch_shapes: configuration_fix, sequencing_fix, ownership_fix, local_fix only after upstream ownership is disproven
validation_lane: interactive_mcp or scenario for full proof; config_inspection with explicit runtime gap for partial proof
private_capability_check: runtime UI validation or playmode smoke planning when optional private-pack routing is available
```

### 5. Host-Local Extension Matrix
Host-local overlays should extend the public trigger matrix with project or organization symbols.

The public core should name the extension mechanism, not private symbols.

Host-local matrix rows should map:
- local signal names
- local service names
- local bootstrap/config owners
- expected owner chain
- required policy-pack additions
- required private capability checks

### 6. Mandatory Routing Debug On Recovery
When a user reports that the agent solved shallowly, misclassified a task, or skipped private-pack/session routing, `utilities/routing_debug_template.md` becomes mandatory.

The debug output must include:
- loaded public files
- loaded internal files
- matched private packs by id and capability only
- matched policy packs
- root-cause chain checked
- patch shape
- pre-patch blockers
- validation contract
- validation gaps
- why the nearest stack frame was not enough

### 7. Runtime Proof Classes
Define proof classes:
- `static_route_only`
- `source_inspection`
- `config_inspection`
- `compile`
- `interactive_runtime`
- `scenario_runtime`

For popup/runtime UI warnings:
- partial closeout may use `config_inspection` only with an explicit runtime validation gap
- full closeout requires `interactive_runtime` or `scenario_runtime`

## Acceptance Plan

1. Add canonical execution contract owner.
2. Replace duplicated execution-contract field lists with references to the owner.
3. Add trigger matrix and route runtime warning families through it.
4. Add routing smoke fixtures for known shallow-classification failures.
5. Add pre-patch gate checker.
6. Wire private capability requirements through session-plan output only.
7. Require routing debug output for recovery/postmortem sessions.

## Score Projection
- Current state after prompt fixes: about `82/100`.
- Canonical execution contract: about `87/100`.
- Trigger matrix: about `90/100`.
- Routing smoke fixtures: about `94/100`.
- Pre-patch gate checker with pass/fail behavior: about `96/100`.

## Highest-Leverage Move
Build the first executable routing acceptance test before adding more prose.

The test should fail if a popup/runtime-content warning is classified as a local UI fix before startup/config ownership, active config/profile, content availability, and runtime UI validation obligations are accounted for.

## Implementation Status (2026-06-16)
The executable layer is built:
- Step 1 — canonical owner `knowledge/execution_contract.md` (done).
- Step 2 — the three copied field lists in `tasks/start_session.md` replaced with references to the owner (done).
- Step 3 — `knowledge/routing_trigger_matrix.md` added; runtime-warning families routed through it from `tasks/start_session.md` and `tasks/bug_fixing.md` (done).
- Step 4 — routing smoke fixtures in `scripts/tests/routing_fixtures/` — 2 fixtures: a popup/runtime-content case (deep-pass + shallow-fail contracts) and a legitimate-`local_fix` case (done).
- Step 5 — pre-patch gate checker `scripts/routing_gate_check.py` enforcing the five section-3 rules, covered by `scripts/tests/test_routing_gate.py` (done).
- Step 6 — private capability requirements already route through `scripts/module_registry_tool.py session-plan --require-capability` (pre-existing).
- Step 7 — routing debug on recovery already mandated via `utilities/routing_debug_template.md` (pre-existing).

Remaining:
- host-local trigger-matrix rows (section 5) in the host overlay.
- broader fixture and bug-family owner-chain coverage (the public matrix currently details the runtime-content family).
- optional wiring of the gate checker into a pre-commit or CI step.
