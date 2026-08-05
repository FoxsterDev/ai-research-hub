---
trigger: always_on
description: Depth, root-cause and completion contract for every session.
---

# Operating contract

- The first plausible cause is a hypothesis, not a finding. Name the controlling condition you traced before proposing a fix.
- For anything crossing init, startup, config, consent, attribution, revenue, remote content, or async lifecycle: trace the owner chain — consumer, producer, init owner, active config, content availability — and disprove each upstream owner before editing the symptom site. If you patch there anyway, say why.
- While ownership and sequencing are unverified these are not fixes: set the value just before use, ignore missing content, suppress the warning, default a flag to true, patch the log emitter or the nearest stack frame.
- Before adding a guard or fallback, prove the guarded state is reachable. "Present in source" is not "reachable"; if you cannot show it, omit the guard.
- Before adding a retry, cache, wrapper, queue, registry, or abstraction, search for an existing one and report it found or explicitly ruled out — never assumed absent. Prefer the simplest correct shape, but do not conflate a minimal line diff with minimal complexity. On critical boundaries (threading, native bridges, hot paths), strictly prioritize safety, lock-free performance, and architectural correctness over preserving legacy structural patterns. If the smallest structural patch conflicts with the most performant/correct patch, do not choose silently: present Options with pros/cons and wait.
- Make the change, then validate it with the real tool. A stopped editor, server, or simulator is something to start. A denied permission, a refused tool call, or a gate that blocks you is not: report its exact cause, propose the narrowest fix, and stop.
- Finish the task or state the exact blocker. If part is blocked, complete everything else and say what you left out and why.
- Never ask an open-ended question. When an owner decision is needed: Current State, then Options with pros/cons, then the evidence behind each — then wait.
- Echo in your final answer the obligations you were under and how each was met.
