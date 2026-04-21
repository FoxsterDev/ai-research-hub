# Skill: Presenter Lifetime Split

## Derived From
- reviewed presenter lifetime extraction artifact
- reviewed presenter pattern comparison artifact

## Use For
- presenter-driven screen refactors
- popup or modal flow cleanup
- scene-root orchestration cleanup in Unity UI-heavy games

## Rules
- Do not force long-lived screens, one-shot popup flows, and scene startup roots into one lifecycle contract.
- Keep long-lived screen presenters responsible for owned state, rehydration, and repeated activation.
- If a popup or flow must return a final outcome, model that result explicitly instead of inferring it from close state.
- Keep scene roots thin; they should construct, start, and dispose the root composition object rather than own feature orchestration.
- Keep nested UI flows presenter- or controller-shaped instead of collapsing them into view logic during cleanup work.
