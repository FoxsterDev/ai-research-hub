# XUUnity Knowledge Extraction Triage: Unity Lifetime Ownership

## Source
- Type: external technical article, verified against public Unity and Microsoft documentation.
- Topic: C# `Dispose`, GC, finalizers, `UnityEngine.Object` destruction, Addressables, NativeContainer, and resource lifetime ownership in Unity.
- Scope: public-core reusable Unity guidance; no project-private source inspected.
- Primary source: https://dev.to/gamedevtoollab/a-deep-dive-into-c-dispose-gc-finalizers-and-unityengineobject-destruction-3175
- Access date: 2026-07-02.
- Source summary: The article separates managed heap reachability, explicit ownership cleanup, Unity engine object destruction, Addressables reference counts, NativeContainer disposal, and Unity asset unloading. The durable value is an ownership-first cleanup model: choose `Dispose`, `Destroy`, `Release`, `ReleaseInstance`, `ReleaseTemporary`, `UnloadUnusedAssets`, or GC reasoning by owner and resource family, not by type name alone or by the belief that GC eventually fixes everything.

## Selected Stack
- Router: `Operations/XUUnityAiCliOrchestrator/Agents.md`, `Operations/XUUnityLightUnityMcp/Agents.md`.
- Core task entrypoint: `Modules/XUUnity/tasks/start_session.md`.
- Primary role: `Modules/XUUnity/role/researcher.md`, with `Modules/XUUnity/role/base_role.md` baseline.
- Core baseline skills: `skills/core/README.md`, `unity6000_baseline.md`, `mobile_runtime_safety.md`, `zero_crash_zero_anr.md`, `critical_flow_protection.md`, `sensitive_data_handling.md`.
- Utility stack: `utilities/knowledge_extraction_triage.md`, `utilities/knowledge_extract.md`, `utilities/knowledge_ingest_from_link.md`, `utilities/knowledge_intake_review.md`, `utilities/knowledge_intake_review_report_template.md`.
- Knowledge for routing and placement: `knowledge/decision_rules.md`, `knowledge/execution_contract.md`, `knowledge/validation_contract.md`, `knowledge/validation_lanes.md`, `knowledge/unity_validation_boundaries.md`, `knowledge/risk_classification.md`.
- Existing-coverage files checked: `knowledge/cache_lifetime_ownership.md`, `knowledge/assetbundle_compatibility.md`, `codestyle/unity.md`, `skills/native/ownership.md`, `skills/optimization/allocation_control.md`, `skills/mobile/lifecycle_boundaries.md`, `platforms/performance.md`.

## Inferred Risk Class
- Risk class: `low` for this triage action because no source code, shared prompt, skill, or project memory is integrated yet.
- Integration risk if approved: `moderate`, because a bad merge could steer future memory, lifecycle, and cleanup reviews toward incorrect ownership advice on critical mobile runtime paths.

## Derived Execution Contract
- `resolved_project`: `AIRoot public XUUnity core`
- `primary_task`: `utilities/knowledge_extraction_triage.md`
- `overlay_tasks`: `knowledge_ingest_from_link.md`
- `matched_skills`: `skills/core/*`, `role/researcher.md`
- `matched_policy_packs`: `none`
- `matched_private_packs`: `none`
- `private_pack_report_references`: `none`
- `trigger_reasons`: `xuunity extract knowledge`, `external Unity/C# lifetime source`, `Dispose/Destroy/GC/Addressables/NativeContainer signals`
- `risk_class`: `low`
- `root_cause_chain_checked`: `source article -> public docs verification -> existing public-core coverage -> candidate destination`
- `patch_shape`: `none`
- `pre_patch_blockers`: `explicit user approval required before any integration`
- `primary_validation_lane`: `none`
- `secondary_validation_lane`: `none`
- `lane_selection_reason`: `none`
- `expected_evidence_class`: `none`
- `validation_contract`: `primary_validation_lane=none; secondary_validation_lane=none; lane_selection_reason=none; expected_evidence_class=none; validation_gaps=review-only triage; no Unity project behavior claim`
- `why_not_local_fix`: `this is knowledge routing, not a source-code fix`
- `validation_gaps`: `no project-specific Unity validation run; source claims only checked against public docs and existing prompt files`
- `required_validation`: `user review of proposed destination before integration`
- `required_self_review`: `avoid duplicating existing cache-lifetime guidance; keep public-safe API specifics; preserve version-sensitive Unity 6.2 context`

## Missing Project Memory
- No project memory was loaded because the source is a public reusable knowledge candidate and no concrete Unity project path was referenced.
- No `AIModules/XUUnityInternal/` overlay was present in this workspace.

## Main Risk Areas
- Over-generalizing cleanup rules into "Destroy every UnityEngine.Object" or "Dispose every field".
- Treating `GC.Collect()` as a memory leak fix instead of managed-heap reachability work.
- Hiding important version-sensitive context around Unity 6.2 GC behavior.
- Adding a new standalone knowledge file even though `knowledge/cache_lifetime_ownership.md` already covers part of the same doctrine.
- Collapsing Addressables loaded-asset release, instantiated-object release, manually instantiated prefab cleanup, and load-handle lifetime into one vague "release/destroy" rule.

## Critical Flows That Must Not Regress
- Startup and scene loading memory behavior.
- Mobile low-memory resilience.
- Runtime-created textures, materials, render targets, VFX, and prefabs.
- Addressables-backed content and dependency lifetimes.
- Jobs/NativeContainer lifetime boundaries.
- Ads, rewards, purchases, and other flows that allocate or destroy runtime resources while the user is waiting.

## Validation Focus
- Thread safety: NativeContainer disposal must respect JobHandle completion; cleanup must not race consumers.
- Exception safety: `Dispose`/cleanup paths should be idempotent and avoid throwing on normal repeated teardown.
- Performance: do not replace ownership fixes with full blocking GC calls or heavy `Resources.UnloadUnusedAssets()` in hot paths.

## Source Verification
- Unity 6.2 GC docs support the article's core GC framing: incremental GC is default, `System.GC.Collect()` is full/blocking in Unity's configuration docs, and disabled GC mode prevents collection.
- Unity `Object.Destroy` docs support delayed destruction after the current Update loop and before rendering, and clarify component/GameObject destruction effects.
- Unity `Resources.UnloadUnusedAssets` docs support the distinction between Unity asset reachability and normal C# stack reachability.
- Unity Addressables docs support reference-counted loaded assets, mirrored load/release calls, and `ReleaseInstance` for objects created by `InstantiateAsync`.
- Microsoft finalizer and Dispose-pattern docs support the article's finalizer cautions, explicit cleanup guidance, and SafeHandle preference.

## Extracted Durable Rules

### Rule 1: Cleanup is selected by ownership boundary
- Problem: Unity code often treats GC, `Dispose`, `Destroy`, Addressables release, and asset unloading as interchangeable cleanup mechanisms.
- Solution: Decide what lifetime the current owner actually controls before choosing the API.
- Rule: For every resource cleanup review, ask "who created or acquired this, who owns it now, and what API closes that specific ownership?" before approving `Dispose`, `Destroy`, `Release`, `ReleaseInstance`, `ReleaseTemporary`, `UnloadUnusedAssets`, or GC-related changes.
- Confidence: high.

### Rule 2: `Dispose` closes explicit resource ownership; it does not delete managed objects
- Problem: Developers can expect `Dispose` to make an object disappear or to make GC run.
- Solution: Treat `Dispose` as a semantic lifetime close for unmanaged resources or owned disposable fields.
- Rule: Implement simple `Dispose()` for sealed owners of disposable fields; use the full Dispose Pattern only when inheritance or direct unmanaged ownership requires it; prefer `SafeHandle` for direct handles where possible.
- Confidence: high.

### Rule 3: Finalizers are last-resort safety nets, not normal Unity cleanup
- Problem: Finalizers run nondeterministically and are unsafe places to call Unity APIs or traverse managed ownership graphs.
- Solution: Use explicit ownership cleanup and keep finalizers only for direct unmanaged safety nets that cannot be represented with safer wrappers.
- Rule: Do not rely on finalizers for files, sockets, NativeContainers, Addressables, or runtime-created Unity objects; close those lifetimes through their owner-controlled API.
- Confidence: high.

### Rule 4: Runtime-created `UnityEngine.Object` instances require ownership-aware `Destroy`
- Problem: `Texture2D`, `Material`, `GameObject`, and similar objects have managed wrappers plus native engine resources; nulling C# references or collecting managed heap does not close the engine lifetime.
- Solution: If runtime code creates and owns the object, schedule destruction with `Object.Destroy` when the owner is finished and stop treating the reference as usable immediately after that call.
- Rule: Destroy runtime-created owned Unity objects; do not casually destroy imported assets, `sharedMaterial`, shared `Resources.Load` results, or Addressables asset results.
- Confidence: high.

### Rule 5: Unity object null checks are a lifetime check, not a normal C# null check
- Problem: A C# wrapper can still exist while Unity's native object has been destroyed or scheduled for destruction.
- Solution: Use explicit Unity `== null`/`!= null` checks on Unity object paths and avoid null-conditional/coalescing shortcuts.
- Rule: In reviews, treat Unity object's overloaded null behavior as a resource-lifetime signal; `ReferenceEquals`, `is null`, generic comparisons, and `?.` do not substitute for Unity null checks.
- Confidence: high.

### Rule 6: `GC.Collect()` is not a lifetime-management fix
- Problem: Manual GC calls are sometimes used to hide leaked references or missed explicit cleanup.
- Solution: Inspect references and owner cleanup first.
- Rule: Before recommending `GC.Collect()`, check reachable roots, static fields, event subscriptions, cache ownership, missed `Dispose`, missed `Destroy`, Addressables releases, NativeContainer disposal, and temporary render texture release.
- Confidence: high.

### Rule 7: Addressables load, instantiate, and manually instantiated prefab lifetimes differ
- Problem: Teams can merge loaded-asset release and instance destruction into one vague cleanup step.
- Solution: Keep handle/result ownership separate from instantiated object ownership.
- Rule: Mirror `LoadAssetAsync` with Addressables release; mirror `InstantiateAsync` with `ReleaseInstance`; for manual prefab instantiation from an Addressables-loaded prefab, destroy the instance separately and keep/release the load handle according to remaining instance needs.
- Confidence: high.

### Rule 8: NativeContainer disposal must respect job ownership
- Problem: Disposing a `NativeArray<T>` or other NativeContainer while a scheduled job can still access it creates correctness and crash risk.
- Solution: Dispose synchronously only after work is complete, or use `Dispose(JobHandle)` when supported to chain disposal after the job.
- Rule: NativeContainer cleanup reviews must prove the owner knows whether a JobHandle still owns access before approving disposal.
- Confidence: high.

### Rule 9: `Resources.UnloadUnusedAssets()` is a heavy boundary tool, not routine cleanup
- Problem: It can be used as a substitute for actual owner cleanup, and its reachability model differs from C# GC.
- Solution: Use it at large loading or scene boundaries only after references and explicit lifetimes are handled.
- Rule: Do not use `UnloadUnusedAssets()` to compensate for lingering static fields, event subscriptions, caches, Addressables handles, or runtime-created Unity objects; treat it as a coarse asset-unload boundary.
- Confidence: high.

## Candidate Outputs

### Review artifact candidate
- Candidate: "Unity resource lifetime ownership review checklist".
- Content shape: short checklist for memory-growth or cleanup reviews: identify owner, resource family, close API, delayed destruction semantics, Addressables handle ownership, NativeContainer job ownership, and proof that `GC.Collect()` or `UnloadUnusedAssets()` is not masking missed cleanup.
- Destination: keep inside this review package unless the user approves integration.
- Pedagogical value: a senior reader gets a compact review sequence that prevents cleanup API substitution, not just a list of APIs.

### Public-core shared knowledge candidate
- Candidate destination: update `AIRoot/Modules/XUUnity/knowledge/cache_lifetime_ownership.md` with a compact "Unity resource lifetime selector" section, or split to a new `knowledge/unity_resource_lifetime_ownership.md` only if the existing cache file is kept narrow and cross-linked.
- Preferred first apply shape: update the existing file, because it already owns the closest doctrine and has explicit triggers for `Dispose`, texture caches, Addressables, and memory growth.
- Trigger/reachability plan: current `tasks/start_session.md` already loads `knowledge/cache_lifetime_ownership.md` for `cache`, `Texture2D`, `Dispose`, static dictionary, repeated popup opens, and memory growth. If the approved update adds broader triggers such as `Destroy`, `GC.Collect`, `NativeArray`, `UnloadUnusedAssets`, or `Addressables.Release`, update the routing hint in the same apply step.
- Pedagogical value: a senior reader learns how to choose the cleanup API by owner/resource family across managed, Unity-native, Addressables, NativeContainer, and temporary render-target lifetimes.

### Skill candidate
- Candidate: no new skill family recommended.
- Optional minor skill refinement: `skills/native/ownership.md` could remain focused on native bridge wrapper ownership; do not dilute it with general Unity object cleanup unless a later native-interop source specifically requires that.
- Pedagogical value: none for a new skill file right now; the reusable material is decision doctrine more than workflow.

### Code style candidate
- Candidate: no update recommended.
- Reason: `codestyle/unity.md` already covers explicit Unity object null checks and forbids null-conditional/coalescing operators on Unity object paths.

### Project-only candidate
- Candidate: none.
- Reason: source is public and project-agnostic.

### External promotion candidate
- Candidate: maybe later.
- Reason: the article itself is public, but this extraction is a public-core decision table rather than a standalone external module.

## Existing Coverage
- `knowledge/cache_lifetime_ownership.md`: strongest overlap. Already covers static dictionaries leaking native memory, `Object.Destroy` for cached Unity objects, Addressables-managed lifecycle, owner lifetime selection, and popup cache lifetime. Missing broader Dispose/finalizer/GC.Collect/NativeContainer/UnloadUnusedAssets decision coverage.
- `codestyle/unity.md`: already covers Unity object null checks and null-conditional pitfalls. No change needed.
- `skills/native/ownership.md`: covers native bridge wrappers and Android Java wrapper borrowed ownership. Related but narrower; not the right destination for broad Unity lifetime selection.
- `knowledge/assetbundle_compatibility.md`: covers AssetBundle compatibility and dependency lifetime; not a general cleanup decision file.
- `skills/optimization/allocation_control.md`: covers allocation discipline, pooling, and cache decisions; `GC.Collect()` caution belongs better in shared knowledge than optimization skill text.
- `platforms/performance.md`: contains unrelated extracted timer lifecycle rules; not a good destination for this knowledge.

## Duplicate And Conflict Analysis
- No direct conflict found with existing public-core guidance.
- Main duplication risk: creating a new standalone lifetime file while `knowledge/cache_lifetime_ownership.md` already covers the nearest review trigger family.
- Best merge strategy: add a compact selector to the existing cache lifetime file first, then only split into a new file if the approved content would make the cache file semantically too broad.
- Hard placement check: this is not `codestyle/` because it is not naming or formatting guidance; it is not primarily `skills/` because it is not a workflow playbook; it is `knowledge/` because it defines ownership and resource-lifetime decision rules.

## Quality Evaluation

| Area | Score | Notes |
|---|---:|---|
| technical_quality | 4 | Aligned with official docs; keep Unity backend wording version-sensitive. |
| production_safety | 5 | Directly prevents memory leaks, invalid Unity object access, premature disposal, and blocking GC misuse. |
| Unity 6000+ relevance | 5 | Source assumes Unity 6.2 and was checked against Unity 6.2 docs. |
| mobile_relevance | 5 | Strong for low-memory, frame stability, loading, and teardown behavior on mobile. |
| novelty | 3 | Existing cache-lifetime file overlaps; broader decision matrix is still useful. |
| merge_fitness | 4 | Best as a compact update to existing shared knowledge, not a large imported summary. |
| expected_usefulness | 5 | Likely to change review outcomes for memory, asset, Addressables, and NativeContainer cleanup. |

## Impact Analysis
- Problem solved: reviewers get one ownership-first cleanup model instead of scattered API-specific folk rules.
- What becomes better if integrated: memory-leak reviews, cache teardown reviews, Addressables cleanup reviews, and Unity object lifetime reviews become more consistent.
- What does not improve after integration: project-specific memory profiling, device evidence, and actual code fixes still require project inspection and representative Unity/device validation.
- Semantic-loss risk: medium if the merge compresses all APIs into "call cleanup"; low if the merge preserves separate ownership families and examples.

## Recommendation
- Recommended action: prepare a shared knowledge update after user approval.
- Recommended apply scope: `apply shared knowledge only`.
- Candidate destination: `Modules/XUUnity/knowledge/cache_lifetime_ownership.md` first, with an optional routing hint update in `Modules/XUUnity/tasks/start_session.md` only if broader triggers are approved.
- Required narrowing: keep the integrated rule compact; avoid importing article narrative, jokes, basic C# tutorials, or code samples wholesale.
- Rejected destinations: `codestyle/` for not being style; `skills/native/ownership.md` for being bridge-specific; new skill family for low workflow value; project memory for not project-specific.

## Approval Options
- `apply shared knowledge only`
- `apply only routing trigger update`
- `apply review artifact only`
- `apply shared knowledge and routing triggers`
- `merge only rules 1, 4, 6, and 7`
- `reject`

## References
- Primary article: https://dev.to/gamedevtoollab/a-deep-dive-into-c-dispose-gc-finalizers-and-unityengineobject-destruction-3175
- Unity Manual, Configuring garbage collection: https://docs.unity3d.com/6000.2/Documentation/Manual/performance-disabling-garbage-collection.html
- Unity Manual, Garbage collection modes: https://docs.unity3d.com/6000.2/Documentation/Manual/performance-incremental-garbage-collection.html
- Unity Scripting API, Object.Destroy: https://docs.unity3d.com/6000.2/Documentation/ScriptReference/Object.Destroy.html
- Unity Scripting API, Resources.UnloadUnusedAssets: https://docs.unity3d.com/6000.2/Documentation/ScriptReference/Resources.UnloadUnusedAssets.html
- Unity Addressables Memory management overview: https://docs.unity3d.com/Packages/com.unity.addressables%402.2/manual/MemoryManagement.html
- Unity Addressables ReleaseInstance: https://docs.unity3d.com/Packages/com.unity.addressables%402.2/api/UnityEngine.AddressableAssets.Addressables.ReleaseInstance.html
- Microsoft Learn, GC.Collect: https://learn.microsoft.com/en-us/dotnet/api/system.gc.collect
- Microsoft Learn, Finalizers: https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/classes-and-structs/finalizers
- Microsoft Learn, Dispose Pattern: https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/dispose-pattern
