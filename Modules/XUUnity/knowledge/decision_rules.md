# XUUnity Decision Rules

- If guidance is reusable across repos and public-safe, store it in `AIRoot/Modules/XUUnity/`.
- If guidance is reusable across projects in this monorepo but not public-safe, store it in `AIModules/XUUnityInternal/`.
- If guidance is specific to one project, store it in `Assets/AIOutput/ProjectMemory/`.
- If a finding is temporary, investigative, or not yet validated, keep it in `Assets/AIOutput/`.
- When shared and project memory conflict, follow project memory.
- Prefer the safest compatible SDK version, not the newest version.
- Treat compatibility mismatch, native instability, and store compliance failure as blockers for SDK upgrades.
