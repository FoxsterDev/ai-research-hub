# Skill: PrimeTween

## Use For
- PrimeTween implementation
- PrimeTween bug fixing
- PrimeTween code review
- UI fade, scale, move, and sequence flows built on PrimeTween
- null, destroyed, disabled, or stale tween target diagnosis
- callback allocation review for PrimeTween usage
- DOTween-to-PrimeTween migration review

## Rules
- Treat tween handles as non-reusable. After completion or manual stop, create a new tween for the next animation.
- Keep the tween owner explicit. The owning view, presenter, or component should decide when a tween may start, stop, or be replaced.
- Default to PrimeTween's zero-allocation delegate forms. Always try to bind callbacks with an explicit target for `OnComplete`, `OnUpdate`, `Tween.Delay`, `Tween.Custom`, `Tween.ShakeCustom`, and sequence callback APIs.
- In code review, flag closure-capturing PrimeTween callbacks unless the allocation is clearly irrelevant for that path.
- Do not assume repeated open/close or show/hide flows must stop the previous tween first. PrimeTween normally starts the new tween from the current state and overwrites prior tweens on the same target/property.
- Store active `Tween` or `Sequence` handles only when the owner truly needs explicit `Stop()`, `Complete()`, pause, progress control, or duplicate-spam protection.
- Check `isAlive` before calling `Stop()` or `Complete()` on stored handles.
- If code can create duplicate tweens every frame or every layout/update tick, stop or redesign that path instead of relying on overwrite behavior.
- Prefer `Sequence` for hot or frequently repeated flows. Coroutines and `async`/`await` are valid, but they allocate.
- When waiting in coroutines, prefer `.ToYieldInstruction()` over generic coroutine waits for tween completion.
- Use inspector-driven `TweenSettings<T>`, `ShakeSettings`, and `WithDirection(...)` when the animation shape is stable and should be tuned without code changes.
- For `Tween.Custom(...)`, prefer target-bound overloads that take typed settings such as `TweenSettings<float>`, `TweenSettings<Vector2>`, or `TweenSettings<Vector3>` instead of obsolete `TweenSettings` plus separate start/end overloads.
- When `Tween.Custom(...)` needs both explicit start/end values and shared timing config, build `new TweenSettings<T>(startValue, endValue, settings)` first, then call `Tween.Custom(target, tweenSettings, callback)`.
- PrimeTween's target-bound `Tween.Custom(...)` overload order matters:
  - duration overload: `Tween.Custom(target, startValue, endValue, duration, callback, ...)`
  - typed-settings overload: `Tween.Custom(target, tweenSettings, callback)`
- Do not rely on guessed overload shapes for PrimeTween. If `Tween.Custom(...)` or another helper becomes ambiguous, check the installed package API before patching.
- Distinguish business-critical callbacks from cosmetic teardown callbacks. If target destruction during close is expected and harmless, consider `warnIfTargetDestroyed: false` on that specific callback path instead of treating it as a bug by default.
- Do not start a child tween after disabling, unloading, or closing the parent hierarchy that contains its target unless the tween target lives under a surviving owner or the teardown path intentionally tolerates target destruction.
- For popup-style UI, resolve close-order first:
  - animate the child before parent shutdown starts, or
  - skip animation and close the child immediately, or
  - move the animated object under a lifetime that survives the parent close
- For null-target or destroyed-target errors, inspect inspector assignment, destroy order, disable order, active-in-hierarchy state, and parent hierarchy teardown before changing easing, duration, or animation type.
- Use `Tween.StopAll(onTarget: ...)`, `Tween.CompleteAll(onTarget: ...)`, or `Tween.SetPausedAll(...)` only for broad owner cleanup when explicit stored handles are unavailable or materially less safe.
- For projects that care about runtime allocations, size PrimeTween early with `PrimeTweenConfig.SetTweensCapacity(...)` during launch or level-load setup, not during active gameplay.

## Review Checklist
- Is the tween target guaranteed to be valid at animation start time?
- Is the code using target-bound callback overloads so the tween path stays zero-allocation where it matters?
- If callbacks are not target-bound, is that allocation acceptable for the actual call frequency?
- Can parent close or dispose logic invalidate the target before the tween begins?
- If target destruction is expected during teardown, is `warnIfTargetDestroyed: false` used only on cosmetic paths and not as a blanket silence switch?
- Are repeated open/close or show/hide calls relying on normal overwrite behavior, or does this path actually require a stored handle for explicit control?
- Could this code accidentally create duplicate tweens every frame?
- Does a hot path use `Sequence` instead of coroutine or `async` choreography?
- Does `OnDisable`, dispose, or equivalent cleanup stop long-lived tweens that should not survive the owner?
- If inspector-tuned animation settings would reduce magic values and code churn here, should this use `TweenSettings<T>` or `WithDirection(...)`?
- Does `Tween.Custom(...)` use the current non-obsolete overload, especially when combining target binding with settings reuse?

## Debug Notes
- Use the PrimeTween manager in play mode to inspect running tweens and their targets.
- Supplying useful targets to delayed or custom tweens improves debugging and ownership tracing.
- If a tween starts on an inactive hierarchy object, check whether the disabled-target warning is revealing a real lifecycle bug.
- Use the manager's max-alive count to estimate a safe `SetTweensCapacity(...)` value before shipping allocation-sensitive flows.
