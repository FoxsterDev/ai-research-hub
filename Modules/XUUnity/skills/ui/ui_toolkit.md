# Skill: UI Toolkit

## Use For
- editor-facing UI
- runtime UI Toolkit flows if the project already standardizes on it

## Rules
- Prefer UI Toolkit where retained-mode behavior is a clear fit.
- Do not mix UI Toolkit and UGUI on the same runtime flow without a reason.
- Validate event, focus, and navigation behavior on both iOS and Android.
- Avoid broad style or tree rebuilds on frequently updated screens.
