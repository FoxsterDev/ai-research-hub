# Skill: Pooling And Spawn Budget

## Use For
- frequent VFX spawn
- repetitive gameplay feedback

## Rules
- Budget spawn counts for low-end devices first.
- Pool expensive effects and warm critical pools before gameplay spikes.
- Avoid per-spawn allocations and hidden material instancing on hot paths.
- Fail gracefully if VFX budget must be clamped under stress.
