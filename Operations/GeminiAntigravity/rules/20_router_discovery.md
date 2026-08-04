---
trigger: always_on
description: How to find and obey a workspace's own instruction router before doing work in it.
---

# Router discovery

- When a workspace contains `Agents.md`, `AGENTS.md`, or `Gemini.md`/`GEMINI.md`, the nearest one is the source of truth for this work. It outranks your defaults and your habits.
- A router or start-session file is atomic context: load it first line through EOF, then follow its load order in the order given. Never act on a router you only skimmed, and name what you read before your first edit.
- Load the chain, not the leaf: repo-level router, then the shared protocol modules it names, then the project-level router, then that project's local memory. Resolve project roots dynamically from the paths in the request, never from a remembered list of names; if they span more than one root, ask which.
- Project memory and project-local rules beat workspace-shared rules, which beat these global rules. On conflict the more specific file wins — say which one you followed.
- Archived or dated report material is not runtime instruction, and any stored note or prior-session claim is a point-in-time observation to re-verify against current code. Long knowledge and reference files are valid only when the router routes you there.
