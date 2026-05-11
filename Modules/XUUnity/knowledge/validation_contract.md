# XUUnity Knowledge: Validation Contract

Use this file when a task, review, or system utility needs a stable validation schema across session routing, design, planning, implementation, and closeout.

Lane semantics live in `knowledge/validation_lanes.md`.
Evidence-strength and Unity-path boundaries live in `knowledge/unity_validation_boundaries.md`.
This file owns the contract shape and field meanings.

## Canonical Field Names
- `primary_validation_lane`
- `secondary_validation_lane`
- `lane_selection_reason`
- `expected_evidence_class`
- `validation_gaps`

## Allowed Values

### `primary_validation_lane`
Use exactly one of:
- `interactive_mcp`
- `batch_compile`
- `scenario`
- `none`

### `secondary_validation_lane`
Use exactly one of:
- `interactive_mcp`
- `batch_compile`
- `scenario`
- `none`

Use `none` when no justified secondary lane exists.

### `lane_selection_reason`
State why the primary lane is the narrowest representative proof for the current claim.

Keep it short and concrete, for example:
- `live editor state and console inspection are the real proof surface`
- `artifact correctness depends on generated build outputs, not source-only inspection`
- `ordered runtime transitions must be observed across more than one step`

Use `none` only when the stage cannot yet justify a lane choice and `primary_validation_lane` is also `none`.

### `expected_evidence_class`
Name the evidence expected from the chosen lane.

Keep it short and concrete, for example:
- `interactive scene snapshot`
- `console inspection after play mode entry`
- `compile matrix across build-config profiles`
- `artifact build exit + artifact presence`
- `generated manifest inspection`
- `generated plist inspection`

Use `none` only when the stage cannot yet justify a concrete proof target.

### `validation_gaps`
State any missing proof, blocked tool path, weak evidence, or observability hole that still prevents a stronger claim.

Examples:
- `none`
- `interactive lane unavailable in current session`
- `artifact build not run; source-only inspection is weaker evidence`
- `full Android and iOS profile matrix not executed`
- `lane can start tests but cannot provide trustworthy final totals`

## Rules
- Use the exact field names from this file. Do not rename the contract to `validation posture`, `proof surface`, `evidence target`, or similar variants.
- Keep all five fields present in validation-aware outputs. Use `none` explicitly instead of omitting a field.
- Keep lane choice and evidence class aligned. Do not name `interactive scene snapshot` as the evidence class for `batch_compile`.
- When the real claim is build-sensitive, prefer generated outputs over source-only reasoning in `expected_evidence_class`.
- If the chosen lane cannot provide trustworthy final accounting for the claim, record that in `validation_gaps` instead of silently weakening the claim.
- Task files may add stage-specific output obligations, but they should not redefine this schema.

## Stage Responsibilities
- `tasks/start_session.md`: initialize the validation contract inside the execution contract for the current session.
- `tasks/feature_design_brief.md`: set the earliest justified contract and use `none` explicitly for unresolved fields.
- `tasks/implementation_plan.md`: refine the contract to the concrete execution slice.
- `tasks/validation_plan.md`: expand coverage around the same contract fields instead of inventing a new schema.
- `tasks/feature_development.md`: carry the current contract through implementation and update it when the proof surface changes.

## Quick Mapping
- compile health or define-matrix claim -> `batch_compile` -> `compile matrix across build-config profiles`
- artifact output correctness -> `batch_compile` -> `artifact build exit + artifact presence`
- generated manifest, plist, Gradle, or Xcode mutation -> `batch_compile` -> `generated manifest inspection`
- live editor, console, hierarchy, or Game View state -> `interactive_mcp` -> `interactive scene snapshot`
- ordered runtime transition proof -> `scenario` -> `persisted runtime sequence evidence`

## Compact Examples

### Build-sensitive feature
- `primary_validation_lane`: `batch_compile`
- `secondary_validation_lane`: `none`
- `lane_selection_reason`: `artifact correctness depends on generated outputs`
- `expected_evidence_class`: `artifact build exit + artifact presence`
- `validation_gaps`: `none`

### Runtime scene-state feature
- `primary_validation_lane`: `interactive_mcp`
- `secondary_validation_lane`: `none`
- `lane_selection_reason`: `live scene and console state are the real proof surface`
- `expected_evidence_class`: `interactive scene snapshot`
- `validation_gaps`: `device-native behavior still unproven`

### Ordered runtime flow
- `primary_validation_lane`: `scenario`
- `secondary_validation_lane`: `interactive_mcp`
- `lane_selection_reason`: `state change must be observed across ordered editor-integrated steps`
- `expected_evidence_class`: `persisted runtime sequence evidence`
- `validation_gaps`: `none`
