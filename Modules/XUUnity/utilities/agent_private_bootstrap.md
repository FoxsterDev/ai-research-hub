# XUUnity Utility: Agent Private Bootstrap

## Goal
Install or refresh a thin agent-private memory entry so an AI agent that supports durable local memory remembers how to load and apply `xuunity` without duplicating shared rule bodies.

## Use For
- first `xuunity` request in a new project
- onboarding a new AI agent or tool to an existing `xuunity` project
- repairing an agent-private memory folder that copied shared rules instead of routing to them
- creating a tool-specific capability map for how that agent executes shared validation, search, edit, and memory rules

## Entry Commands
- `xuunity agent bootstrap`
- `xuunity bootstrap agent memory`
- `xuunity setup agent memory`
- `xuunity install working discipline`
- `xuunity refresh working discipline`

## Source Of Truth
Load `knowledge/agent_source_of_truth.md` before using this utility.

Shared rule bodies remain in:
- `AIRoot/Modules/XUUnity/`
- the host-local shared overlay when present
- the resolved project's durable project memory

Agent-private memory may contain only:
- routing pointers into those shared layers
- a capability map for that agent's own tools
- small calibration notes that are specific to the user or agent

## Process
1. Detect whether the current agent supports durable private memory, a persistent project entrypoint, or another user-approved agent-local store.
2. If no private store exists, do not create ad hoc files in random locations. Report that bootstrap is unsupported and continue with normal `xuunity` stack loading.
3. Resolve the active repo and Unity project before writing agent-private routing pointers.
4. Inspect existing agent-private memory for duplicated shared rule bodies.
5. Replace duplicated shared doctrine with pointers to the canonical shared owners.
6. Create or update one working-discipline entry from `utilities/agent_private_bootstrap_template.md`.
7. Keep the private entry short. It should force the agent to load the shared core, not become a second copy of the core.
8. If the private memory system has an index file, add or update one index entry pointing to the working-discipline entry.
9. Preserve unrelated user-authored private memories.
10. Report:
   - whether bootstrap was installed, refreshed, skipped, or unsupported
   - private destination used, redacted if it contains user-specific or host-private details
   - canonical shared files referenced
   - duplicated rule bodies removed or left for manual cleanup

## Safety Rules
- Do not write secrets, credentials, tokens, private keys, or credential-bearing URLs into agent-private memory.
- Do not copy long shared rule sections into private memory.
- Do not overwrite unrelated private memories.
- Do not make private memory the source of truth for `xuunity` behavior.
- If agent-private memory conflicts with shared `xuunity` guidance, follow the shared layer and refresh the private router.
- If the agent cannot safely write private memory, continue the task and mention the missing bootstrap as a non-blocking gap.

## Capability Map Guidance
The capability map should be agent-specific, but the categories are portable:
- how this agent loads `xuunity` files
- how this agent searches code and prompts
- how this agent edits files safely
- how this agent runs representative Unity validation in the current host
- how this agent records durable outputs without duplicating shared rules

Keep concrete tool names in the private entry, not in the public core, unless the tool is part of a public reusable `xuunity` workflow.
