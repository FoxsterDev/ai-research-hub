# Knowledge: Unity Cache Lifetime Gotchas

## When To Load
- a Unity-side cache holds `Texture2D`, `Sprite`, `AudioClip`, `AssetBundle`, or other GPU/native-memory-bound objects
- a popup or presenter that owns a cache is destroyed-and-recreated on every open
- diagnosing memory growth across logout/login, scene transitions, or repeated popup opens

## Two Unity-Specific Gotchas
- **Buried `static readonly Dictionary<,>` leaks native memory.** Looks instance-scoped to a reviewer; is process-wide. Disposing the class instance does not free GPU memory because GC does not call `Object.Destroy` on Unity objects. Fix: non-static instance field + `IDisposable` that iterates the dictionary and calls `UnityEngine.Object.Destroy()` before clearing.
- **Cache field on a short-lived consumer forces re-download per open.** A popup that constructs cache in `Initialize` and disposes in `OnDispose` re-downloads every entry on next open because the popup is reconstructed. Move the cache to a longer-lived owner.

## Choosing The Longer-Lived Owner
Pick the pattern by what owns the upstream data lifecycle. There is no single "right" answer — pick honestly.

| Pattern | When it fits | Trade-off |
|---|---|---|
| Constructor inject into a long-lived facade (service locator / DI container / app-root service facade) | Project already has a long-lived facade and cache lifetime should match a service that lives there. | Couples the cache to the facade. Easiest to test with DI. |
| Addressables-managed lifecycle (`AsyncOperationHandle` per asset, `Release` on the handle) | Cache content is already a Unity asset, project uses Addressables, and `Resources.Load` / `UnityWebRequest` is being replaced. | Adds a dependency on Addressables. Best when assets are content-pipeline-shaped. |
| ScriptableObject-scoped store, with `Object.Destroy` on entries during scene transition | Cache lifetime is bounded by scene or session boundary. | Tight coupling to scene lifecycle. |
| Lazy singleton with explicit reset (`GetOrCreateShared` + `ResetShared`) | Cache lifetime is bounded by a refresh boundary in remote data (catalog, manifest, remote config). No DI container in the project. | Static surface area on the cache class. Less testable than constructor injection. Reset must be called by the data layer; missing this call silently keeps stale entries. |

The lazy-singleton + reset shape is the easiest one to reach for when there is no DI container, but it is not necessarily the best one for a given project — constructor injection into a facade is usually preferred when the project already has one.

## Anti-Patterns
- `cache?.Dispose()` in a popup presenter's `OnDispose` when the presenter is recreated on every open. Re-downloads on next open.
- `Object.Destroy` on a `Texture2D` that is still bound to an active `RawImage` or `Material`. Renders as a pink quad. Sequence dispose after consumers stop using the cache.
- `RawImage` left with a null texture renders a solid white quad. Hide an unresolved icon by toggling `Graphic.enabled` (or the GameObject), not by only clearing the texture. For a remote/cached image, render the cache-owned `Texture2D` through a `RawImage` rather than a per-consumer runtime `Sprite.Create` — no per-row allocation, and the cache keeps owning the texture.
- Reset called on every refresh attempt regardless of whether the data changed. Defeats the cache. Reset only when upstream identity changed.

## Persisted Snapshot Policy
- When parser, filtering, deduplication, or eligibility semantics change for a persisted runtime snapshot, add or bump a local cache-policy version and reject stale disk snapshots whose policy does not match.
- Do not rely on TTL or fetched-at freshness to migrate semantic policy. A fresh-enough file can still encode old parser behavior.
- Keep the policy version local to the client/runtime cache contract unless the upstream API has its own explicit version that controls the same semantics.

## Validation Focus
- open the same popup 10 times in a row. Expect 1× download on first open, 0× on opens 2–10.
- profile native GPU memory across 5–10 opens on a low-tier Android device. The shared cache plateaus; a `static readonly Dictionary` keeps growing across refreshes; a per-consumer cache shows downloads but plateaus equally.
