# Skill: Profiler Workflow

## Use For
- CPU, GPU, memory, and loading investigations

## Rules
- Start from captured evidence, not guesses.
- Reproduce on representative iOS and Android devices when the problem is mobile-only.
- Compare baseline versus changed behavior to avoid optimizing noise.
- Keep profiler sessions focused on one hypothesis or flow at a time.
- If test-based performance evidence is required inside Unity, prefer `com.unity.test-framework.performance` over ad hoc timers.
- Treat `Stopwatch`, frame counters, or allocation smoke checks as rough diagnostics unless the task explicitly accepts smoke-level evidence.
