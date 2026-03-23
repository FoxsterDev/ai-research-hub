# Engineering Review Artifact: Generic SDK Integrations

## 1. Problem and Context
- **Problem**: Integrating third-party SDKs (e.g., Analytics, Consents, Ads like AppsFlyer, Facebook, Usercentrics) introduces external points of failure, concurrency issues, thread safety risks, and data pollution into the core application.
- **Goal**: Establish a generalized, "Enterprise Production Ready" standard for wrapping and interacting with any third-party SDK. The wrapper must eliminate race conditions, prevent Application Not Responding (ANR) states, isolate third-party data models, and provide robust structured logging.
- **Context**: Unity environment using C# and `UniTask` for async operations. Interactions involve third-party black-box libraries and external network requests that operate outside the Unity Main Thread and dictate critical app flow (e.g., app startup, user tracking).

## 2. Constraints
- **Runtime / platform constraints**: 
  - Third-party SDK callbacks frequently execute on background threads (ThreadPool). Interacting with Unity APIs, Unity Objects, or other SDKs from these callbacks causes silent crashes or hard ANRs.
  - External network calls (SDK init, data fetching, UI rendering) can hang indefinitely without throwing an exception if the server is unreachable.
- **Performance constraints**: 
  - Minimize unnecessary memory allocations when mapping SDK arrays/lists to internal structures (e.g., specifying collection capacities).
- **Correctness constraints**: 
  - The application must not crash due to malformed, missing, or altered data models coming from an SDK update.
  - Initialization flows must safely support sequential execution (retry on fail, return cached result on success) while preventing concurrent execution (race conditions).
- **API / usability constraints**: 
  - The public interface of the SDK wrapper must be stateless. Exposing mutable properties to track async state (like `IsReady` or `WasUIOpened`) is dangerous as they can be read prematurely.

## 3. Core Technical Questions
- How do we protect the application flow from hanging if a third-party SDK fails to respond or hangs indefinitely?
- How do we guarantee thread safety when returning from third-party SDK callbacks back into Unity space?
- How do we safely manage concurrent calls to async initialization methods without causing multiple-await exceptions?
- How do we expose the rich result of an SDK operation without polluting the interface with mutable state?
- How do we prevent third-party data structures from leaking into the core business logic?

## 4. Key Decisions and Conclusions

- **Decision**: Isolate third-party SDK data types using an internal structural mapping immediately at the wrapper boundary.
  - **Why it was chosen**: "Zero trust" in third-party SDKs. Prevents SDK-specific types from leaking into core application logic.
  - **Benefits**: If the SDK changes its data structure, nullability rules, or throws parsing exceptions, the blast radius is confined entirely to the safe wrapper methods.
  - **When this decision is valid**: Always, for any third-party data model.
  - **Confidence**: High.

- **Decision**: Wrap *all* SDK interactions in `try-catch` blocks and use safe fallbacks.
  - **Why it was chosen**: SDKs can return malformed JSON, null objects, or throw unexpected exceptions during routine property access.
  - **Benefits**: Prevents startup crashes and allows the app to fallback gracefully (e.g., continuing with empty cached data).
  - **Confidence**: High.

- **Decision**: Implement `CancellationTokenSource` with `CancelAfterSlim` to enforce hard timeouts on SDK async operations.
  - **Why it was chosen**: SDK callbacks might never return if the network drops or the SDK experiences an internal deadlock.
  - **Benefits**: Prevents infinite loading screens (ANRs).
  - **Confidence**: High.

- **Decision**: Enforce `await UniTask.SwitchToMainThread();` inside the `finally` block of all async SDK wrappers.
  - **Why it was chosen**: SDK callbacks execute on background threads. Putting it in `finally` guarantees execution context recovery back to Unity regardless of whether the operation succeeded, failed, or timed out.
  - **Benefits**: Ensures thread-safe state cleanup and safe continuation for callers.
  - **Confidence**: High.

- **Decision**: Replace `UniTask.Preserve()` task caching with an explicit `OperationState` enum (`None`, `Running`, `Success`, `Failed`) and nullify tasks upon completion.
  - **Why it was chosen**: Prevents holding onto completed tasks in memory. Allows the state machine to control concurrent access (`if state == Running return existing task`), while safely supporting retries if the state transitions to `Failed`.
  - **When this decision is valid**: When an async initialization needs concurrency protection but must allow sequential retries upon failure, without keeping the task object alive indefinitely.
  - **Confidence**: High.

- **Decision**: Async wrapper methods should return rich `Result` structs rather than simple booleans.
  - **Why it was chosen**: Allows the caller to know metadata (e.g., "was it a cache hit?", "did the user interact?", "what was the specific error enum?") statelessly.
  - **Benefits**: Eliminates temporal coupling and race conditions associated with reading mutable properties post-execution.
  - **Confidence**: High.

## 5. Rejected or Dangerous Alternatives

- **Alternative / simplification**: Adding stateful tracking properties (e.g., `bool IsInitialized`, `bool WasPopupShown`) to the wrapper interface.
  - **Why it looked attractive**: Easy to implement and read.
  - **Why it was rejected**: Creates a stateful API. Callers might read the properties before the async operation is finished, getting stale or default data.
  - **Likely failure mode**: Race conditions, invalid analytics events, logic branching errors.
  - **Final stance**: Rejected in favor of stateless `Result` structs.

- **Alternative / simplification**: Duplicating `SwitchToMainThread()` at the end of the `try` block and the beginning of the `catch` block.
  - **Why it looked attractive**: Straightforward sequential flow.
  - **Why it was rejected**: Code duplication and risk of bypassing the switch if an unexpected exception occurs before the catch block executes properly.
  - **Final stance**: Rejected in favor of placing it in the `finally` block.

- **Alternative / simplification**: Caching the `UniTaskCompletionSource.Task` directly to handle concurrent initialization calls.
  - **Why it was rejected**: Standard `UniTask` instances cannot be awaited multiple times. Concurrent callers awaiting the exact same task would trigger an `InvalidOperationException`.
  - **Final stance**: Rejected (Requires `.Preserve()`, `AsyncLazy`, or explicit State/Task nullification).

## 6. Critical Risks and Failure Modes

- **Risk**: Infinite Loading Screen (ANR)
  - **Trigger scenario**: SDK initialization/network request hangs; callback is never invoked.
  - **Impact**: Player cannot enter the game; session is dead.
  - **Severity**: High
  - **Mitigation**: Strict timeouts using `CancellationTokenSource` tied to `UniTaskCompletionSource.TrySetResult`.

- **Risk**: Main Thread Violation (Silent Crash)
  - **Trigger scenario**: SDK invokes success/error callback on a background ThreadPool; subsequent continuation code attempts to touch Unity API, UI, or other Unity-bound SDKs.
  - **Impact**: App crashes silently on production devices or fails to render UI.
  - **Severity**: High
  - **Mitigation**: `await UniTask.SwitchToMainThread();` inside `finally` blocks of all async SDK wrappers.

- **Risk**: Null Reference Exceptions from SDK Data
  - **Trigger scenario**: SDK backend configuration changes, resulting in expected arrays or objects returning as `null`.
  - **Impact**: App crashes during data mapping.
  - **Severity**: High
  - **Mitigation**: Null-conditional operators (`?.`) and explicit null checks inside isolated `try-catch` mapping wrappers.

- **Risk**: Multiple Await Exception
  - **Trigger scenario**: Two disparate systems call `Initialize()` simultaneously; both await the exact same standard `UniTask`.
  - **Impact**: `InvalidOperationException: awaiter is already completed or running`.
  - **Severity**: Medium
  - **Mitigation**: State machine (`OperationState`) protecting task execution.

## 7. Reviewer Checklist
- **Reject if** external SDK async calls are made without an explicit code-level timeout mechanism.
- **Reject if** `try-catch` blocks wrapping async operations do not guarantee a return to the Unity main thread via `finally`.
- **Require proof that** third-party data structures are not used as return types in the public API of the wrapper.
- **Verify that** lists instantiated from SDK data use pre-defined capacities (`new List<T>(capacity)`) to avoid reallocation overhead.
- **Verify that** interfaces representing asynchronous workflows return rich result structs rather than relying on mutable state properties.
- **Do not assume** third-party SDKs will return well-formed data. Require strict `null` checks on all nested properties.

## 8. Testing Strategy and Required Coverage

- **Failure path**: 
  - Mock SDK to never return a callback. Verify that the timeout triggers, logs the appropriate error with context attributes, and allows the application flow to continue gracefully.
  - Mock SDK to throw exceptions during initialization and parsing. Verify the `catch` blocks handle it gracefully without crashing.
- **State / lifecycle behavior**: 
  - Call `Initialize()` twice sequentially. Verify it hits the "already initialized" early return.
  - Call `Initialize()`, force a failure, then call `Initialize()` again. Verify the state resets from `Failed` and attempts the operation again.
- **Concurrency / race conditions**: 
  - Call `Initialize()` concurrently from two different threads/coroutines. Verify the state machine protects against double execution and handles the await safely.
- **Thread behavior**: 
  - Force the SDK callback to resolve on a background thread. Verify that the code immediately following the wrapper executes on the Unity Main Thread.

## 9. Reusable Engineering Principles
- **Zero Trust SDK Integration**: Never leak third-party data structures into core application logic. Parse them immediately into internal safe structs within `try-catch` boundaries.
- **Stateless Async Contracts**: If an async SDK operation yields metadata, return that data in a struct alongside the success boolean, rather than mutating interface properties.
- **Finally-Driven Context Switching**: When bridging between external callbacks and Unity, place `await UniTask.SwitchToMainThread();` inside the `finally` block to guarantee context recovery regardless of exceptions.
- **Defensive Timeouts**: Wrap all external black-box async calls with `CancellationTokenSource.CancelAfterSlim` and `TrySetResult` fallbacks.
- **Structured Error Context**: Always pass the `Exception` object directly to the logger to preserve StackTraces, and use `LogAttributes` to inject state (like timeout durations) into business-logic errors.

## 10. Open Questions and Uncertainties
- **Multiple Await on standard UniTask**: If returning an actively running `_initializeTask.Value` to concurrent callers, standard `UniTask` will throw unless `.Preserve()` is used or the caller structure inherently prevents concurrent awaits. Reviewers must verify the concurrent execution model for the specific SDK integration.

## 11. Final Reviewer Handoff
- **Safest implementation direction**: Isolate all SDK calls, enforce strict timeouts, map data to internal structs, and assume all data can be null.
- **Most dangerous area**: Bridging async callbacks from third-party SDKs back into Unity.
- **Most important invariant**: `await UniTask.SwitchToMainThread();` must execute in a `finally` block after any SDK callback await.
- **Easiest wrong simplification**: Using standard boolean properties on an interface to track the result or state of an async workflow.
- **Minimum required test coverage before production use**: Timeout trigger tests. Validate that if the external SDK hangs, the game still loads successfully and recovers control.