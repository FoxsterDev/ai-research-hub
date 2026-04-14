# XUUnity Utility: System Progress Review

## Goal
Evaluate where the current AI system stands against the roadmap and execution plan, then identify the next milestone with the highest leverage.

## Use For
- periodic progress reviews
- milestone planning
- deciding what to build next
- checking whether the current system is ready for the next growth step

## Inputs
- current `AIRoot/Modules/XUUnity/` structure
- current `AIModules/XUUnityInternal/` structure when present
- current `AIOutput/Registry/project_registry.yaml` if present
- current utilities, skills, product protocols, and reviews
- `AIRoot/Roadmaps/AI_AUTOMATION_ROADMAP.md`
- `AIRoot/Roadmaps/AI_AUTOMATION_EXECUTION_PLAN.md`
- latest system evaluation or health review if available

## Process
1. Identify what roadmap phases already have meaningful implementation coverage.
2. Check whether the public `xuunity` core and the internal shared overlay are both structurally coherent.
2a. Check whether newly added shared knowledge has actually been wired into routing, trigger hints, or protocol references instead of only being stored on disk.
3. Check whether `AIOutput/Registry/project_registry.yaml` is present and whether its key fields still match the current repo structure.
4. Compare the current system against the active execution-plan deliverables.
5. Score progress by workstream:
   - foundation
   - project health
   - feature delivery
   - risk routing
   - product self-service
   - review artifact pipeline
   - project registry
   - low-risk autonomy
6. Identify the main blockers preventing the next milestone.
7. Recommend the smallest high-leverage next milestone instead of a broad wishlist.

## Output
- current maturity snapshot
- completed versus partial versus missing milestones
- progress score by workstream
- project registry status:
  - current
  - stale
  - missing
- shared layer status:
  - public core current
  - internal overlay current
  - boundary drift detected
- knowledge routing status:
  - reachable
  - partially reachable
  - dead ballast detected
- current bottleneck
- recommended next milestone
- recommended next 3 deliverables

## Rule
Do not reward prompt volume.
Reward operational readiness, consistency, verification quality, and leverage across many projects.
