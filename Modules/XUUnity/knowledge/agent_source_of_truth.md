# XUUnity Knowledge: Agent Source of Truth

## Goal
Keep `xuunity` guidance durable, shared, and reusable when multiple AI agents or tools work on the same Unity project.

## Layer Model
- Shared public core: reusable, public-safe Unity guidance belongs in `AIRoot/Modules/XUUnity/`.
- Host-local shared layer: reusable guidance that depends on a specific host repo, private workflow, or internal portfolio convention belongs in that host's overlay or router, not in the public core.
- Project memory: durable project-specific truth belongs in the project's `Assets/AIOutput/ProjectMemory/` or the host-declared equivalent.
- Agent-private layer: an agent's private memory, entrypoint, or tool config should stay thin. It may contain routing pointers, a capability map for that agent's tools, and small calibration notes. It must not copy shared rule bodies.

## Routing Rules
- When a reusable keeper rule is learned, promote the rule into the smallest correct shared layer instead of storing a duplicate in agent-private memory.
- Before writing a durable rule into an agent-private store, check whether the rule already belongs in public core, host-local shared guidance, or project memory.
- If a rule is already represented in shared guidance, agent-private memory should point to that shared owner instead of restating it.
- On the first `xuunity` use for a new agent or project, if the agent supports durable private memory, install or refresh a thin working-discipline entry from `utilities/agent_private_bootstrap_template.md` through `utilities/agent_private_bootstrap.md`.
- Keep agent capability maps separate from shared doctrine. Tool-specific command names, UI affordances, local credentials, and model-specific habits belong only in the agent-private layer.
- Keep shared guidance model-agnostic. A public `xuunity` rule should be understandable and usable by different agents without depending on one agent's runtime, memory format, or plugin system.
- When the same router is exposed through multiple filenames for tool compatibility, keep one source of truth by using a symlink or a thin pointer rather than maintaining parallel copies.

## Promotion Boundaries
- Public core is correct for Unity, C#, mobile, platform, validation, routing, and review guidance that is reusable across unrelated projects and public-safe.
- Host-local shared guidance is correct for repo-specific validation lanes, private overlays, internal delivery conventions, and named internal workflows.
- Project memory is correct for project architecture, product behavior, local footguns, project-specific SDK setup, and constraints that would not make sense outside that project.
- Agent-private memory is correct only for how a specific agent finds and applies the shared truth.

## Entrypoint Contract
- A selected router, protocol entrypoint, or start-session file is atomic context: load it from first line through EOF before applying it.
- A partial read, summary, excerpt, search hit, or fixed line window is not valid entrypoint loading.
- Keep default-loaded entrypoints lean and head-complete: the must-load rule, routing procedure, and output/execution contract must survive within the smallest head read window. Entrypoint adequacy is governed by the byte-complete-kernel invariant (`scripts/check_entrypoint_kernel.py`), not by a fixed line count.
- Put detailed rules, command catalogs, and matrices in explicitly routed owner files.
- Longer knowledge, review, skill, and reference files are valid only when trigger-loaded; they are not default entrypoints.

## Review Questions
- Is this rule reusable outside the current project?
- Is it public-safe, or does it depend on host-private workflow?
- Does the rule describe Unity/project behavior, or only one agent's way of executing it?
- Would copying it into private memory create a second maintenance point?
- Is there an explicit load path or trigger that will make the shared rule reachable during normal task assembly?
