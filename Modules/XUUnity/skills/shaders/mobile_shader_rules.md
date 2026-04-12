# Skill: Mobile Shader Rules

## Use For
- runtime shaders
- material authoring
- URP/Built-in mobile rendering

## Rules
- Prefer the simplest shader that meets the visual requirement.
- Treat fragment cost, overdraw, and texture bandwidth as mobile bottlenecks.
- Avoid desktop-oriented features that do not justify their battery and thermal cost.
- Validate quality tiers or fallbacks for weaker Android GPUs.
