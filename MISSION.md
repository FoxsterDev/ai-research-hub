# AIRoot Mission

`AIRoot` exists to be a reusable AI architecture module, not a host-repo dump.

## Mission
Keep `AIRoot` public-safe, reusable, and host-agnostic so it can be attached to different repositories as a stable AI module.

## Core Rules
- Treat `AIRoot` as read-mostly reusable infrastructure.
- Keep canonical reusable modules, designs, templates, and generic operations here.
- Do not store host-specific mutable state in `AIRoot`.
- Do not store default generated reports, live registry data, or project-specific operational outputs in `AIRoot`.
- Do not hardcode one host repo, one machine path, or one project portfolio as the universal model.
- Let the host repo `Agents.md` decide how `AIRoot` is integrated.
- Let project `Agents.md` and `Assets/AIOutput/ProjectMemory/` remain the source of local truth.

## Practical Test
Before changing `AIRoot`, ask:

1. Is this reusable across multiple host repos?
2. Is it public-safe?
3. Does it belong to the module, not to one host repo's runtime state?

If any answer is `no`, it should probably live outside `AIRoot`.
