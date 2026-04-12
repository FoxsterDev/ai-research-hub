# Skill: SRP Batcher And Materials

## Use For
- URP material discipline
- draw-call stability

## Rules
- Prefer material usage patterns compatible with batching and predictable draw behavior.
- Avoid avoidable material cloning on runtime hot paths.
- Keep per-instance overrides explicit and measured.
- Validate whether visual customization breaks batching in gameplay or UI-heavy scenes.
