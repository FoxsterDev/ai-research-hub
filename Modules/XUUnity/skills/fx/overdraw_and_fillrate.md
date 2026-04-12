# Skill: Overdraw And Fillrate

## Use For
- transparent effects
- fullscreen flashes
- layered particles

## Rules
- Treat overdraw as a first-class mobile performance risk.
- Keep transparent and fullscreen effects bounded in duration and area.
- Avoid stacking large alpha-heavy effects over already expensive UI or post-processing.
- Validate GPU cost on representative mobile hardware, not only editor preview.
