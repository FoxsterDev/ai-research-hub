# XUUnity Skills

## Purpose
`skills/` contains reusable domain-specific guidance for `XUUnity`.
Use it to load only the best-practice context that matches the current task.

## Layering
1. Always load `skills/core/`.
2. Load only the task-specific skill families that are triggered by intent, keywords, code signals, or project context.
3. After shared skills are loaded, check `Assets/AIOutput/ProjectMemory/SkillOverrides/` for matching project-specific overrides.

## Rules
- Do not load all skill families by default.
- Do not duplicate codestyle or platform rules inside skills unless the skill depends on them.
- Shared skills stay project-agnostic.
- Project-specific constraints belong in `Assets/AIOutput/ProjectMemory/SkillOverrides/`.
- If a skill match exists, implementation or review is incomplete without the matched skill layer.

## Baseline
`skills/core/` is mandatory for all XUUnity tasks.
It defines the default Unity `6000+` mobile safety posture:
- zero crash
- zero ANR
- no microfreezes on critical flows
- performance-first implementation

## Skill Families
- `core/`
- `async/`
- `ui/`
- `editor/`
- `audio/`
- `fx/`
- `shaders/`
- `optimization/`
- `profiling/`
- `tests/`
- `architecture/`
- `refactoring/`
- `mobile/`
- `sdk/`
- `native/`

All skill families should stay mobile-oriented and production-safe for Unity iOS and Android projects.
