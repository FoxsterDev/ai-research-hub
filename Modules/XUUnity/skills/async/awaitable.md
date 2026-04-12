# Skill: Awaitable

## Use For
- Unity `Awaitable`
- engine-native async flows
- subsystems that standardize on `Awaitable`

## Rules
- Use `Awaitable` only where project memory or subsystem conventions justify it.
- Keep boundaries explicit when mixing `Awaitable` with `UniTask` or `.NET Task`.
- Do not introduce `Awaitable` into a subsystem that already has a stable async standard without a migration decision.
- Validate lifecycle and cancellation behavior before broad adoption.

## Review Focus
- subsystem consistency
- boundary clarity
- lifecycle correctness
