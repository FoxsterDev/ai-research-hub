# XUUnity Knowledge: Unity Validation Boundaries

Use this file when validation strategy depends on whether Unity-aware evidence must come from MCP, direct Unity CLI, shell compile, or a build-config-driven compile matrix.

## Rule
- Do not assume that a direct Unity CLI path is valid just because the Unity executable exists locally.
- If a project exposes a supported Unity MCP path, use that MCP path as the default Unity-aware validation route.
- When Unity MCP is available for the active project, treat shell compile, direct Unity CLI, and ad hoc editor automation as fallback-only paths unless a project-local rule says otherwise.
- If repo or project rules require MCP or another integrated path, treat that as a hard must-not for direct shell-launched Unity automation.
- This hard must-not includes direct Unity editor launches, `-batchmode`, `-runTests`, `-executeMethod`, and comparable shell-driven editor automation unless the repo or project exposes an approved batch lane for compile-only or EditMode-test-only validation.
- When an approved batch lane exists, keep it narrow:
  - compile and define-matrix validation may use that lane
  - deterministic EditMode tests may use that lane
  - play mode operations, scene-state inspection, Game View, and runtime choreography still require an interactive integrated lane
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
- A local `file:` UPM package is compiled separately by every consumer project, so the owning project's green compile is not evidence for any consumer once a public or internal API signature changed; the obligation is one compile per consumer project.
- Include the templates that seed future consumers in that fan-out: protocol snippets, integration prompts, and scaffold code carry the old signature until they are updated in the same change.
- Treat artifact-build validation as a different proof class from compile validation.
- For long-running artifact builds, prefer an approved batch build lane over an interactive scenario lane when the claim depends on:
  - process exit
  - generated artifact presence
  - generated manifest, plist, Gradle, or Xcode output
  - compact build summary artifacts
- Do not treat an interactive scenario waiter as the primary correctness proof for artifact builds when an approved batch lane exists.
- For build-sensitive questions, trust generated outputs above source-only reasoning when both are available.
- If the issue depends on postprocess mutation or build output shaping, inspect generated outputs first instead of concluding from source manifests, processors, or editor settings alone.
- Treat `scenario_already_running` or equivalent serialization signals as lane-contract evidence, not as generic flaky transport failure.
- When using ordered Unity MCP scenario validation, follow `knowledge/mcp_scenario_authoring.md` for scenario step order and settle boundaries after mutating hooks.
- If a validation lane can start work but cannot provide trustworthy final accounting for the claim, downgrade that lane's evidence strength and keep the validation gap explicit.

## Claim-To-Proof Routing

- Documentation-only and router-only changes need focused static contract proof;
  they do not acquire Unity runtime authority from an unrelated editor smoke.
- A contained C# change needs the affected assembly compile and the narrowest
  relevant test. When a public package API changes, also compile every affected
  consumer and update the templates or snippets that seed future consumers.
- A scene, prefab, UXML, importer, or other serialized-asset change needs save,
  import, and reload freshness plus identity for the changed asset. Use an
  interactive scene/prefab assertion when wiring or serialized state is the
  claim; script compilation alone is not evidence for that content.
- A domain-reload, editor-startup, or editor-lifecycle claim needs an integrated
  lifecycle sequence that crosses the relevant reload/start/close boundary and
  reaches trustworthy terminal accounting. A batch compile cannot prove it.
- A save-format or data migration claim needs fixtures for each supported prior
  state, idempotence or bounded repeat behavior, failure/recovery evidence, and a
  representative runtime lane. Fresh-state success alone is insufficient.
- An Addressables or content-catalog claim needs the generated catalog/build
  artifact and its identity. If the claim concerns load timing, residency,
  stripping, or first-use behavior, editor evidence cannot close it; use the
  representative player/device tier or report the gap.
- A native SDK, permission, entitlement, manifest, plist, Gradle, or Xcode claim
  needs generated-build inspection. Callback delivery, OS permission UX,
  performance, and bridge behavior remain physical-device-only claims until
  proven on device.
- A release claim needs the declared Unity-version and build-target matrix,
  package-source and consumer-project validation where both exist, and every
  mandatory release gate. Record intentional failures and waivers as release
  blockers or explicit gaps, never as green evidence.

## Evidence Provenance
- Evidence belongs to the exact artifact that produced it. Before treating a run as proof, establish content identity that shows the artifact under test contains the change.
- For a player build, record the originating commit and whether the source tree was clean or dirty. When it was dirty, also record a stable diff or content digest, or a build manifest or artifact id that incorporates the local changes. A build timestamp is supporting metadata, never proof of content identity by itself.
- For an editor-integrated lane, match the freshness proof to the changed content: compiler completion after a script edit; import, save, or reload completion plus an asset identity, revision, or captured editor state for scenes, prefabs, UXML, textures, import settings, and other non-code assets. A script recompile alone does not prove that changed non-code content is loaded.
- A green run on an artifact that predates the fix is not weak evidence for the fix, it is evidence about a different build. Treat an artifact whose identity cannot be established the same way and rebuild instead of reasoning from it.
- State the identity that was established next to the result, so a later reader can tell which build the claim belongs to.

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
- a started-but-untrustworthy test run that cannot provide correct final totals or pass/fail accounting
- a scenario submission that stayed transport-alive but never reached trustworthy artifact or terminal-result proof

## Editor-Resident Evidence Versus Player-Runtime Behavior
Bounded criteria, not a universal law: apply this only when the claim under validation is about
asset residency or load timing. For layout, wiring, reference integrity, and content correctness,
editor-side inspection remains representative and this section does not apply.

- In the editor the asset database is fully resident, referenced assets are live objects, nothing
  is stripped, and no device decodes a texture. A defect whose mechanism is *whether an asset is
  resident at the moment it is first used* therefore cannot appear in editor-side evidence. This
  is a property of the lane, not an oversight in how it was run.
- Consequently, a green editor tree/reference snapshot is evidence that references resolve, and is
  **not** evidence that the referenced assets will be resident in a player build at first render.
  The same snapshot returns green for a build that exhibits the defect.
- Recognize the signal shape that puts a claim in this category: the symptom is transient,
  self-heals on a later attempt, clears on an application restart, appears on some devices only,
  or presents as several sibling views losing their content simultaneously while unrelated
  subsystems render correctly. Any of these means editor evidence cannot close the question.
- This extends the existing rule that a single representative compile does not satisfy a contract
  that varies by define set or target (`## Rule`). Same doctrine, different axis: there, evidence
  must cover the target matrix; here, evidence must come from the runtime tier where the mechanism
  exists. Its exception is preserved — when the claim does not vary along that axis, one
  representative signal is still enough.
- When no player-runtime lane is available, do not silently downgrade the proof target. State the
  gap explicitly as an asset-residency validation gap and say which claims it leaves open.
- For a symptom in this category that produces no log line, the first deliverable is a detector,
  not a fix: nothing about it is falsifiable until an occurrence leaves a trace. Verify that the
  detector's own delivery channel is actually collected in the environments you need it in —
  a diagnostic emitted on a channel a given build does not report is indistinguishable from the
  defect not occurring.

## Output Rule
- When Unity validation is blocked by MCP-only or project-local rules, say so explicitly.
- Describe any shell-side checks as partial compile or syntax signals, not as proof that Unity validation passed.
- If confidence depends on Unity/editor validation that was not run, keep that uncertainty visible in the final answer.
- If MCP was available for the project and not used, state the reason explicitly.
- If build-profile validation was required but the full target/profile matrix was not executed, do not call the work fully validated.
- If artifact correctness was the real question and only source inspection was performed, describe that as weaker evidence than generated-build inspection.
- If a lane lacked trustworthy final accounting for tests, artifact completion, or terminal result state, say so explicitly instead of calling the work validated.
- If the claim was about asset residency or load timing and only editor-side evidence exists, say that the lane cannot close it.
