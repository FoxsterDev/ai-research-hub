# Skill: UniTask

## Use For
- gameplay-facing async flows
- PlayerLoop-integrated async
- low-allocation Unity async work

## Rules
- Prefer `UniTask` for Unity-centric async flows when project memory does not require another primitive.
- Keep `UniTask` boundaries explicit when interacting with `.NET Task` or SDK callbacks.
- Use `Forget` only when the flow is intentionally detached and exception handling is explicit.
- Avoid unnecessary conversions between `UniTask` and `.NET Task`.

## Review Focus
- correct use of `UniTask`
- `Forget` safety
- conversion boundaries
- allocation discipline
