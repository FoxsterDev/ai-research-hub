# Skill: Mixer And Snapshot Usage

## Use For
- AudioMixer routing
- snapshot transitions
- volume policy

## Rules
- Centralize runtime volume and category control.
- Use mixer snapshots for coherent transitions instead of scattered volume changes.
- Keep snapshot transitions lightweight and predictable during ads, pause, reward, and resume flows.
- Validate category handling for music, SFX, and voice if external SDKs affect audio focus.
