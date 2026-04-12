# Skill: VFX Lifecycle

## Use For
- particles
- impact effects
- runtime spawned VFX

## Rules
- Make VFX lifetime explicit and cleanup deterministic.
- Avoid leaked effects across scene changes, pause, and pooled object reuse.
- Keep effect ownership clear when gameplay, UI, or SDK flows can interrupt playback.
- Prefer pooled reusable effects when spawn frequency is high.
