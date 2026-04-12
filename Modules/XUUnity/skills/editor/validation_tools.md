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
