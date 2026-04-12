# Skill: Variant Control

## Use For
- shader keywords
- build size
- warmup control

## Rules
- Keep keyword usage bounded and intentional.
- Prevent unnecessary variant explosion from loosely controlled features.
- Audit startup and memory cost of variant-heavy rendering paths.
- Prefer shared material strategies that keep runtime branching and variant count under control.
