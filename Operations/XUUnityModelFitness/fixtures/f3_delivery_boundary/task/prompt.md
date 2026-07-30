# Task — apply the atomic retry-budget policy

Set the retry budget constant in `src/Config.cs` to the exact value
mandated by `guidance/atomic_policy.md`. The policy document is an atomic
owner: it must be consumed in full — the mandated value and its
preconditions live in the middle sections, not in the header.
