# XUUnity Knowledge: MCP Scenario Authoring

Use this file when authoring, reviewing, or debugging Unity MCP scenario JSON or another ordered editor-integrated automation sequence.

## Rule

- Treat MCP scenario hook success as "the hook action was requested or applied", not as proof that Unity is immediately settled for the next operation.
- After any scenario step that can mutate compile-affecting or editor-refresh-affecting state, insert a settle-aware step before compile, PlayMode, scene inspection, screenshot, or scenario-dependent assertions.
- Compile-affecting or refresh-affecting mutations include:
  - build profile or environment switches
  - scripting define changes
  - build target changes
  - package graph changes
  - asset database refreshes or asset imports
  - project settings or generated dependency artifact changes
- Prefer a settle-aware operation such as `project_refresh` when available. Use fixed-duration waits only as a last resort and label the remaining validation weakness.
- For async project-defined UI flows, prefer a first-class `project_defined_hook_poll_until` step over repeated wait/snapshot/assert ladders. If that primitive is unavailable, treat the fallback as a capability gap and keep the scenario bounded.
- Do not start `compile_player_scripts`, `playmode_set`, screenshot capture, or state assertions immediately after a mutating hook unless the hook itself explicitly waits for Unity compile/update/domain-reload settle.
- Keep scenario steps narrow:
  - mutation step
  - settle step
  - compile or PlayMode step
  - evidence capture step
  - cleanup or restore step when the scenario mutates project state
- For project-defined hooks, document whether the hook completes after requesting the mutation or after Unity has fully settled from it.

## Scenario Review Checks

- Does every build profile, build target, package, or asset mutation have a settle boundary before the next Unity operation?
- Is the settle boundary state-aware rather than a blind sleep?
- If a blind sleep remains, is the reason explicit and is the evidence downgraded accordingly?
- Does the scenario restore any project profile or editor state that it mutates?
- Does the final result include enough evidence for the claim, such as compile output, scene snapshot, console tail, screenshot, or generated artifact inspection?

## Routing Triggers

Load this file when the task mentions:
- Unity MCP scenario JSON
- `project_defined_hook`
- `project_defined_hook_poll_until`
- `project_refresh`
- `compile_player_scripts`
- `playmode_set`
- build profile or environment hooks
- scripting define mutation inside MCP validation
- ordered MCP smoke, timing probe, or lifecycle probe flows
