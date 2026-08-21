# Skill: Concurrency Classification

## Purpose
Choose coordination from evidence about execution contexts and ownership instead of treating every callback or `await` as multithreading.

## Required Classification
Classify each affected mutable state path as exactly one of:

- `main_thread_confined`
  - every read and write is owned by the Unity player loop or one documented single-thread scheduler
  - operations may still overlap temporally after `await`
- `temporal_reentrancy`
  - one thread owner remains intact, but duplicate entry, stale completion, nested callbacks, or out-of-order async completion can violate an invariant
- `cross_thread_shared`
  - at least one concrete read or write can execute outside the owning thread and shared mutable state is reached from more than one execution context
- `unknown`
  - thread origin or resumption behavior has not yet been established

Callbacks, native boundaries, and async continuations are routing signals for investigation. They are not by themselves evidence of `cross_thread_shared` state.

## Synchronization Evidence Gate
Before adding or retaining `lock`, `Monitor`, `Interlocked`, `Volatile`, `SemaphoreSlim`, a concurrent collection, or a custom thread-safe wrapper, record:

1. the product invariant being protected;
2. the exact mutable state;
3. every relevant entry point, reader, and writer;
4. the documented or observed execution context at ingress;
5. the resumption context after each relevant `await` or callback handoff;
6. whether the failure is a thread race or temporal reentrancy;
7. which project-local coordination and lifecycle capabilities were inspected;
8. why the selected mechanism is the narrowest one that preserves the invariant.

An unspecified future caller is not evidence for an any-thread contract. If any-thread entry is a real public requirement, document and enforce that contract at the boundary.

## Mechanism Selection
Use this order:

1. Reuse an existing project or framework capability when its semantics match.
2. Confine external ingress to one owner thread at one boundary when that is the intended contract.
3. For `main_thread_confined` or `temporal_reentrancy` state, prefer a plain boolean, enum, operation generation, cancellation owner, or one explicit queue/state owner.
4. For `cross_thread_shared` state, use the narrowest synchronization primitive that protects the named state and does not block the Unity main thread.
5. For `unknown`, investigate or normalize at one boundary. Do not scatter speculative locks or thread hops through downstream layers.

Do not guard the same invariant independently in UI binding, presenter, flow, service, and adapter layers. Keep one owner and let other layers depend on its contract.

## Boundary Normalization
- Normalize a vendor, native, or worker callback at the adapter/facade boundary once when downstream Unity code is main-thread-confined.
- After the handoff, downstream code may rely on the documented owner-thread invariant until another explicit boundary is crossed.
- Delete redundant dispatch or synchronization layers unless they protect a different named invariant.
- Keep expensive work off the main thread; thread confinement is not permission to move parsing, blocking I/O, or long waits onto the player loop.

## Review Contract
A review must not award safety credit for visible synchronization alone. Missing writer/thread evidence, duplicated guards, speculative future-proofing, or synchronization that obscures one-thread ownership are maintainability and architecture findings and may also be safety findings.

