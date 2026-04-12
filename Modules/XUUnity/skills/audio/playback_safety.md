# Skill: Playback Safety

## Use For
- SFX
- music
- voice
- runtime audio triggers

## Rules
- Keep audio playback resilient to scene changes, pause, and resume.
- Do not create unbounded transient `AudioSource` churn on hot gameplay flows.
- Prevent duplicated playback on repeated callbacks or repeated button taps.
- Validate mute, focus loss, and interruption behavior on iOS and Android.
