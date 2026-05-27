# AIReferenceWatch Utilities

Use this folder for reusable prompts, scripts, schemas, and operational helpers
that support reference ingestion, normalization, comparison, and reporting.

## First Slice

This first operational slice is intentionally dependency-light:

- `schemas/`
  - public JSON contracts for source registries, feature bags, comparison
    reports, reference-first reviews, and issue-watch summaries
- `prompts/`
  - reusable extraction and comparison prompts for agent-assisted review
- `scripts/`
  - Python `argparse` utilities that use only the standard library
- `examples/`
  - public-safe seed feature bags and generated example reports

The scripts consume normalized JSON feature bags. They do not fetch live
references, validate YAML, or require `PyYAML` / `jsonschema`.

The checked-in seed bags now include a first manual external-evidence pass for
`unity_mcp_coplay`, `unity_mcp_ivanmurzak`, and
`mcp_unity_codergamester`. Capabilities are promoted to `implemented` only when
tool registry, schema, manifest, or Unity-side handler evidence was reviewed.
Implemented reference capabilities can open backlog only when they are also a
direct analog; related broad surfaces use `directAnalog: false` and stay as
design input.
The first UI review is stored at
`examples/reviews/ui_primitives.reference_first_review.json`, with the source
evidence notes in `examples/reviews/external_evidence_review_2026-05-23.md`.
Transport and build-profile reference-first reviews are stored beside it.

Mutable crawler outputs should live outside this module, for example:

```text
AIOutput/Operations/ReferenceWatch/
  snapshots/
  normalized/
  reports/
  reviews/
```

Do not store host-private paths, secrets, downloaded repository snapshots, or
machine-local state in this public module.

## Quick Checks

Run the dependency-free smoke validator:

```bash
python3 Modules/AIReferenceWatch/utilities/scripts/validate_examples.py
```

Run the utility regression tests:

```bash
python3 -m unittest Modules/AIReferenceWatch/utilities/tests/test_reference_watch_utilities.py
```

Run the full seed workflow into host-local output:

```bash
python3 Modules/AIReferenceWatch/utilities/scripts/run_seed_workflow.py \
  --out-root AIOutput/Operations/ReferenceWatch
```

Regenerate the checked-in seed reports with deterministic timestamps:

```bash
python3 Modules/AIReferenceWatch/utilities/scripts/compare_feature_bags.py \
  --focus ui_primitives \
  --generated-at-utc 2026-05-23T00:00:00Z \
  --xuunity-id xuunity_light_unity_mcp \
  --bag Modules/AIReferenceWatch/utilities/examples/feature_bags/xuunity_light_unity_mcp.json \
  --bag Modules/AIReferenceWatch/utilities/examples/feature_bags/unity_mcp_coplay.json \
  --bag Modules/AIReferenceWatch/utilities/examples/feature_bags/unity_mcp_ivanmurzak.json \
  --bag Modules/AIReferenceWatch/utilities/examples/feature_bags/mcp_unity_codergamester.json
```

Checked-in examples use fixed `generatedAtUtc` values so diffs stay stable.
