# XUUnity Decision Rules

- If guidance is reusable across repos and public-safe, store it in `AIRoot/Modules/XUUnity/`.
- If guidance is reusable across projects in this monorepo but not public-safe, store it in `AIModules/XUUnityInternal/`.
- If guidance is specific to one project, store it in `Assets/AIOutput/ProjectMemory/`.
- If a finding is temporary, investigative, or not yet validated, keep it in `Assets/AIOutput/`.
- When shared and project memory conflict, follow project memory.
- Prefer the safest compatible SDK version, not the newest version.
- Treat compatibility mismatch, native instability, and store compliance failure as blockers for SDK upgrades.
- Treat runtime client/build configuration as input, not mutable state. Compute effective remote or derived values locally at the feature or system boundary instead of merging them back into config objects at runtime.
- Prefer the narrowest existing owner for behavior changes. If a behavior can be resolved in a feature/helper/policy boundary, do not push the special-case logic into app-root or bootstrapper code.
- Keep shared public-core guidance project-agnostic. Do not use project-, product-, brand-, or repo-specific identifiers in shared examples or reusable rules.
- Do not add new shared knowledge unless it is reachable by an explicit load path, routing rule, or keyword/intent trigger. When adding knowledge, also verify how it will be selected during normal task assembly.
- Do not claim stronger validation than the evidence actually supports. When representative Unity validation tooling is unavailable, do not treat generated project-file `dotnet build` or `dotnet test` runs, or ad hoc substitute execution paths, as equivalent proof by default. Keep the validation gap explicit and prefer narrow source-level changes over inflated confidence.
- Do not assume that direct shell-launched Unity validation is allowed just because a Unity binary exists on disk. A repo, host-local overlay, or project router may require Unity validation to run only through MCP or another integrated path.
- Treat host-local and project-local validation-path constraints as hard overrides. If they forbid direct Unity CLI, batchmode, `-runTests`, or `-executeMethod`, do not run those paths and do not re-interpret substitute shell checks as equivalent proof.
