# Concurrency Classification

Classify mutable state as main-thread-confined, temporal reentrancy,
cross-thread-shared, or unknown. A callback or `await` alone is not evidence of a
worker thread. Require a named off-main reader or writer before awarding safety
credit for locks, atomics, semaphores, or thread-safe wrappers.

Preserve real duplicate-entry, stale-completion, ordering, and idempotency
invariants with the smallest owner appropriate to the resolved project.
