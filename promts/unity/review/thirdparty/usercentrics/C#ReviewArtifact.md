# Engineering Review Artifact

## 1. Problem and Context
- **Problem**: Refactoring a critical, fragile, third-party consent integration (Usercentrics SDK) to improve safety, readability, and predictability without breaking the existing product flow. The initial implementation suffered from concurrency bugs, state corruption, blocking API calls without timeouts, and tight coupling to third-party data models.
- **Goal**: Achieve an "Enterprise Production Ready" consent manager. Establish a predictable API contract, eliminate race conditions, prevent Application Not Responding (ANR) states, isolate third-party data models, and provide robust structured logging.
- **Context**: Unity environment using C# and `UniTask` for async operations. Interactions involve third-party SDKs (MaxSdk, AppsFlyer, OneSignal, Facebook) and external server requests which dictate app startup flow.

## 2. Constraints
- **Runtime / platform constraints**: 
  - Third-party SDK callbacks can fire on background threads. Interacting with Unity APIs or other SDKs from a background thread can cause silent crashes or ANRs.
  - External network calls (SDK initialization, UI rendering) can hang indefinitely if the server is unreachable.
- **Performance constraints**: 
  - Minimize unnecessary memory allocations (e.g., specifying collection capacities, avoiding closure allocations inside repeated completion sources).
- **Correctness constraints**: 
  - Partial user consent (accepting some, denying others) must correctly propagate individual `true`/`false` values to respective SDKs rather than failing the entire batch.
  - The `AcceptedAllConsentsPref` must only be set to `true` if *all* consents are granted.
  - `TryApply` must safely support sequential execution (retry on fail, return cached result on success) while preventing concurrent execution.
- **API / usability constraints**: 
  - The `IConsent` interface must be stateless. Exposing mutable properties like `WasPopupShown` is dangerous as they can be read prematurely.

## 3. Core Technical Questions
- How do we safely manage concurrent calls to async initialization methods without using error-prone `UniTaskCompletionSource` caching?
- How do we protect the application startup from hanging if a third-party SDK fails to respond?
- How do we handle partial user consents accurately?
- How do we expose the result of a consent operation (cache hit vs. UI shown, user decision) without adding mutable state to the interface?
- How do we guarantee thread safety when returning from third-party SDK callbacks into Unity space?

## 4. Key Decisions and Conclusions

- **Decision**: Replace `UniTask.Preserve()` task caching with an explicit `OperationState` enum (`None`, `Running`, `Success`, `Failed`) and nullify tasks upon completion.
  - **Why it was chosen**: Prevents holding onto completed tasks in memory. Allows the state machine to control concurrent access (`if state == Running return existing task`), while safely supporting retries if the state transitions to `Failed`.
  - **Benefits**: Clearer lifecycle management, prevents multiple await exceptions, eliminates memory leaks from lingering tasks.
  - **Costs / tradeoffs**: Slightly more verbose than a simple cached `Lazy<UniTask>`.
  - **When this decision is valid**: When an asynchronous operation needs concurrency protection during execution but must allow sequential retries upon failure, without keeping the task object alive indefinitely.
  - **Confidence**: High.

- **Decision**: Isolate third-party SDK data types using an internal structural mapping (`ConsentData`).
  - **Why it was chosen**: "Zero trust" in third-party SDKs. Prevents SDK-specific types (`UsercentricsServiceConsent`) from leaking into core application logic.
  - **Benefits**: If the SDK changes its data structure or throws parsing exceptions, the blast radius is confined to the safe wrapper methods.
  - **Confidence**: High.

- **Decision**: Wrap all SDK interactions in `try-catch` blocks and use safe fallbacks (e.g., returning an empty list or assuming `true` for banner requirements on failure).
  - **Why it was chosen**: SDKs can return malformed JSON, null objects, or throw unexpected exceptions.
  - **Benefits**: Prevents startup crashes.
  - **Confidence**: High.

- **Decision**: Implement `CancellationTokenSource` with `CancelAfterSlim` to enforce timeouts on SDK initialization (10s) and UI interactions (60s).
  - **Why it was chosen**: SDK callbacks might never return if the network drops.
  - **Benefits**: Prevents infinite loading screens (ANRs).
  - **Confidence**: High.

- **Decision**: Enforce `await UniTask.SwitchToMainThread()` inside the `finally` block of all async SDK wrappers.
  - **Why it was chosen**: SDK callbacks may execute on background threads. Putting it in `finally` guarantees execution context recovery regardless of whether the operation succeeded, failed, or timed out.
  - **Benefits**: Ensures thread-safe state cleanup and safe continuation for callers.
  - **Confidence**: High.

- **Decision**: Refactor `IConsent.TryApply` to return a rich `ConsentApplyResult` struct instead of a `bool`.
  - **Why it was chosen**: Allows the caller to know if the operation succeeded, if the popup was shown (`WasPopupShown`), and what the specific decision was (`ConsentDecision` enum), all statelessly.
  - **Benefits**: Eliminates temporal coupling and race conditions associated with reading mutable properties post-execution.
  - **Confidence**: High.

## 5. Rejected or Dangerous Alternatives

- **Alternative / simplification**: Returning `false` and aborting all SDK updates if `allConsentsGranted == false`.
  - **Why it looked attractive**: Simple binary logic for tracking (all or nothing).
  - **Why it was rejected**: Violates GDPR intent. If a user grants partial consent, those specific SDKs *must* receive the `true` status, while others receive `false`.
  - **Likely failure mode**: Loss of valid analytics data and potential compliance violations.
  - **Final stance**: Rejected.

- **Alternative / simplification**: Adding `WasPopupShown` and `UserDecision` as properties on the `IConsent` interface.
  - **Why it looked attractive**: Easy to implement.
  - **Why it was rejected**: Creates a stateful API. Callers might read the properties before `TryApply` is finished, getting stale or default data.
  - **Likely failure mode**: Race conditions and invalid analytics events.
  - **Final stance**: Rejected.

- **Alternative / simplification**: Caching the `UniTaskCompletionSource.Task` directly.
  - **Why it was rejected**: Standard `UniTask` instances cannot be awaited multiple times. Concurrent callers awaiting the same task would trigger an `InvalidOperationException`.
  - **Final stance**: Rejected (Requires `.Preserve()` or explicit State/Task nullification).

- **Alternative / simplification**: Duplicating `SwitchToMainThread()` in `try` and `catch` blocks.
  - **Why it was rejected**: Code duplication and risk of bypassing the switch if an unexpected exception occurs before the catch block resolves.
  - **Final stance**: Rejected in favor of placing it in the `finally` block.

## 6. Critical Risks and Failure Modes

- **Risk**: Infinite Loading Screen (ANR)
  - **Trigger scenario**: Third-party SDK initialization hangs due to server outage; callback is never invoked.
  - **Impact**: Player cannot enter the game.
  - **Severity**: High
  - **Mitigation**: Strict timeouts (10s/60s) using `CancellationTokenSource` tied to `UniTaskCompletionSource.TrySetResult`.

- **Risk**: Main Thread Violation (Silent Crash)
  - **Trigger scenario**: SDK invokes success/error callback on a background thread pool; subsequent code attempts to touch Unity API or UI.
  - **Impact**: App crashes silently on production devices.
  - **Severity**: High
  - **Mitigation**: `await UniTask.SwitchToMainThread();` inside `finally` blocks of all async wrappers.

- **Risk**: Null Reference Exceptions from SDK Data
  - **Trigger scenario**: SDK dashboard configuration changes, resulting in `geolocationRuleset` or `consents` lists returning as `null`.
  - **Impact**: App crashes during consent evaluation.
  - **Severity**: High
  - **Mitigation**: Null-conditional operators (`?.`) and explicit null checks inside isolated `try-catch` wrappers.

- **Risk**: Multiple Await Exception
  - **Trigger scenario**: Two disparate systems call `Initialize()` simultaneously; both await the exact same standard `UniTask`.
  - **Impact**: `InvalidOperationException`.
  - **Severity**: Medium
  - **Mitigation**: State machine (`OperationState`) protecting task execution, returning the active task. (Note: standard UniTasks still shouldn't be multi-awaited unless preserved. Returning the active `_initializeTask.Value` to multiple concurrent callers *still* risks a multi-await exception unless the caller structure guarantees sequentiality or `.Preserve()` is used. *See Open Questions*).

## 7. Reviewer Checklist
- **Reject if** external SDK async calls are made without an explicit timeout mechanism.
- **Reject if** `try-catch` blocks wrapping async operations do not guarantee a return to the main thread via `finally`.
- **Require proof that** partial user consents are mapped and routed individually to respective SDKs, rather than treated as a binary pass/fail.
- **Verify that** lists instantiated from SDK data use pre-defined capacities (`new List<T>(capacity)`) to avoid reallocation overhead.
- **Verify that** interfaces representing asynchronous workflows return rich result structs rather than relying on mutable state properties.
- **Do not assume** third-party SDKs will return well-formed data. Require `null` checks on all nested objects.

## 8. Testing Strategy and Required Coverage

- **Failure path**: 
  - Mock SDK to never return a callback. Verify that the 10s/60s timeouts trigger, log the appropriate error, and allow the application flow to continue with default/empty consents.
  - Mock SDK to throw exceptions during initialization and parsing. Verify the `catch` blocks handle it gracefully without crashing.
- **State / lifecycle behavior**: 
  - Call `Initialize()` twice sequentially. Verify it hits the "already initialized" early return.
  - Call `Initialize()`, force a failure, then call `Initialize()` again. Verify the state resets from `Failed` and attempts the operation again.
- **Concurrency / race conditions**: 
  - Call `Initialize()` concurrently from two different threads/coroutines. Verify the state machine protects against double execution. (Verify multiple-await safety).
- **Happy path**: 
  - Verify that a mix of granted and denied consents correctly triggers `MaxSdk.SetHasUserConsent(true)` and `AppsFlyerClient.StartTracking(..., false)` respectively.

## 9. Reusable Engineering Principles
- **Zero Trust SDK Integration**: Never leak third-party data structures into core application logic. Parse them immediately into internal safe structs within `try-catch` boundaries.
- **Stateless Async Contracts**: If an async operation yields metadata (e.g., "was the UI shown?"), return that data in a struct alongside the success boolean, rather than mutating interface properties.
- **Finally-Driven Context Switching**: When bridging between external callbacks and Unity, place `await UniTask.SwitchToMainThread();` inside the `finally` block to guarantee context recovery regardless of exceptions.
- **Defensive Timeouts**: Wrap all external black-box async calls with `CancellationTokenSource.CancelAfterSlim` and `TrySetResult` fallbacks.

## 10. Open Questions and Uncertainties
- **Multiple Await on standard UniTask**: The code returns `_initializeTask.Value` to concurrent callers if `_initState == OperationState.Running`. If `_initializeTask` is not backed by `.Preserve()` or an `AsyncLazy`, awaiting it concurrently from multiple callers will throw an `InvalidOperationException`. The reviewer should verify if `UniTaskCompletionSource` (which backs `_initializeTask`) safely supports multiple awaits in the specific version of `UniTask` being used, or if `.Preserve()` needs to be reinstated for the cached task.
- **LogAttributes implementation**: The code assumes `new LogAttributes(key, value)` works cleanly with the custom logger. Verify the exact signature of `ILogger.LogError` to ensure compilation.

## 11. Final Reviewer Handoff
- **Safest implementation direction**: Isolate all SDK calls, enforce strict timeouts, and map data to internal structs.
- **Most dangerous area**: Bridging async callbacks from third-party SDKs back into Unity.
- **Most important invariant**: `await UniTask.SwitchToMainThread()` must execute in a `finally` block after any SDK callback await.
- **Easiest wrong simplification**: Using standard boolean properties on an interface to track the result of an async workflow.
- **Minimum required test coverage before production use**: Timeout trigger tests. Validate that if Usercentrics hangs, the game still loads successfully after 10 seconds.