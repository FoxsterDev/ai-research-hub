# Skill: Validation Tools

## Use For
- content validation
- pre-build checks
- release sanity checks

## Rules
- Validate assets, scenes, configs, SDK settings, and critical references before release.
- Prefer actionable validation messages over generic warnings.
- Group high-severity mobile blockers such as missing references, bad import settings, and conflicting SDK config.
- Keep validators easy to run in CI or pre-release workflows.
- After shared asset consolidation, audit scenes, prefabs, ScriptableObjects, and relevant `.meta` files for missing GUIDs and duplicate GUIDs.
- Make shared-asset audits source-aware: project-local duplicates are valid only when they are intentional visual or behavior overrides, not identical copies of the shared asset.
