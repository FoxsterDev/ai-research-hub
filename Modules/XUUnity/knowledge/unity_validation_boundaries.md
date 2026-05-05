# XUUnity Knowledge: Unity Validation Boundaries

Use this file when validation strategy depends on whether Unity-aware evidence must come from MCP, direct Unity CLI, shell compile, or a build-config-driven compile matrix.

## Rule
- Do not assume that a direct Unity CLI path is valid just because the Unity executable exists locally.
- If a project exposes a supported Unity MCP path, use that MCP path as the default Unity-aware validation route.
- When Unity MCP is available for the active project, treat shell compile, direct Unity CLI, and ad hoc editor automation as fallback-only paths unless a project-local rule says otherwise.
- If repo or project rules require MCP or another integrated path, treat that as a hard must-not for direct shell-launched Unity automation.
- This hard must-not includes direct Unity editor launches, `-batchmode`, `-runTests`, `-executeMethod`, and comparable shell-driven editor automation.
- When opening Unity through an MCP wrapper or host helper, resolve the editor version from the target project's `ProjectSettings/ProjectVersion.txt`.
- For define-sensitive validation, treat the project's build-config asset as the source of truth for the compile matrix.
- Resolve the validation matrix from the project's `BuildConfigurationsBase` resource, typically a `*BuildConfiguration.asset` under `Assets/.../Resources/...`.
- Enumerate every required build profile under `Configurations`.
- For each build profile, use the profile's `CompilationCSharpSettings.ScriptingDefines` as the define set for validation.
- Success for define-sensitive validation requires Unity-aware compile evidence for every required build profile on both `Android` and `iOS` unless a project-local rule narrows that matrix.
- Status, health probes, or a single representative compile do not satisfy that contract when the change can vary by define set or target.
- Prefer a build-config-aware MCP compile route that derives the matrix from the asset and submits it through `unity.compile.matrix` or an equivalent integrated operation.
- When the lightweight `xuunity` MCP wrapper exposes `unity_compile_build_config_matrix` or `request-build-config-compile-matrix`, prefer that route over ad hoc per-profile compile requests.
- Do not hand-author per-profile define lists in chat when the project already has a build-config source of truth.
- Do not mutate `PlayerSettings.SetScriptingDefineSymbols*` as the default route for validation when the integrated MCP compile matrix can accept the per-profile define sets directly.

## Preflight
1. Confirm whether the task actually requires validation now, not merely a validation note.
2. Check the project router and project memory for validation-path constraints.
3. Check whether MCP or the declared repo-specific integration is available in the current session.
4. Resolve the project's build-profile source of truth before claiming define-sensitive validation is complete.
5. If MCP is available, use it first for Unity-aware validation.
6. If the required validation path is unavailable, keep the validation gap explicit instead of silently substituting a weaker path.

## Allowed Partial Signals
- source inspection
- native syntax checks
- generated project-file `dotnet build`
- targeted non-Unity shell compilation checks

## Not Equivalent To Unity Validation
- generated project-file `dotnet build`
- generated project-file `dotnet test`
- native syntax-only compilation
- ad hoc shell scripts that do not exercise the real Unity/editor integration path
- hand-authored define sets when the project has a build-config source of truth
- a single-target compile when the real contract requires both `Android` and `iOS`
- a single-profile compile when the real contract requires the whole project profile matrix

## Output Rule
- When Unity validation is blocked by MCP-only or project-local rules, say so explicitly.
- Describe any shell-side checks as partial compile or syntax signals, not as proof that Unity validation passed.
- If confidence depends on Unity/editor validation that was not run, keep that uncertainty visible in the final answer.
- If MCP was available for the project and not used, state the reason explicitly.
- If build-profile validation was required but the full target/profile matrix was not executed, do not call the work fully validated.
