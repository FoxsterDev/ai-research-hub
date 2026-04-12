# Skill: Import Pipeline

## Use For
- asset import automation
- validation on import
- platform import settings

## Rules
- Enforce import settings that are critical for mobile memory, texture size, and compression.
- Avoid hidden import-time mutations that are hard to debug.
- Keep import hooks deterministic and idempotent.
- Separate validation from auto-fix when the change may be risky.
