# AIReferenceWatch Continuation

Date: `2026-05-23`
Status: updated handoff snapshot after first hardening pass

## Goal

Continue `AIReferenceWatch` as the public module for reference-first comparison:

- inspect external AI/MCP references
- distinguish implemented capabilities from claims
- identify capability gaps
- produce reference-first design inputs for XUUnity and future AIRoot modules

Important constraint from the current work:

- `Operations/XUUnityLightUnityMcp/` is read-only unless the user explicitly
  allows edits there.

## What Was Done In This Slice

Implemented the first working operational slice under:

- `Modules/AIReferenceWatch/utilities/`

Added:

- public JSON schemas
- dependency-free Python utilities
- prompts
- seed feature bags
- reports for `ui_primitives`, `transport`, and `build_profiles`
- first reference-first UI review
- external evidence review
- utility regression tests

External references manually inspected:

- `CoplayDev/unity-mcp`
- `IvanMurzak/Unity-MCP`
- `CoderGamester/mcp-unity`

Source clones used for audit were host-local under:

- `/private/tmp/AIReferenceWatch-source-audit-20260523/`

They are not part of the public module.

## Key Evidence Conclusions

Coplay:

- `manage_ui` is implemented.
- `get_visual_tree` is implemented.
- `modify_visual_element` is implemented.
- direct `query`, `exists`, `get_text`, `click`, and semantic `wait_for` were
  not confirmed.

IvanMurzak:

- broad AiTool registry is implemented.
- tests, profiler, screenshots, reflection, GameObject/component tools are
  implemented.
- dedicated semantic UI primitives were not confirmed.

CoderGamester:

- Node MCP server registry plus Unity C# handlers are implemented.
- scene read/write and component mutation are implemented.
- dedicated UI primitives were not confirmed.

## Locked Rules

- `implemented` only with code/schema/registry/manifest/repo evidence.
- `claimed` never opens backlog by itself.
- `unknown` never opens backlog by itself.
- `contradicted` documents disproven broad inference and never opens backlog.
- Backlog candidates come only from implemented reference capabilities where
  `directAnalog` is not `false`.

## What Was Done After This Handoff Was Created

- Added direct analog metadata to feature bag schema and examples.
- Added direct analog metadata to comparison report reference statuses.
- Updated prompts with evidence and direct-analog checklists.
- Hardened comparison logic so implemented non-direct evidence does not create
  backlog.
- Added tests for implemented non-direct and contradicted capabilities.
- Regenerated `ui_primitives`, `transport`, and `build_profiles` reports.
- Added reference-first reviews for `transport` and `build_profiles`.
- Updated seed workflow to emit all three reference-first reviews.
- Drafted the downstream XUUnity read-only UI primitives design in
  `design/XUUNITY_READ_ONLY_UI_PRIMITIVES_DOWNSTREAM_DESIGN_2026-05-23.md`.

## Current Canonical Design Docs

Start here:

- `design/AIREFERENCEWATCH_FIRST_SLICE_LOCK_DESIGN_2026-05-23.md`
- `design/XUUNITY_UI_PRIMITIVES_REFERENCE_INPUT_DESIGN_2026-05-23.md`
- `design/XUUNITY_READ_ONLY_UI_PRIMITIVES_DOWNSTREAM_DESIGN_2026-05-23.md`
- `design/FEATURE_BAG_EVIDENCE_NORMALIZATION_DESIGN_2026-05-23.md`
- `design/REFERENCE_REPORT_WORKFLOW_ROADMAP_2026-05-23.md`

Current working artifacts:

- `utilities/examples/reports/ui_primitives.comparison.json`
- `utilities/examples/reports/transport.comparison.json`
- `utilities/examples/reports/build_profiles.comparison.json`
- `utilities/examples/reviews/ui_primitives.reference_first_review.json`
- `utilities/examples/reviews/transport.reference_first_review.json`
- `utilities/examples/reviews/build_profiles.reference_first_review.json`
- `utilities/examples/reviews/external_evidence_review_2026-05-23.md`

## Recommended Next Work

1. Move or adapt the downstream XUUnity read-only UI primitives design into the
   XUUnity operation when that operation is open for edits.
2. Keep `transport` and `build_profiles` reports current when new external
   evidence is reviewed.
3. Run live benchmarks only into `AIOutput/Operations/ReferenceWatch/`.
4. Start crawler/watch mode only after the UI contract design is stable.

Do not start crawler/watch mode until the UI contract design is stable.

## Verification Commands

```bash
python3 -B Modules/AIReferenceWatch/utilities/scripts/validate_examples.py
python3 -B -m unittest Modules/AIReferenceWatch/utilities/tests/test_reference_watch_utilities.py
python3 -B Modules/AIReferenceWatch/utilities/scripts/run_seed_workflow.py \
  --out-root /private/tmp/AIReferenceWatch-seed-workflow-check \
  --generated-at-utc 2026-05-23T00:00:00Z
find Modules/AIReferenceWatch/utilities/examples -name '*.json' -print0 \
  | xargs -0 -n1 python3 -m json.tool >/dev/null
```

## Suggested Next Chat Prompt

Use `Modules/AIReferenceWatch/CONTINUATION_2026-05-23.md` as the handoff.

Implement the next AIReferenceWatch pass:

- use the existing direct analog metadata and reports
- use `design/XUUNITY_READ_ONLY_UI_PRIMITIVES_DOWNSTREAM_DESIGN_2026-05-23.md`
  as the source for the XUUnity operation-owned implementation design
- keep `Operations/XUUnityLightUnityMcp/` read-only unless explicitly reopened
