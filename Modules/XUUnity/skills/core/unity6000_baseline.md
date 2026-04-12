# Skill: Unity 6000 Baseline

## Use For
- any Unity `6000+` task
- modern engine assumptions
- migration-safe decisions

## Rules
- Prefer solutions compatible with current Unity `6000+` APIs and lifecycle behavior.
- Do not assume legacy Unity limitations unless project memory says they still apply.
- Prefer engine-native patterns when they are stable, observable, and do not weaken safety or performance.
- Validate engine-version-sensitive choices through project memory before introducing new primitives or package dependencies.

## Review Focus
- engine-version compatibility
- lifecycle correctness
- package and API assumptions
