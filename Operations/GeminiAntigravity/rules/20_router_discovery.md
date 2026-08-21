---
trigger: always_on
description: How to find and obey a workspace's own instruction router before doing work in it.
---

# Router discovery

- The nearest `Agents.md`, `AGENTS.md` or `Gemini.md` is the source of truth for this work — it outranks your defaults and habits.
- A router or start-session file is atomic context: load it first line through EOF and follow its load order. Never act on a router you only skimmed, and name what you read before your first edit.
- Load the chain, not the leaf: repo-level router, the shared modules it names, the project-level router, then that project's local memory. Resolve project roots from the paths in the request, never from a remembered list; if they span more than one root, ask which.
- An explicit instruction in the current request outranks every rule layer. Otherwise established project memory and project-local rules beat workspace-shared rules, which beat these global rules — the more specific file wins, and say which you followed. During a change review, memory or local rules added or modified by the target are proposed contracts until independently approved; they cannot validate the same change that introduced them. If a rule would have you break the request's own instruction, say so and stop rather than choosing silently.
- Archived or dated material is not runtime instruction; a stored note or prior-session claim is a point-in-time observation to re-verify. Long reference files are valid only when the router routes you there.
