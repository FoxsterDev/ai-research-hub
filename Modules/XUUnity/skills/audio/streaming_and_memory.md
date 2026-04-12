# Skill: Streaming And Memory

## Use For
- clip loading strategy
- long music tracks
- large voice or ambient assets

## Rules
- Choose preload versus streaming based on actual access pattern and memory cost.
- Avoid loading large audio assets synchronously on sensitive flows.
- Keep mobile memory ceilings in mind for Android low-memory devices and older iPhones.
- Audit compression, sample rate, and channel count for runtime value, not only quality.
- Treat large `DecompressOnLoad` clips as stability risks during ad, startup, and scene-transition flows on memory-constrained devices.
- Favor lighter channel count and memory footprint for UI and short feedback sounds unless the content clearly needs stereo detail.
