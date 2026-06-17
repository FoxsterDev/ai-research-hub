# XUUnity Knowledge: Execution Contract

Use this file when a task, review, or system utility must derive, surface, or update the compact execution contract for a session.

This file is the single owner of the execution-contract field set, the field meanings, and the contract rules. All task, review, and utility files should reference this owner instead of copying the full field list.

The validation cluster (`primary_validation_lane`, `secondary_validation_lane`, `lane_selection_reason`, `expected_evidence_class`, `validation_gaps`, and the umbrella `validation_contract`) is owned by `knowledge/validation_contract.md`; reference that owner rather than redefining lane semantics or allowed values here. Lane semantics live in `knowledge/validation_lanes.md`; evidence-strength and Unity-path boundaries live in `knowledge/unity_validation_boundaries.md`. The public-safe debug rendering of this contract is `utilities/routing_debug_template.md`.

## When To Derive
- Derive and surface a compact execution contract before implementation, large review output, or implementation planning is finalized, and before any patch.
- Initialize it in `tasks/start_session.md` during stack assembly, then carry and refine it through the selected task.

## Canonical Field Names
Keep the set complete and in this order. Use `none` explicitly when a field is intentionally empty instead of omitting it.

- `resolved_project`: the concrete target project, `multi-project`, or `unresolved`.
- `primary_task`: the selected task file or task family.
- `overlay_tasks`: additive task overlays such as `startup/config ownership`, `ui-heavy`, or `refactoring`.
- `matched_skills`: the skill files that materially affect routing, patch shape, or validation.
- `matched_policy_packs`: the matched `reviews/policy_packs/*` files.
- `matched_private_packs`: matched private pack ids and capability ids only — never private paths, manifests, or bodies.
- `private_pack_report_references`: public-safe report references returned by the registry tool.
- `trigger_reasons`: the concrete signals that drove task, risk, and overlay selection.
- `risk_class`: `low`, `moderate`, `high`, or `critical` from `knowledge/risk_classification.md`; otherwise `not-classified`.
- `root_cause_chain_checked`: the ownership layers inspected. For runtime-content warnings, prefer `symptom -> immediate caller -> service/wrapper -> initialization owner -> active config/profile -> content/manifest availability`.
- `patch_shape`: `local_fix`, `configuration_fix`, `sequencing_fix`, `ownership_fix`, `state_orchestration_fix`, or `cross_layer_fix`.
- `pre_patch_blockers`: unchecked ownership or validation conditions that block a source patch.
- `primary_validation_lane`: owned by `knowledge/validation_contract.md`.
- `secondary_validation_lane`: owned by `knowledge/validation_contract.md`.
- `lane_selection_reason`: owned by `knowledge/validation_contract.md`.
- `expected_evidence_class`: owned by `knowledge/validation_contract.md`.
- `validation_contract`: the active validation contract fields for the session, using the exact schema from `knowledge/validation_contract.md`.
- `why_not_local_fix`: why the fix may not stop at the log site, presenter, local service, or nearest stack frame.
- `validation_gaps`: owned by `knowledge/validation_contract.md` — missing proof, blocked tool path, weak evidence, or observability hole.
- `required_validation`: the narrowest representative proof currently required.
- `required_self_review`: what must still be re-checked before closure.

## Field Rules
- Keep the contract short and concrete. Use `none` explicitly instead of omitting any field.
- If investigation changes the inferred stack, risk class, validation obligations, routing, or patch shape, update the contract before proposing a patch, final recommendation, or closure.
- `required_validation` should name the narrowest representative proof currently required, such as affected assembly compile, representative build target, explicit runtime validation gap, or a review-only limitation.
- For `tasks/bug_fixing.md`, treat `required_validation` as provisional until patch-shape classification is known, then derive it from patch shape and bug family instead of leaving it at generic wording such as `validate fix`.
- When a supported Unity MCP path exists for the project, prefer `interactive_mcp` or MCP-backed `batch_compile` over non-MCP substitutes.
- The validation cluster must use the exact schema from `knowledge/validation_contract.md`; do not rename or redefine it here.
- `required_self_review` should say what must still be re-checked before closure, such as hidden behavior drift, queue cleanup, ownership fallout, or contract fallout from moved call paths.
- When queues, flags, wrappers, flush paths, delay gates, cache-backed fallbacks, or other orchestration ballast appear during investigation, add those signals to `trigger_reasons` and make `required_self_review` explicitly cover simplification and complexity-budget review before closure.
- If the user is likely to copy code, commands, config, prompts, or patch text from the answer, add a copy-safety check to `required_self_review` and plan the final answer around clean fenced blocks.
- If new tests are authored, extend `required_self_review` to include a quick test-quality pass against `skills/tests/testing_doctrine.md` and `reviews/test_quality_review.md`.

## Rendering
- In `tasks/start_session.md`, surface the derived contract under `Derived execution contract` using this field set.
- For routing/start-session debug, private-pack accounting, or root-cause-gated sessions, render the contract through `utilities/routing_debug_template.md` instead of re-listing the fields.

## Rule
This file is the single source of truth for the execution-contract field set and rules. Reference it; do not copy the field list into task, review, or utility files.
