# XUUnity Utility: Routing Debug Template

## Goal
Provide a compact, public-safe routing and validation debug output for sessions where prompt-stack selection, root-cause gating, private-pack availability, or validation obligations must be explicit.

Use this utility when:
- the user asks for routing debug, start-session debug, loaded module accounting, or private-pack capability accounting
- a bug is blocked by root-cause gating before a local patch can be proposed
- a runtime warning or exception crosses startup/config ownership, async services, remote content, UI flow routing, SDK/service initialization, or validation-pack routing

## Output Shape
Use `none` explicitly when a field is intentionally empty.

```text
routing_debug:
  resolved_project:
  primary_task:
  overlay_tasks:
  loaded_public_files:
  loaded_internal_files:
  matched_skills:
  matched_private_packs:
  private_pack_report_references:
  matched_policy_packs:
  risk_class:
  root_cause_chain_checked:
  patch_shape:
  pre_patch_blockers:
  validation_contract:
    primary_validation_lane:
    secondary_validation_lane:
    lane_selection_reason:
    expected_evidence_class:
    required_validation:
    validation_gaps:
  why_not_local_fix:
```

## Field Guidance
- `resolved_project`: name the concrete project, `multi-project`, or `unresolved`.
- `primary_task`: name the selected task file or task family.
- `overlay_tasks`: list additive task overlays such as `startup/config ownership`, `ui-heavy`, or `refactoring`.
- `loaded_public_files`: list the public `XUUnity` files actually used.
- `loaded_internal_files`: list host-local overlay files actually used; use repo-relative paths only when safe for the host repo.
- `matched_skills`: list only the skills that materially affected routing, patch shape, or validation.
- `matched_private_packs`: list private pack ids and capability ids only. Do not include private filesystem paths, private manifests, or private file bodies.
- `private_pack_report_references`: list public-safe report references returned by the registry tool.
- `matched_policy_packs`: list the selected policy pack names and the trigger reason for each.
- `risk_class`: use the active risk classification from `knowledge/risk_classification.md` when loaded; otherwise state `not-classified`.
- `root_cause_chain_checked`: list the inspected ownership layers. For runtime-content warnings, prefer `symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability`.
- `patch_shape`: name the selected patch shape, such as `local_fix`, `configuration_fix`, `sequencing_fix`, `ownership_fix`, `state_orchestration_fix`, or `cross_layer_fix`.
- `pre_patch_blockers`: list unchecked ownership or validation conditions that block a source patch.
- `validation_contract`: use the active validation contract fields selected for this session. Keep it compact and representative.
- `why_not_local_fix`: explain why the fix is not allowed to stop at the log site, presenter, local service, or nearest stack frame.

## Private Content Rule
When private modules are involved, this template may report:
- pack id
- capability id
- loaded, locked, invalid, or unavailable state
- public-safe session contract fields returned by the registry tool

This template must not report:
- private pack entrypoint paths
- private prompt bodies
- private manifests
- local-only secrets or credential-bearing config values

## Rule
This utility is a debug and accountability surface. It should make routing decisions observable without expanding the task stack by itself.
