# Skill: Event Driven Design

## Use For
- event buses
- observer patterns
- decoupled subsystem messaging

## Rules
- Use events to reduce coupling, not to hide control flow.
- Keep event ownership and lifecycle clear.
- Guard against duplicate subscription, stale listeners, and callback storms.
- If a repeatable registration path attaches a stable event handler and duplicate delivery has no valid semantics, make the registration idempotent, for example with unsubscribe-before-subscribe.
- Avoid event chains that make crash, ANR, or hitch diagnosis difficult.
