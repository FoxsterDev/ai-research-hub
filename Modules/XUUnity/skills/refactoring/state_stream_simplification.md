# Skill: State Stream Simplification

## Derived From
- reviewed live state-wrapper simplification artifact

## Use For
- live connectivity or remote-state wrapper refactors
- event contract cleanup for monitor-style runtime services
- ownership cleanup around reducer, dispatcher, and subscriber flows

## Rules
- Keep mutable state in one explicit owner, preferably the reducer or equivalent state transition owner.
- Prefer explicit current-state reads over replay-on-subscribe when replay adds hidden delivery rules or reentrancy risk.
- Isolate subscriber failures so one consumer cannot block later consumers or paired event delivery.
- Prefer cheap semantic diff before heavy payload building when native or monitor callbacks are noisy.
- Keep bridge or plugin lifecycle instance-owned unless global ownership is an explicit public contract.
